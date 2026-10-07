"""Quote chaser: a prospect who opened their quote but hasn't accepted it after two days.

Someone who has read a £2,500 quote and gone quiet is the warmest lead there is. Each morning (with
the nudges, from 8:30) the Telegram bot texts you each one: what they were quoted, how often they've
opened it, their number to ring, and a short follow-up ready to send (✅ Send it / ✏️ Edit / 🗑 Discard).
Nothing goes out without your tap. Each quote is chased once (outreach/quotes-chased.csv).

The open quotes come from the dashboard (GET /api/prospects/quotes); phones and emails from your lists.
"""

from __future__ import annotations

import csv
import json
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

CHASED = "quotes-chased.csv"
WAIT_HOURS = 48
MOST = 5


def fetch(api: str, secret: str, tenant: str, get=None) -> list[dict]:
    def _get(url: str) -> dict:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {secret}"})
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read())

    try:
        return (get or _get)(f"{api.rstrip('/')}/api/prospects/quotes?tenant_id={tenant}").get("quotes") or []
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return []  # an old dashboard, or offline: no chasers today, never an error


def chased(outreach: Path) -> set[str]:
    path = outreach / CHASED
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        return {r["quote"] for r in csv.DictReader(f) if r.get("quote")}


def mark(outreach: Path, quote: dict, today: date) -> None:
    path = outreach / CHASED
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["quote", "slug", "business", "chased"])
        w.writerow([quote.get("quote_number") or quote.get("quote_url"), quote.get("slug"), quote.get("business_name"), today.isoformat()])


def _when(value: str | None) -> datetime | None:
    try:
        return datetime.fromisoformat((value or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def due(quotes: list[dict], outreach: Path, now: datetime | None = None) -> list[dict]:
    """Opened at least once, sent 48+ hours ago, not accepted, never chased - most opened first."""
    now = now or datetime.now(timezone.utc)
    done = chased(outreach)
    out = []
    for q in quotes:
        sent = _when(q.get("sent_at"))
        if not sent or (now - sent).total_seconds() < WAIT_HOURS * 3600 or not q.get("view_count"):
            continue
        if (q.get("quote_number") or q.get("quote_url")) in done:
            continue
        out.append(q)
    out.sort(key=lambda q: (-int(q.get("view_count") or 0), q.get("last_viewed_at") or ""))
    return out[:MOST]


def pounds(pence) -> str:
    try:
        return f"£{int(pence) / 100:,.0f}"
    except (TypeError, ValueError):
        return ""


def draft(quote: dict, firm: dict, your_name: str) -> str:
    from saved_replies import first_name

    return (f"Hi {first_name(firm.get('contact', ''))},\n\n"
            f"Just checking the quote for {quote.get('business_name') or firm.get('business')} came through OK and made sense. "
            "If anything in it isn't clear, or you'd like something changed, reply here or give me a ring - happy to go "
            "through it in 10 minutes.\n\n"
            f"{quote.get('quote_url', '')}\n\n"
            f"{your_name or 'Scalar Digital'}\nScalar Digital · 07401 696272")
