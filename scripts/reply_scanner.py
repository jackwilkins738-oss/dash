"""Reads the replies to your outreach and acts on them - so nobody slips through.

    python scripts/reply_scanner.py        (the panel's "Check replies")

Connects to your sending inbox over IMAP with a Gmail app password, READ-ONLY:
nothing is marked read, moved or deleted. Only messages from firms you've
contacted are looked at (matched on their email address, or their website's
domain); everything else is ignored and never stored.

Each reply is sorted:
    bounce          the address doesn't exist - marked bad, so the firm moves to a letter
    not interested  "no thanks", "unsubscribe", "remove me" ... - added to the
                    do-not-contact list at once, for every list (you must honour these)
    out of office   noted, nothing else
    interested      "call me", "how much", "sounds good" ... - top of the Calls tab,
                    and a phone alert if Telegram is set up
    read it         anything else: a person wrote back - top of the Calls tab for you

"Not interested" wins over "interested" when a reply has both: the safe side.
Kept in outreach/replies.csv (who, when, what kind, a 300-character snippet).

Settings (panel): MAIL_ADDRESS, MAIL_APP_PASSWORD, and MAIL_IMAP_HOST (default
imap.gmail.com). A Gmail app password needs 2-Step Verification on the account:
Google Account > Security > App passwords.
"""

from __future__ import annotations

import csv
import email
import imaplib
import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone
from email.header import decode_header, make_header
from email.message import Message
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

REPLIES = "replies.csv"
FIELDS = ["message_id", "date", "from", "business", "website", "kind", "subject", "snippet", "handled", "intent", "message", "objection"]
FREE_MAIL = {"gmail.com", "googlemail.com", "hotmail.com", "hotmail.co.uk", "outlook.com", "live.co.uk", "live.com",
             "yahoo.co.uk", "yahoo.com", "btinternet.com", "icloud.com", "aol.com", "sky.com", "msn.com", "me.com"}

NEGATIVE = re.compile(
    r"\bnot interested\b|\bno,? thank(s| you)\b|\bno thanks\b|unsubscribe|\bremove (me|us)\b|take (me|us) off|"
    r"stop (emailing|contacting|sending)|(don'?t|do not) (email|contact)|not (required|needed)|no need\b|"
    r"(happy|fine|sorted) with (our|my|the) (current )?(site|website)|already have (a|our) (site|website|web designer)",
    re.I,
)
POSITIVE = re.compile(
    r"\binterested\b|call me|give (me|us) a (call|ring|bell)|ring me|how much|what (would|does) it cost|\bprice|\bcost\b|"
    r"\bquote\b|sounds (good|great)|tell me more|more info|when (can|could) (you|we)|let'?s (talk|chat)|\bbook\b",
    re.I,
)
# What a reply is asking for, so the Calls tab can suggest the right saved reply. "later" wins: a
# "maybe in the spring - how much would it be?" is a call-back, not a price to chase today.
INTENTS = [
    ("later", re.compile(r"not (right )?now|not at the moment|maybe (later|next year|in the (new )?year)|(in|next|after) "
                         r"(the )?(spring|summer|autumn|winter|new year|january|february|march|april|may|june|july|august|"
                         r"september|october|november|december)|too busy|busy at the moment|get back to you|"
                         r"(few|couple of|6|six|3|three) months|later (in|this) (the )?year", re.I)),
    ("price", re.compile(r"how much|what (would|does|will) (it|that|this) cost|\bprice|\bcost\b|\bquote\b|ballpark|budget", re.I)),
    ("call", re.compile(r"call me|give (me|us) a (call|ring|bell)|ring me|phone me|\bcall\b.*\b(on|at)\b|my number|"
                        r"\b0\d{3,4}[\s-]?\d{3}[\s-]?\d{3,4}\b|\b07\d{3}[\s-]?\d{6}\b|let'?s (talk|chat)", re.I)),
    ("info", re.compile(r"tell me more|more info|more details|how (does|would) (it|this) work|what('?s| is) included|"
                        r"what do (i|we) get|examples?|portfolio", re.I)),
]


