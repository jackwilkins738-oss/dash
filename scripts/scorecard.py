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

Also a weekly funnel (each week's sends followed through: opened, replied,
keen, quoted, won - where they drop out) and an experiment board: replies by
send time (recorded from panel v66 on) and by how slow their site was.

Small numbers mislead: a version isn't called better until each has 100+
sends and at least 5 replies between them; a send time or score band needs
50+ sends in each group compared.
"""

from __future__ import annotations

import re
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
    scores: dict[str, int] = {}
    for src in eb.sources(outreach, None):
        for r in eb._rows(src)[1]:
            if r.get("email"):
                trades[_lower(r["email"])] = (r.get("trade") or "").strip() or "Unknown"
                try:
                    scores[_lower(r["email"])] = int(float(r.get("mobile_score") or ""))
                except ValueError:
                    pass
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
            "hour": int(r["sent_at"][:2]) if re.fullmatch(r"\d{2}:\d{2}", r.get("sent_at") or "") else None,
            "score": scores.get(email),
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


MIN_GROUP = 50  # sends in each of the two groups being compared before one is called better


def compare(title: str, groups: dict[str, list[dict]]) -> list[str]:
    """One line per group, then a verdict that stays "not enough data" until a difference is real -
    so a hunch about 7am vs lunchtime isn't settled by 12 emails."""
    groups = {k: v for k, v in groups.items() if v}
    if len(groups) < 2:
        return []
    out = [f"{title}:"] + [f"  {line(k, v)}" for k, v in groups.items()]
    big = sorted((k for k, v in groups.items() if len(v) >= MIN_GROUP),
                 key=lambda k: -sum(bool(r["replied"]) for r in groups[k]) / len(groups[k]))
    replies = sum(bool(r["replied"]) for v in groups.values() for r in v)
    if len(big) < 2 or replies < MIN_REPLIES:
        out.append(f"  Not enough data yet - needs {MIN_GROUP}+ sends in at least two groups and {MIN_REPLIES}+ replies.")
        return out
    best, next_ = big[0], big[1]
    rb, rn = (sum(bool(r["replied"]) for r in groups[k]) for k in (best, next_))
    rate_b, rate_n = rb / len(groups[best]), rn / len(groups[next_])
    if rate_b >= 1.5 * rate_n and rb - rn >= 3:
        out.append(f"  {best} is clearly getting more replies.")
    else:
        out.append("  No clear difference yet - within normal chance.")
    return out


def hour_band(h: int) -> str:
    return "Before 9am" if h < 9 else "9am-12" if h < 12 else "12-5pm" if h < 17 else "After 5pm"


def score_band(s: int) -> str:
    return "Score under 30" if s < 30 else "Score 30-49" if s < 50 else "Score 50-69" if s < 70 else "Score 70+"


def experiments(rows: list[dict]) -> list[str]:
    """Replies by send time and by how slow their site was - what to change next."""
    out = []
    by_hour: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("hour") is not None:
            by_hour.setdefault(hour_band(r["hour"]), []).append(r)
    out += compare("By send time", {k: by_hour.get(k, []) for k in ("Before 9am", "9am-12", "12-5pm", "After 5pm")})
    by_score: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("score") is not None:
            by_score.setdefault(score_band(r["score"]), []).append(r)
    out += compare("By their mobile score", {k: by_score.get(k, []) for k in ("Score under 30", "Score 30-49", "Score 50-69", "Score 70+")})
    return out


def funnel(rows: list[dict], today: date, weeks: int = 4) -> list[str]:
    """Each week's sends, followed through: where do they drop out?"""
    out = []
    start = today - timedelta(days=today.weekday())
    for w in range(weeks):
        monday = start - timedelta(weeks=w)
        week = [r for r in rows if r["sent"] and monday <= r["sent"] < monday + timedelta(days=7)]
        if not week:
            continue
        steps = [f"{len(week)} sent"]
        if any(r["opened"] is not None for r in week):
            steps.append(f"{sum(bool(r['opened']) for r in week)} opened")
        steps += [f"{sum(bool(r[k]) for r in week)} {label}" for k, label in
                  (("replied", "replied"), ("keen", "keen"), ("quoted", "quoted"), ("won", "won"))]
        out.append(f"  w/c {monday:%d %b}: " + " -> ".join(steps))
    return (["Weekly funnel (each week's sends, followed through):"] + out) if out else []


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


def objections(outreach: Path, today: date | None = None, days: int = 90) -> str:
    """'What's holding people back' across recent replies - tagged at reply check (or now, for older replies)."""
    from reply_scanner import OBJECTION_LABELS, objection

    since = ((today or date.today()) - timedelta(days=days)).isoformat()
    counts: dict[str, int] = {}
    replies = 0
    for r in eb._rows(outreach / "replies.csv")[1]:
        if r.get("kind") not in REPLY_KINDS or (r.get("date") or "")[:10] < since:
            continue
        replies += 1
        tag = r.get("objection") or objection(r.get("message") or r.get("snippet") or "")
        if tag:
            counts[tag] = counts.get(tag, 0) + 1
    if not counts:
        return ""
    top = sorted(counts.items(), key=lambda kv: -kv[1])
    text = " · ".join(f"{OBJECTION_LABELS.get(k, k)} {n}" for k, n in top)
    out = f"What's holding people back ({replies} replies, last {days} days): {text}"
    if replies >= 15 and top[0][1] >= 3:
        out += f" - most common: {OBJECTION_LABELS.get(top[0][0], top[0][0])}. Answer it in the email before they raise it."
    return out


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
    out += funnel(rows, today)
    out += experiments(rows)
    out += domains(rows)
    out += money(outreach, rows)
    held = objections(outreach, today)
    if held:
        out.append(held)
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
