"""Texts you about interested replies even when your PC is off - run by GitHub Actions every 15 minutes.

    .github/workflows/reply-watch.yml runs:  python scripts/cloud_reply_watch.py

It never sees your outreach lists (those stay on your PC). It reads each sending inbox the same
read-only way as the panel (nothing marked read, moved or deleted), looks only at messages that
are replies to an email you sent (they carry In-Reply-To), sorts them with the panel's own rules
(reply_scanner.classify / intent), and texts you on Telegram for the ones worth answering now:
interested, or asking the price, for a call, or for more info. No's, bounces and out-of-office are
left for the panel's Check replies to deal with.

This repository is public, so the Actions log is too: nothing personal is ever printed - only
counts. Replies already texted are remembered as one-way hashes (in the Actions cache), so a reply
is never texted twice.

Secrets (repository Settings -> Secrets and variables -> Actions):
    REPLY_WATCH_INBOXES   one inbox per line: address app-password
    TELEGRAM_BOT_TOKEN    TELEGRAM_CHAT_ID    (the same as the panel's)
    MAIL_IMAP_HOST        optional - imap.gmail.com if not set
"""

from __future__ import annotations

import email
import hashlib
import imaplib
import json
import os
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import reply_scanner as rs  # noqa: E402

SEEN_FILE = Path(os.environ.get("REPLY_WATCH_STATE", ".reply-watch/seen.txt"))
KEEP_SEEN = 3000
FIRST_RUN_WINDOW = timedelta(minutes=45)  # with no memory yet, only text about the last few replies
WINDOW = timedelta(days=2)  # GitHub's schedule can be late; anything newer than this not yet texted is
WORTH_TEXTING = {"price", "call", "info"}
LABELS = {"price": "asks the price", "call": "wants a call", "info": "wants more info", "later": "not right now"}


def inboxes(text: str) -> list[tuple[str, str]]:
    """'address app-password' per line (app passwords may have spaces - they're removed)."""
    out = []
    for line in (text or "").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and "@" in parts[0]:
            out.append((parts[0].lower(), "".join(parts[1:])))
    return out


def fingerprint(message_id: str) -> str:
    return hashlib.sha256(message_id.strip().encode()).hexdigest()[:20]


def load_seen() -> list[str]:
    return SEEN_FILE.read_text(encoding="utf-8").split() if SEEN_FILE.exists() else []


def save_seen(seen: list[str]) -> None:
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    SEEN_FILE.write_text("\n".join(seen[-KEEP_SEEN:]) + "\n", encoding="utf-8")


def worth_texting(kind: str, want: str) -> bool:
    return kind == "interested" or (kind == "read it" and want in WORTH_TEXTING)


def is_reply(msg, own: str) -> bool:
    sender = (getaddresses([msg.get("From") or ""]) or [("", "")])[0][1].lower()
    if not sender or sender == own or rs.BOUNCE_FROM.search(sender):
        return False
    return bool((msg.get("In-Reply-To") or "").strip() or (msg.get("References") or "").strip())


def alert_line(msg, text: str, kind: str, want: str, inbox: str) -> str:
    name, sender = (getaddresses([msg.get("From") or ""]) or [("", "")])[0]
    said = " ".join(text.split())[:160]
    label = LABELS.get(want, "sounds interested")
    who = f"{name} <{sender}>" if name else sender
    return f"{who} replied to {inbox} - {label}" + (f':\n"{said}"' if said else "")


def check_inbox(host: str, address: str, password: str, seen: set[str], since: datetime) -> tuple[list[str], list[str], int]:
    """(alert lines, new fingerprints, replies looked at) for one inbox."""
    imap = imaplib.IMAP4_SSL(host, 993, timeout=60)
    alerts, new, looked = [], [], 0
    try:
        imap.login(address, password)
        imap.select("INBOX", readonly=True)
        status, data = imap.search(None, "SINCE", since.strftime("%d-%b-%Y"))
        if status != "OK":
            return alerts, new, looked
        for num in (data[0] or b"").split():
            status, parts = imap.fetch(num, "(BODY.PEEK[HEADER])")
            if status != "OK" or not parts or not isinstance(parts[0], tuple):
                continue
            head = email.message_from_bytes(parts[0][1])
            mid = (head.get("Message-ID") or "").strip()
            if not mid or fingerprint(mid) in seen or not is_reply(head, address):
                continue
            try:
                when = parsedate_to_datetime(head.get("Date"))
                when = when if when.tzinfo else when.replace(tzinfo=timezone.utc)
            except (TypeError, ValueError):
                when = datetime.now(timezone.utc)
            if when < since:
                continue
            status, parts = imap.fetch(num, "(BODY.PEEK[])")
            if status != "OK" or not parts or not isinstance(parts[0], tuple):
                continue
            msg = email.message_from_bytes(parts[0][1])
            text = rs.body_text(msg)
            kind, want = rs.classify(msg, text), rs.intent(text)
            looked += 1
            new.append(fingerprint(mid))
            if worth_texting(kind, want):
                alerts.append(alert_line(msg, text, kind, want, address))
    finally:
        try:
            imap.logout()
        except Exception:  # noqa: BLE001
            pass
    return alerts, new, looked


def send(token: str, chat: str, text: str) -> None:
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                 data=json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=20).close()


def main() -> int:
    accounts = inboxes(os.environ.get("REPLY_WATCH_INBOXES", ""))
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    if not (accounts and token and chat):
        print("Not set up yet - add REPLY_WATCH_INBOXES, TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID as repository secrets.")
        return 0
    host = os.environ.get("MAIL_IMAP_HOST", "").strip() or "imap.gmail.com"
    seen_list = load_seen()
    now = datetime.now(timezone.utc)
    since = now - (WINDOW if seen_list else FIRST_RUN_WINDOW)
    seen = set(seen_list)
    alerts, failed, looked = [], 0, 0
    for n, (address, password) in enumerate(accounts, 1):
        try:
            a, new, k = check_inbox(host, address, password, seen, since)
        except (imaplib.IMAP4.error, OSError) as e:
            failed += 1
            print(f"Inbox {n}: couldn't check ({type(e).__name__}).")  # never the address or the message
            continue
        alerts += a
        looked += k
        seen_list += new
        seen.update(new)
    if alerts:
        text = "\n\n".join(alerts[:6]) + ("\n\n...and more." if len(alerts) > 6 else "") + \
            "\n\nOpen the panel and press Check replies to answer."
        try:
            send(token, chat, text)
        except OSError as e:
            print(f"Telegram didn't take the message ({type(e).__name__}) - will try again next run.")
            return 1  # not saved as seen, so the next run texts them
    save_seen(seen_list)
    print(f"Checked {len(accounts) - failed} of {len(accounts)} inboxes: {looked} new replies, {len(alerts)} texted.")
    return 1 if failed == len(accounts) else 0


if __name__ == "__main__":
    sys.exit(main())