# What's stopping them, when a reply pushes back - counted in the scorecard so you can see which
# objection your email should answer up front. First match wins; most replies have none.
OBJECTIONS = [
    ("suspicious", re.compile(r"\bscam\b|spam|who (are|is) (you|this)|how did you get (my|our|this)|where did you get|"
                              r"is this (legit|real|genuine)|phishing|gdpr", re.I)),
    ("price", re.compile(r"too (expensive|dear|much)|can'?t afford|out of (my|our) (price range|budget)|cheaper|"
                         r"(no|not got the|haven'?t got the|don'?t have the) (money|budget)|bit steep|pricey", re.I)),
    ("has someone", re.compile(r"already (got|have|use|using) (a|an|someone|somebody|our|my)\b|"
                               r"(have|got) (someone|somebody|a guy|a lad|a mate|a friend|a web designer|a company) (who|that|for)|"
                               r"(my|our) (son|daughter|nephew|niece|brother|sister|wife|husband|mate|friend|cousin) "
                               r"(does|did|built|made|looks after|sorts|is doing)|in-?house|"
                               r"(being|getting) (re)?(done|built|redone|designed)", re.I)),
    ("enough work", re.compile(r"(enough|plenty of|loads of|lots of|more than enough) work|word of mouth|fully booked|"
                               r"booked (up|solid)|busy enough|(all|most) (of )?(our|my) work (comes )?(from|through)", re.I)),
    ("happy with site", re.compile(r"(happy|fine|ok|okay|pleased|sorted|content) with (our|my|the) (current |existing )?"
                                   r"(site|website)|(site|website) (is|works) (fine|ok|okay|good)|(just|recently) (had|got) (a new|it)", re.I)),
    ("not now", re.compile(r"not (right )?now|not at the moment|maybe (later|next year|in the (new )?year)|too busy|"
                           r"(few|couple of|6|six|3|three) months|get back to you|another time|next year", re.I)),
]
OBJECTION_LABELS = {"suspicious": "wary of a cold email", "price": "price", "has someone": "already has someone",
                    "enough work": "gets enough work already", "happy with site": "happy with their site", "not now": "not right now"}


def objection(text: str) -> str:
    for name, pattern in OBJECTIONS:
        if pattern.search(text or ""):
            return name
    return ""


def intent(text: str) -> str:
    for name, pattern in INTENTS:
        if pattern.search(text or ""):
            return name
    return ""


OOO = re.compile(r"out of (the )?office|automatic reply|auto-?reply|on (annual )?leave|on holiday|away from (the )?office|"
                 r"currently away|limited access to (my )?email", re.I)
BOUNCE_FROM = re.compile(r"mailer-daemon|postmaster|mail delivery", re.I)
BOUNCE_SUBJECT = re.compile(r"delivery status notification|undeliver|delivery (has )?failed|mail delivery (failed|subsystem)|"
                            r"returned mail|failure notice|address not found", re.I)
QUOTE_START = re.compile(r"^(on .+ wrote:|-{2,} ?original message|from: .+|sent from my )", re.I | re.M)


def outreach_dir() -> Path:
    for parent in [HERE.parent, *HERE.parents]:
        if (parent / "outreach").is_dir():
            return parent / "outreach"
    return HERE.parent / "outreach"


# ---------------------------------------------------------------- who you've contacted


