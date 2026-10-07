"""The Telegram bot's daily texts, beyond the nudges and quote chasers:

    plan        8:30 every day: one line per thing waiting - call-backs due, hot viewers, replies,
                open quotes, emails left to send - so the day starts from one message
    week        Sundays: this week against last week - sent, opened, replied, calls, conversations, won
    referrals   30 days after a launch (outreach/case-studies.csv): ask for a Google review and a
                referral, with the words ready to paste; asked once per client (referrals-asked.csv)

Counts only - nothing here sends anything to anyone but you.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

ASKED = "referrals-asked.csv"
REFERRAL_AFTER_DAYS = 30


def plan(data: dict, quotes: int, to_email: int) -> str:
    rows = [
        (len(data.get("callbacks") or []), "call-back(s) due"),
        (sum(1 for v in data.get("viewing") or [] if v.get("views", 0) >= 2), "firm(s) opened their preview 2+ times - ring them"),
        (len(data.get("replied") or []), "repl(ies) waiting"),
        (quotes, "quote(s) open"),
        (to_email, "firm(s) waiting for a first email"),
    ]
    lines = [f"• {n} {what}" for n, what in rows if n]
    return "☀️ Today:\n" + ("\n".join(lines) if lines else "• Nothing waiting - a good day to find a new list.")


def week(outreach: Path, views: dict | None, today: date) -> str:
    """This week (the last 7 days) against the 7 before."""
    import email_batches as eb
    import scorecard

    rows = scorecard.gather(outreach, views, today)
    calls = eb._rows(outreach / "calls.csv")[1]

    def span(start: date, end: date) -> dict:
        sent = [r for r in rows if r["sent"] and start <= r["sent"] < end]
        made = [c for c in calls if start.isoformat() <= (c.get("at") or "")[:10] < end.isoformat()]
        return {
            "sent": len(sent),
            "opened": sum(bool(r["opened"]) for r in sent) if views is not None else None,
            "replied": sum(bool(r["replied"]) for r in sent),
            "calls": len(made),
            "conversations": sum(1 for c in made if c.get("outcome") in scorecard.SPOKE),
            "won": sum(1 for c in made if c.get("outcome") == "Won"),
        }

    now, before = span(today - timedelta(days=6), today + timedelta(days=1)), span(today - timedelta(days=13), today - timedelta(days=6))

    def cell(k: str) -> str:
        if now[k] is None:
            return ""
        diff = now[k] - before[k]
        return f"{k} {now[k]} ({'+' if diff > 0 else ''}{diff})"

    parts = [c for c in (cell(k) for k in now) if c]
    return "📈 This week vs last: " + " · ".join(parts)


def asked(outreach: Path) -> set[str]:
    path = outreach / ASKED
    if not path.exists():
        return set()
    with path.open(encoding="utf-8") as f:
        return {r["site"] for r in csv.DictReader(f) if r.get("site")}


def mark_asked(outreach: Path, site: str, today: date) -> None:
    path = outreach / ASKED
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["site", "asked"])
        w.writerow([site, today.isoformat()])


def referrals_due(outreach: Path, today: date) -> list[dict]:
    path = outreach / "case-studies.csv"
    if not path.exists():
        return []
    done = asked(outreach)
    out = []
    with path.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                launched = date.fromisoformat((r.get("launched") or "")[:10])
            except ValueError:
                continue
            if (today - launched).days >= REFERRAL_AFTER_DAYS and r.get("new_site") and r["new_site"] not in done:
                out.append(r)
    return out


def referral_text(row: dict, site_url: str, review_link: str = "") -> str:
    better = ""
    try:
        before, after = int(float(row.get("score_before") or "")), int(float(row.get("score_after") or ""))
        better = f" (from {before} to {after} on Google's phone test)"
    except ValueError:
        pass
    refer = (f"If you know another trade who needs a site, send them {site_url}/refer - they get 15% off, "
             "and you get 10% off a future build (or cash) once they've paid for theirs.")
    if review_link:
        asks = ("Two small favours, if you're happy with it:\n\n"
                f"1. A Google review - two lines on how it went makes a real difference to a new business: {review_link}\n"
                f"2. {refer}")
    else:
        asks = f"One small favour, if you're happy with it: {refer}"
    return f"Hi - it's been a month since {row.get('new_site')} went live{better}. {asks}\n\nThanks again."
