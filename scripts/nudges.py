"""Morning nudges: firms that opened their preview more than once but haven't replied or been rung.

Each morning (from 8:30, while the panel is open) the Telegram bot texts you each one, with a short
follow-up written for them, in the thread of the email they already have. ✅ Send it sends it from the
inbox that first wrote to them; ✏️ Edit or 🗑 Discard otherwise. Nothing goes out without your tap.

A firm is nudged once, ever (outreach/nudged.csv), and only when:

    opened their preview 2+ times, the latest in the last 3 days
    never rung, and no reply from them waiting
    emailed by you, but not in the last 2 days
"""

from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from pathlib import Path

NUDGED = "nudged.csv"
MIN_VIEWS = 2
FRESH_DAYS = 3
QUIET_DAYS = 2
MOST = 5
AT = (8, 30)  # local time


def _day(value: str) -> date | None:
    try:
        return date.fromisoformat((value or "")[:10])
    except ValueError:
        return None


def nudged(outreach: Path) -> set[str]:
    path = outreach / NUDGED
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        return {r["website"] for r in csv.DictReader(f) if r.get("website")}


def mark(outreach: Path, website: str, business: str, today: date) -> None:
    path = outreach / NUDGED
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["website", "business", "nudged"])
        w.writerow([website, business, today.isoformat()])


def sent_rows(outreach: Path) -> dict[str, dict]:
    path = outreach / "emails-sent.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return {(r.get("email") or "").strip().lower(): r for r in csv.DictReader(f) if r.get("email")}


def candidates(data: dict, outreach: Path, now: datetime | None = None) -> list[dict]:
    """The viewers worth a nudge today, hottest first, each with the email they were sent ("sent")."""
    now = now or datetime.now(timezone.utc)
    done = nudged(outreach)
    sent = sent_rows(outreach)
    replied = {i.get("website") for i in data.get("replied") or []}
    out = []
    for item in data.get("viewing") or []:
        email = (item.get("email") or "").strip().lower()
        viewed = _day(item.get("last_viewed", ""))
        row = sent.get(email)
        if (item.get("views", 0) < MIN_VIEWS or not viewed or (now.date() - viewed).days > FRESH_DAYS
                or item.get("calls") or item.get("website") in replied or item.get("website") in done or not row):
            continue
        last_email = max(filter(None, (_day(row.get(c, "")) for c in ("sent", "followup_sent", "final_sent"))), default=None)
        if not last_email or (now.date() - last_email).days < QUIET_DAYS:
            continue
        out.append({**item, "sent": row})
    out.sort(key=lambda i: -i.get("heat", 0))
    return out[:MOST]


def draft(item: dict, your_name: str) -> dict:
    """The follow-up: subject and message id of their first email (so it lands in that thread), and the text."""
    from saved_replies import first_name

    row = item.get("sent") or {}
    link = row.get("preview_url") or (item.get("preview") or "").replace("src=dashboard", "src=email")
    text = (f"Hi {first_name(item.get('contact', ''))},\n\n"
            f"Quick one - did the page I put together for {item['business']} make sense? I'm happy to talk you "
            "through the two or three changes that would make the biggest difference - 10 minutes on the phone, "
            "whenever suits.\n\n"
            f"{link}\n\n"
            f"{your_name or 'Scalar Digital'}\nScalar Digital · 07401 696272")
    return {"subject": row.get("subject") or "", "message_id": row.get("message_id") or "", "text": text}


def due(now_local: datetime, last_day: str) -> bool:
    """True once a day, from 8:30 local time."""
    return (now_local.hour, now_local.minute) >= AT and last_day != now_local.date().isoformat()
