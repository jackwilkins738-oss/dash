"""The outreach scorecard: what's working, in numbers.

    python scripts/scorecard.py

From what's already recorded on this computer (emails-sent.csv, replies.csv,
calls.csv, quotes-sent.csv) and who opened their preview (the dashboard), for
every email sent:

    opened    they opened their preview page
    replied   they wrote back (bounces and out-of-office don't count)
    keen      the reply read as interested
    quoted    you sent them a quote
    won       you logged Won for them, or they accepted their quote online

...split by email version (A/B - see the panel's "Version B"), by trade, and
for the last 7 days, and by sending domain - with a warning when one is
bouncing too much or getting far fewer replies than the others (a sign it's
landing in spam), so a burnt domain is caught before it drags the rest
down. Then the money - what's been quoted and won, and how
many emails it takes to win a job - your letters (who scanned the code), and
your calls, and how many were real conversations. The autopilot texts it to
you every Monday.

Small numbers mislead: a version isn't called better until each has 100+
sends and at least 5 replies between them.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import email_batches as eb  # noqa: E402

REPLY_KINDS = {"interested", "read it", "not interested"}
BOUNCE_WARN, BOUNCE_STOP = 0.03, 0.05  # the usual danger lines for cold email
MIN_DOMAIN_SENT = 100
SPOKE = {"Replied to them", "Interested", "Quoted", "Not interested", "Won", "Call back"}
MIN_SENT, MIN_REPLIES = 100, 5


def _lower(s: str | None) -> str:
    return (s or "").strip().lower()


def gather(outreach: Path, views: dict[str, dict] | None, today: date | None = None) -> list[dict]:
    """One row per firm emailed, with what happened since."""
    today = today or date.today()
    trades: dict[str, str] = {}
    for src in eb.sources(outreach, None):
        for r in eb._rows(src)[1]:
            if r.get("email"):
                trades[_lower(r["email"])] = (r.get("trade") or "").strip() or "Unknown"
    replied_from, replied_names, keen_from, keen_names = set(), set(), set(), set()
    bounced = {_lower(r.get("from")) for r in eb._rows(outreach / "replies.csv")[1] if r.get("kind") == "bounce"}
    for r in eb._rows(outreach / "replies.csv")[1]:
        if r.get("kind") not in REPLY_KINDS:
            continue
        replied_from.add(_lower(r.get("from")))
        replied_names.add(_lower(r.get("business")))
        if r.get("kind") == "interested":
            keen_from.add(_lower(r.get("from")))
            keen_names.add(_lower(r.get("business")))
    quoted = {_lower(r.get("business")) for r in eb._rows(outreach / "quotes-sent.csv")[1]}
    won = {_lower(r.get("business")) for r in eb._rows(outreach / "calls.csv")[1] if r.get("outcome") == "Won"}
    # A quote accepted online marks their prospect "won" on the dashboard - no call needed.
    won_slugs = {slug for slug, v in (views or {}).items() if v.get("status") == "won"}

    out = []
    for r in eb._rows(outreach / eb.SENT)[1]:
        email, name = _lower(r.get("email")), _lower(r.get("business"))
        if not email:
            continue
        slug = eb._slug(r.get("preview_url", ""))
        opened = None if views is None else bool(((views.get(slug) or {}).get("view_count") or 0) > 0)
        try:
            sent = date.fromisoformat(r.get("sent") or "")
        except ValueError:
            sent = None
        out.append({
            "email": email, "business": name, "sent": sent, "trade": trades.get(email, "Unknown"),
            "variant": (r.get("variant") or "").strip() or "-",
            "inbox": _lower(r.get("sent_from")),
            "bounced": email in bounced,
            "opened": opened,
            "replied": email in replied_from or (name and name in replied_names),
            "keen": email in keen_from or (name and name in keen_names),
            "quoted": bool(name) and name in quoted,
            "won": (bool(name) and name in won) or slug in won_slugs,
        })
    return out


def _pct(n: int, d: int) -> str:
    return f"{100 * n / d:.0f}%" if d else "-"


def line(label: str, rows: list[dict]) -> str:
    n = len(rows)
    opened = [r for r in rows if r["opened"] is not None]
    parts = [f"{label}: {n} sent"]
    if opened:
        parts.append(f"{_pct(sum(r['opened'] for r in opened), len(opened))} opened")
    parts.append(f"{_pct(sum(bool(r['replied']) for r in rows), n)} replied ({sum(bool(r['replied']) for r in rows)})")
    keen, quoted, won = (sum(bool(r[k]) for r in rows) for k in ("keen", "quoted", "won"))
    if keen:
        parts.append(f"{keen} keen")
    if quoted:
        parts.append(f"{quoted} quoted")
    if won:
        parts.append(f"{won} won")
    return " · ".join(parts)


def verdict(rows: list[dict]) -> str:
    a = [r for r in rows if r["variant"] == "A"]
    b = [r for r in rows if r["variant"] == "B"]
    if not b:
        return ""
    ra, rb = sum(bool(r["replied"]) for r in a), sum(bool(r["replied"]) for r in b)
    if min(len(a), len(b)) < MIN_SENT or ra + rb < MIN_REPLIES:
        return f"Too early to pick a winner - wait for {MIN_SENT}+ sent each and {MIN_REPLIES}+ replies in total."
    rate_a, rate_b = ra / len(a), rb / len(b)
    if max(rate_a, rate_b) < 1.5 * min(rate_a, rate_b) or abs(ra - rb) < 3:
        return "No clear winner yet - the two versions are within normal chance of each other."
    best = "B" if rate_b > rate_a else "A"
    return f"Version {best} is getting clearly more replies - make it the main email, and test a new B against it."


def domains(rows: list[dict]) -> list[str]:
    """Sends, bounces and replies per sending domain, and a plain warning when one is in trouble."""
    by: dict[str, list[dict]] = {}
    for r in rows:
        dom = r["inbox"].split("@")[-1] if r["inbox"] else "main inbox"  # older sends didn't record it
        by.setdefault(dom, []).append(r)
    if len(by) < 2 and not any(r["bounced"] for r in rows):
        return []
    out, rates = [], {}
    for dom, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        n = len(rs)
        bounces = sum(bool(r["bounced"]) for r in rs)
        replies = sum(bool(r["replied"]) for r in rs)
        rates[dom] = (n, replies / n if n else 0)
        line = f"{dom}: {n} sent · {_pct(bounces, n)} bounced ({bounces}) · {_pct(replies, n)} replied ({replies})"
        if n >= 20 and bounces / n >= BOUNCE_STOP:
            line += " - STOP sending from it: clean the list (Check emails) and rest it for a week"
        elif n >= 20 and bounces / n >= BOUNCE_WARN:
            line += " - bounces are high: run Check emails before the next batch"
        out.append(line)
    big = {d: r for d, (n, r) in rates.items() if n >= MIN_DOMAIN_SENT}
    if len(big) >= 2:
        best = max(big.values())
        for d, rate in big.items():
            if best > 0 and rate < best / 2:
                out.append(f"{d} gets under half the replies of your best domain - it may be landing in spam. "
                           "Send it a test at mail-tester.com and slow it down until it recovers.")
    return ["By sending domain:"] + ["  " + x for x in out]


def _money(pounds: float) -> str:
    return f"£{pounds:,.0f}"


def money(outreach: Path, rows: list[dict]) -> list[str]:
    """What's been quoted and won in pounds (each firm's latest quote), and emails sent per job won."""
    latest: dict[str, float] = {}
    for r in eb._rows(outreach / "quotes-sent.csv")[1]:
        try:
            latest[_lower(r.get("business"))] = float(r.get("total") or 0)
        except ValueError:
            continue
    if not latest:
        return []
    won = {r["business"] for r in rows if r["won"]}
    won_value = sum(v for k, v in latest.items() if k in won)
    out = [f"Money: {_money(sum(latest.values()))} quoted to {len(latest)} firm{'s' if len(latest) != 1 else ''}"
           + (f", {_money(won_value)} won from {len(won & latest.keys())}" if won_value else ", none won yet")]
    wins = sum(bool(r["won"]) for r in rows)
    if wins:
        out.append(f"One job won for every {round(len(rows) / wins)} emails sent")
    return out


def letters(views: dict[str, dict] | None) -> str:
    """Letters can't be tracked like emails - but a scan of the QR code is a view of their preview."""
    sent = [v for v in (views or {}).values() if v.get("channel") == "letter"]
    if not sent:
        return ""
    scanned = sum(1 for v in sent if (v.get("view_count") or 0) > 0)
    won = sum(1 for v in sent if v.get("status") == "won")
    return f"Letters: {len(sent)} sent · {_pct(scanned, len(sent))} scanned the code ({scanned})" + (f" · {won} won" if won else "")


