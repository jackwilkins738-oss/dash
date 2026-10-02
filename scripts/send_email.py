"""Send today's batch from your own email - the panel's "Send today's batch" / "Send follow-ups".

    python scripts/send_email.py                 send the waiting batch (from Make email batch)
    python scripts/send_email.py --followups     send the waiting follow-up batch
    python scripts/send_email.py --test          send the first email of the batch to yourself only

Replaces importing into Mailmeteor: same emails, from the same account, spaced
out (40-90 seconds apart, like a person sending them) so the account stays out
of spam folders. Nothing is sent until you press the button; the autopilot
only ever makes the batch.

Each email is recorded in outreach/emails-sent.csv the moment it goes, so
stopping half way (the panel's Stop button, a crash, a closed laptop) never
sends anyone the same email twice - pressing Send again carries on with the
rest. Just before each email the do-not-contact list, bounces and replies are
checked again, so someone who said no this morning isn't emailed this
afternoon. A follow-up goes as a reply in the same thread as the first email.

Settings (panel): MAIL_ADDRESS and MAIL_APP_PASSWORD (the same Gmail app
password the reply scanner uses), MAIL_FROM_NAME (the name people see, and
{{your_name}} in the email), and optionally MAIL_SMTP_HOST (default: the
IMAP host with imap. swapped for smtp., else smtp.gmail.com).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import smtplib
import sys
import time
from datetime import date
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import email_batches as eb  # noqa: E402
import mail_accounts  # noqa: E402

TEMPLATES = "email-templates.json"
DAILY_CAP = 100  # first emails + follow-ups per inbox in one day, whatever the batch sizes say
GAP_SECONDS = (40, 90)  # the default spacing when no "minutes apart" is chosen
MAX_GAP_MINUTES = 60


def gap_range(minutes: float | None) -> tuple[float, float]:
    """Seconds to wait between two emails. "5 minutes apart" waits 4-6 minutes - never exactly the same gap,
    which looks like a script to the receiving server (the same idea as Mailmeteor's autopilot)."""
    if not minutes or minutes <= 0:
        return GAP_SECONDS
    m = min(float(minutes), MAX_GAP_MINUTES) * 60
    lo = max(30.0, m * 0.8)
    return lo, max(lo, m * 1.2)


def describe_gap(minutes: float | None, count: int | None = None) -> str:
    """'about 5 minutes apart - roughly 1h35 for 20' for the start-of-run line."""
    lo, hi = gap_range(minutes)
    each = f"{int(lo)}-{int(hi)} seconds apart" if hi < 120 else f"about {round((lo + hi) / 120)} minutes apart"
    if not count or count < 2:
        return each
    total = (count - 1) * (lo + hi) / 2 / 60
    took = f"{int(total)} min" if total < 60 else f"{int(total // 60)}h{int(total % 60):02d}"
    return f"{each} - roughly {took} for {count}"

DEFAULT_TEMPLATES = {
    "first_subject": "{{business}} - quick look at your website",
    "first_body": """Hi {{greeting_name}},

I put together a preview of what a new website for {{business}} could look like, next to how your current one measures up:

{{preview_url}}

I checked your current site on my phone too. {{score_line}} {{issue_line}} {{why_line}}

Worth a 10-minute chat?

{{your_name}}
Scalar Digital · 07401 696272 · scalardigital.co.uk

If you'd rather not hear from me again, just reply and say so and I won't get in touch.""",
    "followup_subject": "Following up - {{business}}",
    "followup_body": """Hi {{greeting_name}},

Just following up on my note last week about {{business}}'s website. {{issue_line}}

The preview I put together is still here if you'd like a look - no sign-up:

{{preview_url}}

If it's not for you, just reply and say so and I won't get in touch again.

Kind regards,
{{your_name}}
Scalar Digital · 07401 696272""",
}
# An optional second version of the first email, tested against the first: each firm gets one
# version, picked from its email address (so a re-send never switches it), and the scorecard
# (scorecard.py) compares how each does. Leave both blank to send one version only.
VARIANT_B = {"first_subject_b": "", "first_body_b": ""}

# What a template may use: the batch file's columns, plus your name.
FIELDS = {"business", "greeting_name", "email", "mobile_score", "lcp_s", "preview_url", "status", "trade", "area",
          "top_issue", "score_line", "issue_line", "why_line", "your_name", "booking_link"}
PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")


class SendStopped(Exception):
    """Something that has to stop the whole run (bad login, the day's cap)."""


# ---------------------------------------------------------------- templates


def load_templates(outreach: Path) -> dict[str, str]:
    try:
        saved = json.loads((outreach / TEMPLATES).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    out = {k: str(saved.get(k) or v) for k, v in DEFAULT_TEMPLATES.items()}
    out.update({k: str(saved.get(k) or "") for k in VARIANT_B})
    return out


def has_variant_b(templates: dict[str, str]) -> bool:
    return bool(templates.get("first_subject_b", "").strip() and templates.get("first_body_b", "").strip())


def variant_for(email: str, templates: dict[str, str]) -> str:
    """"A" or "B" - fixed per address, about half each, and always "A" when there's no version B."""
    if not has_variant_b(templates):
        return "A"
    import hashlib

    return "B" if hashlib.sha256(email.strip().lower().encode()).digest()[0] % 2 else "A"


def template_problem(templates: dict[str, str]) -> str:
    """Why these templates can't be saved/sent, or ''."""
    b = [k for k in VARIANT_B if templates.get(k, "").strip()]
    if len(b) == 1:
        return "Version B needs both a subject and a body (or leave both blank to send one version)."
    for key in [*DEFAULT_TEMPLATES, *b]:
        text = templates.get(key, "")
        if not text.strip():
            return f"The {key.replace('_', ' ')} is empty."
        unknown = sorted(set(PLACEHOLDER.findall(text)) - FIELDS)
        if unknown:
            return f"The {key.replace('_', ' ')} uses {{{{{unknown[0]}}}}}, which isn't a field. Fields: " + ", ".join(sorted(FIELDS))
        if "[your name]" in text.lower():
            return "Replace [your name] with {{your_name}} (set MAIL_FROM_NAME in Settings)."
    for key in ("first_body", "followup_body", *(["first_body_b"] if b else [])):
        if "{{preview_url}}" not in templates[key].replace(" ", ""):
            return f"The {key.replace('_', ' ')} must include {{{{preview_url}}}}."
    return ""


def save_templates(outreach: Path, templates: dict[str, str]) -> str:
    clean = {k: str(templates.get(k) or "").replace("\r\n", "\n")[:6000] for k in [*DEFAULT_TEMPLATES, *VARIANT_B]}
    problem = template_problem(clean)
    if problem:
        return problem
    outreach.mkdir(exist_ok=True)
    (outreach / TEMPLATES).write_text(json.dumps(clean, indent=2), encoding="utf-8")
    return ""


def render(text: str, row: dict, your_name: str) -> str:
    values = {"booking_link": os.environ.get("BOOKING_LINK", "").strip(), **{k: str(v or "") for k, v in row.items() if v},
              "your_name": your_name}
    # A line offering the booking link means nothing without one - drop it rather than leave "pick a time: ".
    if not values.get("booking_link"):
        text = "\n".join(line for line in text.split("\n") if not re.search(r"\{\{\s*booking_link\s*\}\}", line))
    out = PLACEHOLDER.sub(lambda m: values.get(m.group(1), ""), text)
    # An empty {{score_line}} {{issue_line}} leaves double spaces; tidy them, keep line breaks.
    return "\n".join(re.sub(r"[ \t]{2,}", " ", line).rstrip() for line in out.split("\n")).strip() + "\n"


# ---------------------------------------------------------------- sending


def smtp_host(env=None) -> str:
    env = os.environ if env is None else env
    host = (env.get("MAIL_SMTP_HOST") or "").strip()
    if host:
        return host
    imap = (env.get("MAIL_IMAP_HOST") or "").strip()
    return "smtp." + imap[5:] if imap.startswith("imap.") else "smtp.gmail.com"


def connect(env=None):
    """An SMTP login with the panel's mail settings (os.environ, or the settings dict passed in)."""
    env = os.environ if env is None else env
    address, password = env.get("MAIL_ADDRESS", ""), env.get("MAIL_APP_PASSWORD", "")
    if not (address and password):
        raise SendStopped("Add MAIL_ADDRESS and MAIL_APP_PASSWORD in Settings first.")
    try:
        smtp = smtplib.SMTP_SSL(smtp_host(env), 465, timeout=60)
        smtp.login(address, password.replace(" ", ""))
    except smtplib.SMTPAuthenticationError as e:
        raise SendStopped("Your email login was refused - check MAIL_APP_PASSWORD (a Gmail app password, not your normal one).") from e
    except (OSError, smtplib.SMTPException) as e:
        raise SendStopped(f"Couldn't connect to {smtp_host(env)} ({e}).") from e
    return smtp


def build_message(to: str, subject: str, body: str, reply_to_id: str = "", env=None) -> EmailMessage:
    env = os.environ if env is None else env
    address = env.get("MAIL_ADDRESS", "")
    name = (env.get("MAIL_FROM_NAME") or "").strip()
    msg = EmailMessage()
    msg["From"] = formataddr((name, address)) if name else address
    msg["To"] = to
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=address.split("@")[-1] or None)
    # Lets their mail app show an "Unsubscribe" link; it emails you, and the reply scanner blocks them.
    msg["List-Unsubscribe"] = f"<mailto:{address}?subject=unsubscribe>"
    if reply_to_id:
        msg["In-Reply-To"] = reply_to_id
        msg["References"] = reply_to_id
    msg.set_content(body)
    return msg


def sent_today(outreach: Path, today: date, by_inbox: bool = False, main: str = ""):
    """Emails sent today - in total, or per inbox (older rows with no sent_from count to the main inbox)."""
    rows = eb._rows(outreach / eb.SENT)[1]
    counts: dict[str, int] = {}
    for r in rows:
        n = (r.get("sent") == today.isoformat()) + (r.get("followup_sent") == today.isoformat())
        if n:
            inbox = (r.get("sent_from") or main).lower()
            counts[inbox] = counts.get(inbox, 0) + n
    return counts if by_inbox else sum(counts.values())


def today_summary(outreach: Path, today: date, inboxes: list[str]) -> dict:
    """Today's sending for the panel: total sent, the day's cap, what's left, and the same per inbox.

    Counted exactly as the sender counts against DAILY_CAP (first emails + follow-ups). Rows with no
    sent_from - Mailmeteor batches marked as sent, and older sends - count to the main inbox, the
    first of `inboxes`. An inbox that sent today but has since been removed still shows, with no
    allowance left, so the total always matches the log.
    """
    main = inboxes[0].lower() if inboxes else ""
    used = sent_today(outreach, today, by_inbox=True, main=main)
    order = [a.lower() for a in inboxes] or [""]
    order += [a for a in used if a not in order]
    rows = []
    for address in order:
        sent = used.get(address, 0)
        live = address in [a.lower() for a in inboxes] or (not inboxes and address == "")
        rows.append({"inbox": address or "main inbox", "sent": sent, "left": max(0, DAILY_CAP - sent) if live else 0})
    total = sum(r["sent"] for r in rows)
    cap = DAILY_CAP * max(1, len(inboxes))
    return {"sent": total, "cap": cap, "left": sum(r["left"] for r in rows), "by_inbox": rows}


def _still_ok(outreach: Path, email: str, business: str) -> str:
    """'' if they may still be emailed, else why not (checked again just before sending)."""
    stop = eb.do_not_email(outreach)
    if email in stop:
        return stop[email]
    for r in eb._rows(outreach / "replies.csv")[1]:
        if r.get("kind") == "out of office":
            continue
        if (r.get("from") or "").lower() == email or (business and (r.get("business") or "").lower() == business.lower()):
            return "they've replied"
    return ""


BOUNCE_WINDOW_DAYS = 14
BOUNCE_MIN_SENT = 20
BOUNCE_LIMIT = 0.03


def bounce_problem(outreach: Path, today: date) -> str:
    """Why sending should pause, or ''. Too many bounces is the clearest sign of a bad list, and mail
    providers judge a sender on it - past about 3%, more sending hurts the domain every email uses."""
    from datetime import timedelta

    since = today - timedelta(days=BOUNCE_WINDOW_DAYS)
    recent = set()
    for r in eb._rows(outreach / eb.SENT)[1]:
        try:
            if date.fromisoformat(r.get("sent") or "") >= since:
                recent.add((r.get("email") or "").lower())
        except ValueError:
            continue
    if len(recent) < BOUNCE_MIN_SENT:
        return ""
    bounced = {(r.get("email") or "").lower() for r in eb._rows(outreach / "email-checks.csv")[1] if r.get("result") == "bounced"}
    n = len(recent & bounced)
    rate = n / len(recent)
    if rate <= BOUNCE_LIMIT:
        return ""
    return (f"Sending paused: {n} of the {len(recent)} emails sent in the last {BOUNCE_WINDOW_DAYS} days bounced ({rate:.0%}). "
            "Over 3% tells mail providers the list is bad and starts landing you in spam. Check the addresses in your "
            "newest list (the panel's Emails button verifies them), then send smaller batches - it clears as the "
            "bounces age out of the last 14 days.")


def send_batch(outreach: Path, followups: bool = False, test: bool = False, smtp=None, sleep=time.sleep,
               today: date | None = None, out=print, gap_minutes: float | None = None, only_from: str = "") -> int:
    """Sends the waiting batch; returns how many were sent. Raises SendStopped on a run-ending problem."""
    today = today or date.today()
    your_name = os.environ.get("MAIL_FROM_NAME", "").strip()
    if not your_name:
        raise SendStopped("Add MAIL_FROM_NAME in Settings first - it's the name people see and your sign-off.")
    templates = load_templates(outreach)
    problem = template_problem(templates)
    if problem:
        raise SendStopped(problem)
    if not test:
        paused = bounce_problem(outreach, today)
        if paused:
            raise SendStopped(paused)
    kind = "followup" if followups else "first"
    pending_name = eb.FOLLOWUP_PENDING if followups else eb.PENDING
    pending = eb._rows(outreach / pending_name)[1]
    if not pending:
        raise SendStopped("No follow-up batch waiting - press Make follow-up batch first." if followups
                          else "No batch waiting - press Make email batch first (the autopilot makes one each morning).")
    batch_file = outreach / pending[0].get("batch", "")
    details = {(r.get("email") or "").strip().lower(): r for r in eb._rows(batch_file)[1]} if batch_file.is_file() else {}
    sent_rows = {(r.get("email") or "").lower(): r for r in eb._rows(outreach / eb.SENT)[1]}

    todo = []
    for p in pending:
        email = (p.get("email") or "").strip().lower()
        row = {**details.get(email, {}), **{k: v for k, v in p.items() if v}, "email": email}
        already = sent_rows.get(email, {})
        if not test and (already.get("followup_sent") if followups else already.get("sent")):
            continue  # sent on an earlier press
        todo.append(row)
    if not todo:
        (outreach / pending_name).unlink(missing_ok=True)
        out("Everyone in this batch has already been emailed.")
        return 0
    inboxes = mail_accounts.accounts()
    if not inboxes:
        raise SendStopped("Add MAIL_ADDRESS and MAIL_APP_PASSWORD in Settings first.")
    main_inbox = inboxes[0]
    used = sent_today(outreach, today, by_inbox=True, main=main_inbox.address)
    used = {a.address: used.get(a.address, 0) for a in inboxes}
    # "Send from" one inbox: first emails go only from it, and only the follow-ups whose first email it sent
    # (a follow-up from another address would break the thread) - the rest stay waiting for their own inbox.
    only_from = (only_from or "").strip().lower()
    chosen = None
    if only_from:
        chosen = next((a for a in inboxes if a.address == only_from), None)
        if chosen is None:
            raise SendStopped(f"{only_from} isn't one of your inboxes - add it (with its app password) in Settings, or pick another.")
        if followups:
            todo = [r for r in todo
                    if (sent_rows.get(r["email"].lower(), {}).get("sent_from") or main_inbox.address).lower() == only_from]
            if not todo:
                out(f"No follow-ups waiting for {only_from} - the others go from the inbox that sent their first email.")
                return 0
    if test:
        todo = todo[:1]
    else:
        room = (max(0, DAILY_CAP - used[chosen.address]) if chosen
                else sum(max(0, DAILY_CAP - n) for n in used.values()))
        if room <= 0:
            raise SendStopped(f"{DAILY_CAP} emails a day per inbox have already gone - the rest wait for tomorrow (keeps the accounts safe).")
        if len(todo) > room:
            out(f"Only {room} more today (the cap is {DAILY_CAP} a day per inbox) - the rest go next time you press Send.")
            todo = todo[:room]
    if chosen and not test:
        out(f"Sending from {chosen.address} only.")
    elif len(inboxes) > 1 and not test:
        out(f"Sending from {len(inboxes)} inboxes, spread evenly.")

    # One login per inbox, opened when first needed. A test smtp passed in stands in for all of them.
    conns: dict[str, object] = {}

    def conn(inbox: mail_accounts.Account, fresh: bool = False):
        if smtp is not None:
            return smtp
        if fresh or inbox.address not in conns:
            conns[inbox.address] = connect(inbox.env())
        return conns[inbox.address]

    def pick(email: str) -> mail_accounts.Account | None:
        """Follow-ups go from the inbox that sent the first email (same thread); first emails from the least-used inbox."""
        if followups:
            first_from = (sent_rows.get(email, {}).get("sent_from") or main_inbox.address).lower()
            inbox = next((a for a in inboxes if a.address == first_from), main_inbox)
            return inbox if test or used[inbox.address] < DAILY_CAP else None
        if test:
            return chosen or main_inbox
        if chosen:
            return chosen if used[chosen.address] < DAILY_CAP else None
        free = [a for a in inboxes if used[a.address] < DAILY_CAP]
        return min(free, key=lambda a: used[a.address]) if free else None

    me = main_inbox.address
    sent = 0
    try:
        for i, row in enumerate(todo):
            email, business = row["email"], row.get("business", "")
            if not test:
                why = _still_ok(outreach, email, business)
                if why:
                    out(f"[{i + 1}/{len(todo)}] {business}: skipped - {why}")
                    continue
            variant = "" if followups else variant_for(email, templates)
            suffix = "_b" if variant == "B" else ""
            subject = render(templates[f"{kind}_subject{suffix}"], row, your_name).strip()
            reply_to = ""
            if followups:
                first = sent_rows.get(email, {})
                if first.get("message_id") and first.get("subject"):
                    reply_to, subject = first["message_id"], "Re: " + first["subject"]
            body = render(templates[f"{kind}_body{suffix}"], row, your_name)
            inbox = pick(email)
            if inbox is None:
                out(f"[{i + 1}/{len(todo)}] {business}: waits for tomorrow - its inbox has reached today's {DAILY_CAP}.")
                continue
            to = me if test else email
            if test:
                subject = f"[TEST to yourself - would go to {email}{', version ' + variant if has_variant_b(templates) and variant else ''}] {subject}"
            msg = build_message(to, subject, body, reply_to, env=inbox.env())
            try:
                conn(inbox).send_message(msg)
            except smtplib.SMTPRecipientsRefused:
                out(f"[{i + 1}/{len(todo)}] {business}: {email} was refused by your mail server - marked as bounced.")
                if not test:
                    eb.record_bounce(outreach, email)
                continue
            except smtplib.SMTPServerDisconnected:
                conn(inbox, fresh=True).send_message(msg)
            used[inbox.address] += 1
            if test:
                out(f"Test sent to {me} - check it reads right, then press Send.")
                return 1
            if followups:
                eb.record_followup_sent(outreach, email, today)
            else:
                eb.record_sent(outreach, row, batch_file.name, today, msg["Message-ID"], subject, variant, inbox.address)
            sent += 1
            out(f"[{i + 1}/{len(todo)}] sent to {business} ({email})" + (f" from {inbox.address}" if len(inboxes) > 1 else ""))
            if i < len(todo) - 1:
                sleep(random.uniform(*gap_range(gap_minutes)))
    finally:
        for c in [smtp] if smtp is not None else conns.values():
            try:
                c.quit()
            except Exception:  # already closed
                pass
    left = [p for p in pending if not _done(outreach, p, followups)]
    if not left:
        (outreach / pending_name).unlink(missing_ok=True)
    return sent


def _done(outreach: Path, p: dict, followups: bool) -> bool:
    email = (p.get("email") or "").lower()
    for r in eb._rows(outreach / eb.SENT)[1]:
        if (r.get("email") or "").lower() == email:
            return bool(r.get("followup_sent") if followups else r.get("sent"))
    return bool(_still_ok(outreach, email, p.get("business", "")))  # said no or replied: not waiting any more


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--followups", action="store_true")
    ap.add_argument("--test", action="store_true", help="send the first email to yourself only")
    ap.add_argument("--from", dest="only_from", default="", help="send from this one inbox only (default: spread across all)")
    ap.add_argument("--gap-minutes", type=float, default=0,
                    help=f"spread the emails this many minutes apart (varied a little each time; up to {MAX_GAP_MINUTES}). "
                         "Leave out for 40-90 seconds")
    args = ap.parse_args()
    outreach = eb.outreach_dir()
    what = "follow-ups" if args.followups else "emails"
    if not args.test:
        waiting = len(eb._rows(outreach / (eb.FOLLOWUP_PENDING if args.followups else eb.PENDING))[1])
        print(f"Sending the waiting {what}, {describe_gap(args.gap_minutes, waiting)}. "
              "Stop any time - pressing Send again carries on.", flush=True)
    try:
        n = send_batch(outreach, followups=args.followups, test=args.test, out=lambda s: print(s, flush=True),
                       gap_minutes=args.gap_minutes, only_from=args.only_from)
    except SendStopped as e:
        sys.exit(str(e))
    if not args.test:
        print(f"Done: {n} {what} sent. Replies are picked up by Check replies (and the autopilot).")


if __name__ == "__main__":
    main()
