"""Inbox guard: each morning's inbox plan, warmed up and protected automatically.

With "Warm up and protect inboxes" ticked on the Autopilot card, today's number for each inbox is the
smallest of:

    your number         what you set for that inbox (or Emails per inbox)
    its warm-up         10 a day in its first week of sending, +5 each week after - so a new inbox
                        reaches 25 in its fourth week by itself (an inbox with weeks of history is
                        already past it)
    0 if it's in trouble   over 5% of its last 14 days' emails bounced (at least 20 sent), or the
                        daily sending-health check found a problem with its domain (missing SPF/DKIM/
                        DMARC, a blocklisting) - paused until it's clean again, and you're told

Nothing is changed in your settings: it's worked out fresh each morning from what's been sent.
"""

from __future__ import annotations

import csv
from datetime import date, timedelta
from pathlib import Path

WARM_START = 10
WARM_STEP = 5
BOUNCE_LIMIT = 0.05
BOUNCE_MIN_SENT = 20
BOUNCE_DAYS = 14


def _rows(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _day(value: str) -> date | None:
    try:
        return date.fromisoformat((value or "")[:10])
    except ValueError:
        return None


def first_sends(outreach: Path, main: str) -> dict[str, date]:
    out: dict[str, date] = {}
    for r in _rows(outreach / "emails-sent.csv"):
        d = _day(r.get("sent", ""))
        addr = (r.get("sent_from") or main).lower()
        if d and (addr not in out or d < out[addr]):
            out[addr] = d
    return out


def warm_limit(first: date | None, today: date) -> int:
    weeks = 0 if first is None else max(0, (today - first).days // 7)
    return WARM_START + WARM_STEP * weeks


def bounce_rates(outreach: Path, main: str, today: date) -> dict[str, tuple[int, int]]:
    """{inbox: (sent, bounced)} over the last BOUNCE_DAYS days."""
    since = today - timedelta(days=BOUNCE_DAYS)
    bounced = {(r.get("email") or "").lower() for r in _rows(outreach / "email-checks.csv") if r.get("result") == "bounced"}
    bounced |= {(r.get("from") or "").lower() for r in _rows(outreach / "replies.csv") if r.get("kind") == "bounce"}
    out: dict[str, list[int]] = {}
    for r in _rows(outreach / "emails-sent.csv"):
        d = _day(r.get("sent", ""))
        if not d or d < since:
            continue
        addr = (r.get("sent_from") or main).lower()
        tally = out.setdefault(addr, [0, 0])
        tally[0] += 1
        tally[1] += (r.get("email") or "").lower() in bounced
    return {k: (v[0], v[1]) for k, v in out.items()}


def domain_problem(outreach: Path, inbox: str) -> str:
    import sending_health

    domain = inbox.split("@", 1)[-1]
    return next((p for p in sending_health.load(outreach).get("problems") or [] if p.startswith(domain + ":")), "")


def plan_for_today(plan: dict[str, int], outreach: Path, main: str, today: date) -> tuple[dict[str, int], list[str]]:
    """(today's plan, one line per inbox that differs from yours, saying why)."""
    firsts = first_sends(outreach, main)
    rates = bounce_rates(outreach, main, today)
    out, notes = {}, []
    for inbox, wanted in plan.items():
        inbox = inbox.lower()
        sent, bounced = rates.get(inbox, (0, 0))
        problem = domain_problem(outreach, inbox)
        if sent >= BOUNCE_MIN_SENT and bounced / sent > BOUNCE_LIMIT:
            out[inbox] = 0
            notes.append(f"Inbox plan: {inbox} paused - {bounced} of its last {sent} emails bounced ({bounced / sent:.0%}). "
                         "Clean the list (Check emails) before it sends again.")
        elif problem:
            out[inbox] = 0
            notes.append(f"Inbox plan: {inbox} paused - {problem}")
        else:
            limit = warm_limit(firsts.get(inbox), today)
            out[inbox] = min(int(wanted), limit)
            if out[inbox] < int(wanted):
                notes.append(f"Inbox plan: {inbox} warming up - {out[inbox]} today (of your {wanted}); +{WARM_STEP} each week.")
    return out, notes