def _norm(name: str) -> str:
    s = (name or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(w for w in s.split() if w not in {"ltd", "limited", "llp", "plc", "the", "uk", "co", "company"})


def firm_in_subject(subject: str, by_email: dict[str, dict]) -> dict | None:
    """A reply from a personal address still carries your subject line - "Re: A quick look at Kerr Roofing's
    website" - so the firm's own name in it identifies them. Longest name wins; short names aren't trusted."""
    flat = f" {_norm(subject)} "
    best = None
    for firm in by_email.values():
        name = _norm(firm["business"])
        if len(name) >= 6 and f" {name} " in flat and (best is None or len(name) > len(_norm(best["business"]))):
            best = firm
    return best


def known_firms(outreach: Path) -> tuple[dict[str, dict], dict[str, dict]]:
    """(email -> firm, domain -> firm) from every list and the files beside them."""
    import openpyxl

    from push_prospects import domain_of

    by_email: dict[str, dict] = {}
    by_domain: dict[str, dict] = {}

    def add(business: str, website: str, mail: str) -> None:
        business, mail = (business or "").strip(), (mail or "").strip().lower()
        site = domain_of(website or "") or ""
        if not business:
            return
        firm = {"business": business, "website": site}
        if "@" in mail:
            by_email.setdefault(mail, firm)
            dom = mail.split("@", 1)[1]
            if dom not in FREE_MAIL:
                by_domain.setdefault(dom, firm)
        if site:
            by_domain.setdefault(site, firm)

    for sheet in outreach.glob("*.xlsx"):
        if sheet.name.startswith("~$") or sheet.name == "outreach-results.xlsx":
            continue
        try:
            wb = openpyxl.load_workbook(sheet, read_only=True, data_only=True)
        except Exception:
            continue
        for ws in wb.worksheets:
            rows = ws.iter_rows(values_only=True)
            header = [str(h).strip() if h else "" for h in next(rows, ())]
            for values in rows:
                r = dict(zip(header, values))
                add(str(r.get("Business") or ""), str(r.get("Website") or r.get("Possible website") or ""), str(r.get("Email") or ""))
        wb.close()
    found = outreach / "contacts-found.csv"
    if found.exists():
        with found.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                firm = by_domain.get(r.get("website") or "")
                if firm and r.get("email"):
                    by_email.setdefault(r["email"].strip().lower(), firm)
    return by_email, by_domain


# ---------------------------------------------------------------- reading a message


def _header(msg: Message, name: str) -> str:
    raw = msg.get(name) or ""
    try:
        return str(make_header(decode_header(raw)))
    except Exception:
        return str(raw)


def body_text(msg: Message) -> str:
    """The plain text of a message, without the quoted email it replies to."""
    parts = []
    for part in msg.walk() if msg.is_multipart() else [msg]:
        if part.get_content_type() == "text/plain" and not part.get_filename():
            payload = part.get_payload(decode=True) or b""
            parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
    if not parts:
        for part in msg.walk() if msg.is_multipart() else [msg]:
            if part.get_content_type() == "text/html":
                html = (part.get_payload(decode=True) or b"").decode(part.get_content_charset() or "utf-8", errors="replace")
                parts.append(re.sub(r"<[^>]+>", " ", html))
    text = "\n".join(parts)
    lines = []
    for line in text.splitlines():
        if line.strip().startswith(">") or QUOTE_START.match(line.strip()):
            break
        lines.append(line)
    return re.sub(r"\s+", " ", "\n".join(lines)).strip()


def bounced_addresses(msg: Message) -> list[str]:
    """The addresses a bounce says couldn't be delivered to."""
    found = []
    for part in msg.walk():
        if part.get_content_type() in ("message/delivery-status", "text/plain"):
            payload = part.get_payload(decode=True)
            if payload is None and part.is_multipart():
                payload = "\n".join(str(p) for p in part.get_payload()).encode()
            text = (payload or b"").decode("utf-8", errors="replace")
            found += re.findall(r"(?:Final|Original)-Recipient:\s*rfc822;\s*([^\s<>]+@[^\s<>]+)", text, re.I)
            if not found:
                found += re.findall(r"[\w.+'-]+@[\w-]+(?:\.[\w-]+)+", text)
    return list(dict.fromkeys(a.strip().lower().rstrip(".") for a in found))


MONTHS = {m: i for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}
_AWAY = r"(?:back|return(?:ing)?|in the office|until|till|from)\b[^.\n]{0,30}?"
_DAY_MONTH = re.compile(_AWAY + r"\b(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?([a-z]{3})[a-z]*", re.I)
_MONTH_DAY = re.compile(_AWAY + r"\b([a-z]{3})[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\b", re.I)
_NUMERIC = re.compile(_AWAY + r"\b(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?\b", re.I)
OOO_DEFAULT_DAYS = 7


def back_on(text: str, received: date) -> date:
    """When an out-of-office says they're back ("back on Monday 14th October", "returning 14/10"), else a week
    after it arrived. UK day-first dates; the next such date on or after the reply."""
    def next_one(day: int, month: int, year: int | None = None) -> date | None:
        try:
            d = date(year if year and year > 99 else (2000 + year if year else received.year), month, day)
        except ValueError:
            return None
        if not year and d < received:
            d = date(d.year + 1, month, day)
        return d if received <= d <= received + timedelta(days=120) else None

    text = text or ""
    for m in _DAY_MONTH.finditer(text):
        if m.group(2).lower()[:3] in MONTHS and (d := next_one(int(m.group(1)), MONTHS[m.group(2).lower()[:3]])):
            return d
    for m in _MONTH_DAY.finditer(text):
        if m.group(1).lower()[:3] in MONTHS and (d := next_one(int(m.group(2)), MONTHS[m.group(1).lower()[:3]])):
            return d
    for m in _NUMERIC.finditer(text):
        if d := next_one(int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None):
            return d
    return received + timedelta(days=OOO_DEFAULT_DAYS)


def classify(msg: Message, text: str) -> str:
    subject = _header(msg, "Subject")
    auto = (msg.get("Auto-Submitted") or "").lower()
    if (auto and auto != "no") or msg.get("X-Autoreply") or msg.get("X-Autorespond") or OOO.search(subject) or OOO.search(text[:400]):
        return "out of office"
    if NEGATIVE.search(text) or NEGATIVE.search(subject):
        return "not interested"
    if POSITIVE.search(text):
        return "interested"
    return "read it"


# ---------------------------------------------------------------- scan


def scan(outreach: Path, imap, since: date, my_address: str = "") -> list[dict]:
    """Reads INBOX since a date (read-only) and returns new, matched replies."""
    by_email, by_domain = known_firms(outreach)
    done = {r["message_id"] for r in _rows(outreach / REPLIES)}
    imap.select("INBOX", readonly=True)
    status, data = imap.search(None, "SINCE", since.strftime("%d-%b-%Y"))
    if status != "OK":
        raise RuntimeError("the inbox search failed")
    new: list[dict] = []
    for num in (data[0] or b"").split():
        status, parts = imap.fetch(num, "(BODY.PEEK[])")
        if status != "OK" or not parts or not isinstance(parts[0], tuple):
            continue
        msg = email.message_from_bytes(parts[0][1])
        mid = (msg.get("Message-ID") or "").strip() or f"{msg.get('Date')}|{msg.get('From')}"
        if mid in done:
            continue
        display, sender = (getaddresses([msg.get("From") or ""]) or [("", "")])[0]
        sender = sender.lower()
        if my_address and sender == my_address.lower():
            continue
        subject = _header(msg, "Subject")
        try:
            when = parsedate_to_datetime(msg.get("Date")).astimezone(timezone.utc).isoformat(timespec="minutes")
        except Exception:
            when = datetime.now(timezone.utc).isoformat(timespec="minutes")
        if BOUNCE_FROM.search(sender) or BOUNCE_SUBJECT.search(subject):
            for addr in bounced_addresses(msg):
                firm = by_email.get(addr)
                if firm:
                    new.append({"message_id": f"{mid}|{addr}", "date": when, "from": addr, **firm, "kind": "bounce",
                                "subject": subject[:150], "snippet": "", "handled": ""})
            continue
        firm = by_email.get(sender) or by_domain.get(sender.split("@", 1)[-1])
        if not firm and re.match(r"(re|aw|antw|sv)\s*:", subject, re.I):
            firm = firm_in_subject(subject, by_email)  # replied from a personal address
        if not firm:
            continue  # not someone you contacted: ignored, never stored
        text = body_text(msg)
        new.append({"message_id": mid, "date": when, "from": sender, **firm, "kind": classify(msg, text), "intent": intent(text),
                    "subject": subject[:150], "snippet": text[:300], "handled": "",
                    "message": text[:4000], "contact": display[:80],
                    "objection": objection(text) if classify(msg, text) in ("not interested", "read it", "interested") else ""})  # the whole reply, for "Draft with AI" - stays on this PC
    return new


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def act(outreach: Path, replies: list[dict]) -> dict[str, int]:
    """Saves the replies and does what each kind needs."""
    from contact_rules import add_to_blocklist

    counts: dict[str, int] = {}
    for r in replies:
        counts[r["kind"]] = counts.get(r["kind"], 0) + 1
        if r["kind"] == "not interested":
            add_to_blocklist(outreach, [(k, v) for k, v in (("email", r["from"]), ("website", r["website"]), ("name", r["business"])) if v],
                             f"replied: not interested ({r['date'][:10]})")
            r["handled"] = "blocked"
        elif r["kind"] == "bounce":
            path = outreach / "email-checks.csv"
            rows = {x["email"]: x for x in _rows(path) if x.get("email")}
            rows[r["from"]] = {"email": r["from"], "result": "bounced", "checked_at": datetime.now(timezone.utc).isoformat()}
            with path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["email", "result", "checked_at"], extrasaction="ignore")
                w.writeheader()
                w.writerows(rows.values())
            r["handled"] = "moved to letter"
        elif r["kind"] == "out of office":
            r["handled"] = "noted"
    path = outreach / REPLIES
    existing = _rows(path)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(existing + replies)
    return counts


