"""Ticks off a Mailmeteor batch by itself, from what is actually in your Sent folder.

Mailmeteor sends through your own Gmail, so every email it sends lands in Sent. This reads the Sent
folder of each sending inbox - read-only, headers only (To, Cc, Date), nothing is changed or marked
read - and for any batch still waiting to be marked as sent, records the firms it finds there, with
the day the email really went and the inbox it went from. Firms not in Sent yet (a batch Mailmeteor
is still working through) stay waiting and are picked up next time.

Pressing "Mark batch as sent" still works as before; this only saves you having to remember.
"""

from __future__ import annotations

import csv
import email
import re
from datetime import date, datetime, timedelta
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path

import email_batches as eb

HEADERS = "(BODY.PEEK[HEADER.FIELDS (TO CC DATE SUBJECT)])"


def sent_folder(imap) -> str:
    """The Sent folder's name - found by its \\Sent flag, as Gmail names it per language."""
    status, boxes = imap.list()
    if status == "OK":
        for raw in boxes or []:
            line = raw.decode(errors="replace") if isinstance(raw, bytes) else str(raw)
            if "\\Sent" in line:
                m = re.search(r'"([^"]+)"\s*$', line) or re.search(r"(\S+)\s*$", line)
                if m:
                    return m.group(1)
    return "[Gmail]/Sent Mail"


def sent_to(imap, since: date) -> dict[str, list[date]]:
    """Every address emailed from this inbox since a date -> the days it was emailed."""
    return {a: [d for d, _ in v] for a, v in sent_with_subjects(imap, since).items()}


def sent_with_subjects(imap, since: date) -> dict[str, list[tuple[date, str]]]:
    """Every address emailed from this inbox since a date -> (day, subject) for each email."""
    status, _ = imap.select(f'"{sent_folder(imap)}"', readonly=True)
    if status != "OK":
        return {}
    status, data = imap.search(None, "SINCE", since.strftime("%d-%b-%Y"))
    nums = (data[0] or b"").split() if status == "OK" and data else []
    found: dict[str, list[date]] = {}
    if not nums:
        return found
    status, parts = imap.fetch(b",".join(nums).decode(), HEADERS)
    if status != "OK":
        return found
    for part in parts or []:
        if not isinstance(part, tuple):
            continue
        msg = email.message_from_bytes(part[1])
        try:
            day = parsedate_to_datetime(msg.get("Date")).astimezone().date()
        except Exception:
            continue
        subject = _subject(msg.get("Subject") or "")
        for _, addr in getaddresses([msg.get("To") or "", msg.get("Cc") or ""]):
            if addr:
                found.setdefault(addr.strip().lower(), []).append((day, subject))
    return found


def _subject(raw: str) -> str:
    from email.header import decode_header, make_header

    try:
        return " ".join(str(make_header(decode_header(raw))).split())[:200]
    except Exception:  # noqa: BLE001 - an odd header just goes without
        return " ".join(raw.split())[:200]


def prospects(outreach: Path) -> dict[str, dict]:
    """email -> {business, preview_url} for every firm on any list's Mailmeteor or links file."""
    out: dict[str, dict] = {}
    for path in sorted(outreach.glob("mailmeteor*.csv")) + sorted(outreach.glob("preview-links*.csv")):
        for r in eb._rows(path)[1]:
            e = (r.get("email") or r.get("Email") or "").strip().lower()
            if e and e not in out:
                out[e] = {"business": r.get("business") or r.get("Business") or "",
                          "preview_url": r.get("preview_url") or ""}
    return out


def backfill(outreach: Path, found: dict[str, list[tuple[date, str, str]]]) -> tuple[int, int]:
    """Adds every prospect your Sent folders show you emailed but emails-sent.csv doesn't - however it was
    sent (Mailmeteor straight from a list file, a batch that was replaced, by hand) -> (first emails,
    follow-ups) added. found: email -> [(day, inbox, subject)]. A later email to them, 2+ days on and
    before any reply from them, is their follow-up."""
    known = prospects(outreach)
    sent_rows = eb._rows(outreach / eb.SENT)[1]
    by_email = {(r.get("email") or "").lower(): r for r in sent_rows}
    replied: dict[str, date] = {}
    for r in eb._rows(outreach / "replies.csv")[1]:
        try:
            d = datetime.fromisoformat(str(r.get("date"))).date()
        except ValueError:
            continue
        e = (r.get("from") or "").strip().lower()
        replied[e] = min(d, replied.get(e, d))
    firsts = follows = 0
    for e, hits in found.items():
        if e not in known or not hits:
            continue
        hits = sorted(hits)
        row = by_email.get(e)
        if row is None or not row.get("sent"):
            day, inbox, subject = hits[0]
            row = {"email": e, "business": known[e]["business"], "preview_url": known[e]["preview_url"],
                   "batch": "found in Sent", "sent": day.isoformat(), "sent_from": inbox, "subject": subject}
            if e in by_email:
                by_email[e].update(row)
            else:
                sent_rows.append(row)
                by_email[e] = row
            firsts += 1
        if not row.get("followup_sent"):
            first = date.fromisoformat(row["sent"])
            later = [h for h in hits if (h[0] - first).days >= 2 and (e not in replied or h[0] < replied[e])]
            if later:
                row["followup_sent"] = later[0][0].isoformat()
                follows += 1
    if firsts or follows:
        eb._write_sent(outreach, sent_rows)
    return firsts, follows


