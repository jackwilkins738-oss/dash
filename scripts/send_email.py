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
GAP_SECONDS = (40, 90)

DEFAULT_TEMPLATES = {
    "first_subject": "A quick look at {{business}}'s website",
    "first_body": """Hi {{greeting_name}},

I had a look at {{business}}'s website on my phone and ran it through Google's own speed test. {{score_line}} {{issue_line}}

I build fast, hand-coded websites for trade firms, and I've put together a short preview of what a new site for {{business}} could look like - next to how your current one measures up:

{{preview_url}}

There's nothing to sign up for. If it's of interest, just reply and I'll happily talk it through.

Kind regards,
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
          "top_issue", "score_line", "issue_line", "your_name"}
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
    values = {**{k: str(v or "") for k, v in row.items()}, "your_name": your_name}
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


def send_batch(outreach: Path, followups: bool = False, test: bool = False, smtp=None, sleep=time.sleep,
               today: date | None = None, out=print) -> int:
    """Sends the waiting batch; returns how many were sent. Raises SendStopped on a run-ending problem."""
    today = today or date.today()
    your_name = os.environ.get("MAIL_FROM_NAME", "").strip()
    if not your_name:
        raise SendStopped("Add MAIL_FROM_NAME in Settings first - it's the name people see and your sign-off.")
    templates = load_templates(outreach)
    problem = template_problem(templates)
    if problem:
        raise SendStopped(problem)
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
    if test:
        todo = todo[:1]
    else:
        room = sum(max(0, DAILY_CAP - n) for n in used.values())
        if room <= 0:
            raise SendStopped(f"{DAILY_CAP} emails a day per inbox have already gone - the rest wait for tomorrow (keeps the accounts safe).")
        if len(todo) > room:
            out(f"Only {room} more today (the cap is {DAILY_CAP} a day per inbox) - the rest go next time you press Send.")
            todo = todo[:room]
    if len(inboxes) > 1 and not test:
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
            return main_inbox
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
                sleep(random.uniform(*GAP_SECONDS))
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
    args = ap.parse_args()
    outreach = eb.outreach_dir()
    what = "follow-ups" if args.followups else "emails"
    if not args.test:
        print(f"Sending the waiting {what}, 40-90 seconds apart. Stop any time - pressing Send again carries on.", flush=True)
    try:
        n = send_batch(outreach, followups=args.followups, test=args.test, out=lambda s: print(s, flush=True))
    except SendStopped as e:
        sys.exit(str(e))
    if not args.test:
        print(f"Done: {n} {what} sent. Replies are picked up by Check replies (and the autopilot).")


if __name__ == "__main__":
    main()