def alert_text(replies: list[dict]) -> str:
    """The phone alert for replies worth answering now: who, from where, and what they said."""
    hot = [r for r in replies if r["kind"] == "interested"]
    if not hot:
        return ""
    lines = []
    for r in hot[:5]:
        said = " ".join(str(r.get("snippet") or "").split())[:160]
        lines.append(f"{r['business'] or r['from']} replied and sounds interested ({r['from']})" + (f':\n"{said}"' if said else ""))
    if len(hot) > 5:
        lines.append(f"...and {len(hot) - 5} more.")
    return "\n\n".join(lines) + "\n\nAnswer from the panel's Calls tab - the sooner the better."


def alert_messages(replies: list[dict], env: dict, saved: str = "") -> list[str]:
    """One text per interested reply, each with an AI draft when ANTHROPIC_API_KEY is set (the first
    few only); without a key, the single summary text as before."""
    import ai_reply

    hot = [r for r in replies if r["kind"] == "interested"]
    if not hot:
        return []
    if not (env.get("ANTHROPIC_API_KEY") or "").strip():
        return [alert_text(replies)]
    out = []
    for r in hot[: ai_reply.ALERT_DRAFTS]:
        firm = {**r, "message": r.get("message") or r.get("snippet") or ""}
        out.append(ai_reply.with_draft(alert_text([r]), ai_reply.try_draft(firm, env, r.get("contact", ""), saved)))
    rest = hot[ai_reply.ALERT_DRAFTS:]
    if rest:
        out.append(alert_text(rest))
    return out