def read_sent(inboxes, since: date, host: str = "imap.gmail.com", connect=None) -> dict[str, list[tuple[date, str, str]]]:
    """email -> [(day, inbox, subject)] from every sending inbox's Sent folder. Read-only, headers only."""
    if connect is None:
        import imaplib

        def connect():
            return imaplib.IMAP4_SSL(host, 993, timeout=60)

    found: dict[str, list[tuple[date, str, str]]] = {}
    for inbox in inboxes:
        try:
            imap = connect()
            imap.login(inbox.address, inbox.password)
        except Exception:  # noqa: BLE001 - a login problem shows in Check replies
            continue
        try:
            for addr, items in sent_with_subjects(imap, since).items():
                found.setdefault(addr, []).extend((d, inbox.address, subj) for d, subj in items)
        except Exception:  # noqa: BLE001
            pass
        finally:
            try:
                imap.logout()
            except Exception:  # noqa: BLE001
                pass
    return found


def _write_pending(path: Path, fields: list[str], rows: list[dict]) -> None:
    if not rows:
        path.unlink(missing_ok=True)
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def apply(outreach: Path, found: dict[str, list[tuple[date, str]]]) -> tuple[int, int]:
    """Records what Sent shows against the waiting batches -> (first emails, follow-ups) recorded."""
    sent_rows = eb._rows(outreach / eb.SENT)[1]
    by_email = {(r.get("email") or "").lower(): r for r in sent_rows}
    firsts = follows = 0

    fields, pending = eb._rows(outreach / eb.PENDING)
    since = _made(outreach / eb.PENDING)
    still = []
    for p in pending:
        e = (p.get("email") or "").strip().lower()
        if by_email.get(e, {}).get("sent"):
            continue  # already recorded (sent from the panel, or marked by hand)
        hits = sorted(h for h in found.get(e, []) if since is None or h[0] >= since)
        if not hits:
            still.append(p)
            continue
        day, inbox = hits[0]
        row = {"email": p.get("email", e), "business": p.get("business", ""), "preview_url": p.get("preview_url", ""),
               "batch": p.get("batch", ""), "sent": day.isoformat(), "sent_from": inbox}
        sent_rows.append(row)
        by_email[e] = row
        firsts += 1
    if len(still) != len(pending):  # untouched otherwise: its date is how old sends are told apart
        _write_pending(outreach / eb.PENDING, fields, still)

    fields, pending = eb._rows(outreach / eb.FOLLOWUP_PENDING)
    still = []
    for p in pending:
        e = (p.get("email") or "").strip().lower()
        row = by_email.get(e)
        if not row or row.get("followup_sent"):
            continue
        first = date.fromisoformat(row["sent"]) if row.get("sent") else None
        # The first email to them is in Sent too - only a later one is the follow-up.
        hits = sorted(h for h in found.get(e, []) if first is None or h[0] > first)
        if not hits:
            still.append(p)
            continue
        row["followup_sent"] = hits[0][0].isoformat()
        follows += 1
    if len(still) != len(pending):
        _write_pending(outreach / eb.FOLLOWUP_PENDING, fields, still)

    if firsts or follows:
        eb._write_sent(outreach, sent_rows)
    return firsts, follows


def _made(path: Path) -> date | None:
    """The day a batch file was made, less a day's grace - nothing sent before it can be from it."""
    try:
        return datetime.fromtimestamp(path.stat().st_mtime).date() - timedelta(days=1)
    except OSError:
        return None


def waiting(outreach: Path) -> bool:
    return (outreach / eb.PENDING).exists() or (outreach / eb.FOLLOWUP_PENDING).exists()


def sync(outreach: Path, inboxes, host: str = "imap.gmail.com", connect=None) -> tuple[int, int]:
    """Checks every sending inbox's Sent folder and records what it finds. Nothing waiting -> no login."""
    if not waiting(outreach) or not inboxes:
        return 0, 0
    made = [d for d in (_made(outreach / eb.PENDING), _made(outreach / eb.FOLLOWUP_PENDING)) if d]
    since = min(made) if made else date.today() - timedelta(days=7)
    if connect is None:
        import imaplib

        def connect():
            return imaplib.IMAP4_SSL(host, 993, timeout=60)

    found: dict[str, list[tuple[date, str]]] = {}
    for inbox in inboxes:
        try:
            imap = connect()
            imap.login(inbox.address, inbox.password)
        except Exception:
            continue  # a login problem shows up in Check replies; this just waits for next time
        try:
            for addr, days in sent_to(imap, since).items():
                found.setdefault(addr, []).extend((d, inbox.address) for d in days)
        except Exception:
            pass
        finally:
            try:
                imap.logout()
            except Exception:
                pass
    return apply(outreach, found)