def scorecard(outreach: Path, views: dict[str, dict] | None, today: date | None = None) -> list[str]:
    today = today or date.today()
    rows = gather(outreach, views, today)
    if not rows:
        return ["No emails sent yet - nothing to score."]
    out = [line("All time", rows)]
    week = [r for r in rows if r["sent"] and r["sent"] > today - timedelta(days=7)]
    if week:
        out.append(line("Last 7 days", week))
    if any(r["variant"] == "B" for r in rows):
        for v in ("A", "B"):
            out.append(line(f"Version {v}", [r for r in rows if r["variant"] == v]))
        out.append(verdict(rows))
    by_trade: dict[str, list[dict]] = {}
    for r in rows:
        by_trade.setdefault(r["trade"], []).append(r)
    if len(by_trade) > 1:
        for trade, rs in sorted(by_trade.items(), key=lambda kv: -len(kv[1])):
            out.append(line(trade, rs))
    out += domains(rows)
    out += money(outreach, rows)
    if letters(views):
        out.append(letters(views))
    calls = [r for r in eb._rows(outreach / "calls.csv")[1] if (r.get("at") or "")[:10] > (today - timedelta(days=7)).isoformat()]
    if calls:
        spoke = sum(1 for r in calls if r.get("outcome") in SPOKE)
        out.append(f"Calls in the last 7 days: {len(calls)}, real conversations: {spoke}")
    if views is None:
        out.append("(Couldn't ask the dashboard who opened their preview, so 'opened' is left out.)")
    return out


def main() -> None:
    outreach = eb.outreach_dir()
    for text in scorecard(outreach, eb.preview_views()):
        print(text)


if __name__ == "__main__":
    main()