def alert(replies: list[dict], saved: str = "") -> None:
    # With the cloud watch on (cloud_reply_watch.py), it does the texting - this would be a second text.
    if os.environ.get("CLOUD_REPLY_ALERTS", "").strip().lower() in ("1", "yes", "on", "true"):
        return
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    if not (token and chat):
        return
    for text in alert_messages(replies, dict(os.environ), saved):
        try:
            req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                         data=json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode(),
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=15).close()
        except OSError:
            pass


LOCK = ".reply-check.lock"
LOCK_STALE_S = 15 * 60  # a check that died mid-way never blocks the next one for long


class Busy(Exception):
    pass


class reply_lock:
    """One reply check at a time - the panel's button and the 15-minute watch both write replies.csv."""

    def __init__(self, outreach: Path):
        self.path = outreach / LOCK

    def __enter__(self):
        import time

        try:
            if self.path.exists() and time.time() - self.path.stat().st_mtime > LOCK_STALE_S:
                self.path.unlink()
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
        except FileExistsError as e:
            raise Busy("Another reply check is running right now - skipped this one.") from e
        return self

    def __exit__(self, *exc):
        try:
            self.path.unlink()
        except OSError:
            pass
        return False


def main() -> None:
    outreach = outreach_dir()
    outreach.mkdir(exist_ok=True)
    try:
        with reply_lock(outreach):
            _check(outreach)
    except Busy as e:
        print(e)


def _check(outreach: Path) -> None:
    import mail_accounts

    inboxes = mail_accounts.accounts()
    host = os.environ.get("MAIL_IMAP_HOST", "").strip() or "imap.gmail.com"
    if not inboxes:
        sys.exit("Add MAIL_ADDRESS and MAIL_APP_PASSWORD in Settings first (a Gmail app password - see the note there).")
    last = [r["date"] for r in _rows(outreach / REPLIES)]
    since = (date.fromisoformat(max(last)[:10]) - timedelta(days=2)) if last else date.today() - timedelta(days=30)
    # Every sending inbox - replies land wherever the email came from.
    replies: list[dict] = []
    seen: set[str] = set()
    for n, inbox in enumerate(inboxes):
        print(f"Checking {inbox.address} for replies since {since.strftime('%d %b %Y')} (read-only) ...", flush=True)
        try:
            imap = imaplib.IMAP4_SSL(host, 993, timeout=60)
            imap.login(inbox.address, inbox.password)
        except (imaplib.IMAP4.error, OSError) as e:
            problem = (f"The inbox refused the login ({e}). Use an app password, not your normal one: "
                       "Google Account > Security > 2-Step Verification > App passwords."
                       if isinstance(e, imaplib.IMAP4.error) else f"Couldn't reach {host} ({e}).")
            if n == 0:
                sys.exit(problem)
            print(f"  Skipped {inbox.address}: {problem}")
            continue
        try:
            for r in scan(outreach, imap, since, inbox.address):
                if r["message_id"] not in seen:
                    seen.add(r["message_id"])
                    replies.append(r)
        finally:
            try:
                imap.logout()
            except Exception:
                pass
    counts = act(outreach, replies)
    import saved_replies

    alert(replies, saved_replies.load(outreach))
    # A Mailmeteor batch waiting to be marked as sent: tick off whatever is already in Sent.
    try:
        import mailmeteor_sync

        firsts, follows = mailmeteor_sync.sync(outreach, inboxes, host)
        if firsts or follows:
            print(f"Mailmeteor: {firsts} first email(s) and {follows} follow-up(s) found in Sent - marked as sent.")
    except Exception as e:  # never let this stop the replies being reported
        print(f"  (Couldn't check Sent for Mailmeteor sends: {e})")
    if not replies:
        print("No new replies from anyone you've contacted.")
        return
    for r in replies:
        print(f"  {r['kind']:<15} {r['business']}" + (f" - \"{r['snippet'][:90]}\"" if r["snippet"] else ""))
    summary = ", ".join(f"{n} {k}" for k, n in sorted(counts.items()))
    print(f"Found {len(replies)} new: {summary}.")
    if counts.get("not interested"):
        print(f"  {counts['not interested']} added to do-not-contact - they're out of every list and batch.")
    if counts.get("bounce"):
        print(f"  {counts['bounce']} bounced - marked bad, so they'll get a letter instead.")
    if counts.get("interested") or counts.get("read it"):
        print("  Replies worth answering are at the top of the Calls tab.")


if __name__ == "__main__":
    main()
