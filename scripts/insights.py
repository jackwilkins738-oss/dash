"""Insights: every email you've sent, joined with everything that happened after, cut every useful way.

    python scripts/insights.py            (or the panel's Results tab -> Insights)

Writes outreach/insights.txt - counts and percentages only: no names, emails or websites, so it's
safe to paste anywhere (e.g. to Claude) for advice on what to change.

For each email: did they open the preview, really read it (30s+ or reached the price), reply, sound
keen, tap a button, get a quote, become a client - split by trade, area, site speed, the worst issue
named, first line, subject, version, send time, weekday, inbox, company type and age, Google reviews,
list source, follow-up, and more. A group is only called better or worse than average when the gap
is bigger than chance (95% interval); everything else is noise and says so.
"""

from __future__ import annotations

import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import email_batches as eb  # noqa: E402

FILE = "insights.txt"
MIN_GROUP = 15  # smaller groups are listed but never called better or worse
STEPS = [("viewed", "opened preview"), ("engaged", "read it"), ("replied", "replied"), ("keen", "keen"),
         ("tapped", "tapped a button"), ("quoted", "quoted"), ("won", "won")]


def _lower(s) -> str:
    return str(s or "").strip().lower()


def wilson(k: int, n: int) -> tuple[float, float]:
    if not n:
        return 0.0, 1.0
    z, p = 1.96, k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - m) / d, (c + m) / d


def _when(s) -> datetime | None:
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def sheet_facts(outreach: Path) -> dict[str, dict]:
    """email -> the list's own columns about the firm (company type, incorporated, reviews, source...)."""
    import openpyxl

    out: dict[str, dict] = {}
    for path in sorted(outreach.glob("*.xlsx")):
        if path.name.startswith("~$") or path.name in ("outreach-results.xlsx",) or path.name.endswith(".tmp.xlsx"):
            continue
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        except Exception:  # noqa: BLE001 - open in Excel: the rest still count
            continue
        try:
            for ws in wb.worksheets:
                rows = ws.iter_rows(values_only=True)
                header = [str(h).strip() if h else "" for h in next(rows, ())]
                if "Email" not in header:
                    continue
                for values in rows:
                    row = dict(zip(header, values))
                    e = _lower(row.get("Email"))
                    if e and e not in out:
                        out[e] = {**row, "_list": path.name}
        finally:
            wb.close()
    return out


def band_score(s) -> str:
    try:
        s = int(float(s))
    except (TypeError, ValueError):
        return "unknown"
    return "under 30" if s < 30 else "30-49" if s < 50 else "50-69" if s < 70 else "70+"


def band_lcp(s) -> str:
    try:
        s = float(s)
    except (TypeError, ValueError):
        return "unknown"
    return "under 2.5s" if s < 2.5 else "2.5-4s" if s < 4 else "4-8s" if s < 8 else "8s+"


def band_age(incorporated, today: date) -> str:
    try:
        d = date.fromisoformat(str(incorporated)[:10])
    except ValueError:
        return "unknown (sole trader?)"
    y = (today - d).days / 365.25
    return "under 2 years" if y < 2 else "2-5 years" if y < 5 else "5-10 years" if y < 10 else "10+ years"


def band_reviews(n) -> str:
    try:
        n = int(float(n))
    except (TypeError, ValueError):
        return "unknown"
    return "0-9" if n < 10 else "10-49" if n < 50 else "50-149" if n < 150 else "150+"


def band_hour(h) -> str:
    if h is None:
        return "unknown (before send times were kept)"
    return "before 9am" if h < 9 else "9am-12" if h < 12 else "12-5pm" if h < 17 else "after 5pm"


def build(outreach: Path, views: dict[str, dict] | None, today: date | None = None) -> list[dict]:
    """One row per firm emailed, with every fact we have and every outcome."""
    import scorecard

    today = today or date.today()
    base = {r["email"]: r for r in scorecard.gather(outreach, views, today)}
    sent = {_lower(r.get("email")): r for r in eb._rows(outreach / eb.SENT)[1] if r.get("email")}
    mm: dict[str, dict] = {}
    for src in eb.sources(outreach, None):
        for r in eb._rows(src)[1]:
            if r.get("email"):
                mm.setdefault(_lower(r["email"]), r)
    facts = sheet_facts(outreach)
    replies = defaultdict(list)
    for r in eb._rows(outreach / "replies.csv")[1]:
        replies[_lower(r.get("from"))].append(r)
    calls_by_name = defaultdict(list)
    for r in eb._rows(outreach / "calls.csv")[1]:
        calls_by_name[_lower(r.get("business"))].append(r.get("outcome") or "")

    rows = []
    for email, b in base.items():
        s, m, f = sent.get(email, {}), mm.get(email, {}), facts.get(email, {})
        slug = eb._slug(s.get("preview_url", "")) or eb._slug(m.get("preview_url", ""))
        act = (views or {}).get(slug) or {}
        reached = [x for x in (act.get("reached") or []) if isinstance(x, str)]
        seconds = int(act.get("engaged_seconds") or 0)
        sent_day = b["sent"]
        first_view = _when(act.get("first_viewed_at"))
        reply_dates = sorted(d for d in (_when(r.get("date")) for r in replies.get(email, [])) if d)
        follow = s.get("followup_sent") or ""
        first_reply = reply_dates[0] if reply_dates else None
        rows.append({
            **b,
            "views": int(act.get("view_count") or 0),
            "viewed": bool(act.get("view_count")) if views is not None else None,
            "engaged": seconds >= 30 or any(x in reached for x in ("pricing", "rebuilt", "reply")),
            "seconds": seconds,
            "scroll": int(act.get("max_scroll") or 0),
            "reached": reached,
            "tapped": bool(act.get("choice")),
            "choice": act.get("choice") or "",
            "hours_to_view": ((first_view - datetime.combine(sent_day, datetime.min.time())).total_seconds() / 3600
                              if first_view and sent_day else None),
            "days_to_reply": ((first_reply.date() - sent_day).days if first_reply and sent_day else None),
            "replied_after_followup": bool(follow and first_reply and first_reply.date().isoformat() >= follow),
            "followed_up": bool(follow),
            "intent": next((r.get("intent") for r in replies.get(email, []) if r.get("intent")), ""),
            "objection": next((r.get("objection") for r in replies.get(email, []) if r.get("objection")), ""),
            "calls": calls_by_name.get(b["business"], []),
            "dims": {
                "Trade": b["trade"],
                "Area": (m.get("area") or f.get("Area") or "unknown").strip().title() or "unknown",
                "Mobile score": band_score(m.get("mobile_score") or b.get("score")),
                "Load time": band_lcp(m.get("lcp_s")),
                "Worst issue named": (m.get("top_issue") or "none named")[:60],
                "First line": "yes" if (m.get("first_line") or "").strip() else "no",
                "Greeting": "by name" if (m.get("greeting_name") or "there").strip().lower() not in ("", "there") else "generic",
                "Email version": b["variant"],
                "Subject": subject_pattern(s.get("subject") or "", b["business"]),
                "Send time": band_hour(b.get("hour")),
                "Weekday": sent_day.strftime("%A") if sent_day else "unknown",
                "Inbox": (b["inbox"].split("@")[-1] or "unknown"),
                "Company type": str(f.get("Company type") or "unknown"),
                "Company age": band_age(f.get("Incorporated"), today),
                "Google reviews": band_reviews(f.get("Google reviews")),
                "List source": str(f.get("Source") or ("Companies House" if f.get("Company number") else "unknown")),
                "Followed up": "yes" if follow else "no",
            },
        })
    return rows


def subject_pattern(subject: str, business: str) -> str:
    """The subject as a pattern - the firm's own name masked, so the report never names anyone."""
    if not subject:
        return "unknown"
    if business:
        subject = re.sub(re.escape(business), "<firm>", subject, flags=re.I)
    return subject[:60]


def pct(k: int, n: int) -> str:
    return f"{100 * k / n:.0f}%" if n else "-"


def funnel_line(rows: list[dict]) -> str:
    n = len(rows)
    parts = [f"{n} sent"]
    for key, label in STEPS:
        vals = [r[key] for r in rows if r.get(key) is not None]
        if vals:
            parts.append(f"{label} {pct(sum(bool(v) for v in vals), len(vals))}")
    return " | ".join(parts)


def compare(title: str, rows: list[dict], dim: str, metric: str = "replied", min_rows: int = 2) -> list[str]:
    groups = defaultdict(list)
    for r in rows:
        groups[r["dims"][dim]].append(r)
    if len(groups) < min_rows:
        return []
    usable = [r for r in rows if r.get(metric) is not None]
    overall = sum(bool(r[metric]) for r in usable) / len(usable) if usable else 0
    out = [f"{title} (by {dim}; overall {metric} {100 * overall:.1f}%):"]
    for name, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        vals = [r for r in rs if r.get(metric) is not None]
        k, n = sum(bool(r[metric]) for r in vals), len(vals)
        lo, hi = wilson(k, n)
        mark = ""
        if n >= MIN_GROUP:
            mark = "  << BETTER than average" if lo > overall else "  << WORSE than average" if hi < overall else ""
        else:
            mark = "  (too few to judge)"
        out.append(f"  {name[:45]:45} {len(rs):4} sent | viewed {pct(sum(bool(r['viewed']) for r in rs if r['viewed'] is not None), sum(1 for r in rs if r['viewed'] is not None))}"
                   f" | read {pct(sum(r['engaged'] for r in rs), len(rs))} | replied {pct(sum(bool(r['replied']) for r in rs), len(rs))}"
                   f" | keen {sum(bool(r['keen']) for r in rs)} | won {sum(bool(r['won']) for r in rs)}{mark}")
    return out


def report(rows: list[dict], today: date | None = None) -> list[str]:
    today = today or date.today()
    if not rows:
        return ["No emails sent yet - nothing to analyse."]
    out = [f"SCALAR OUTREACH INSIGHTS - {today:%d %B %Y} - {len(rows)} firms emailed",
           "(counts and percentages only - no names, emails or websites)", ""]
    out.append("FUNNEL")
    out.append("  " + funnel_line(rows))
    dated = [r["sent"] for r in rows if r["sent"]]
    if dated:
        out.append(f"  First send {min(dated):%d %b}, last {max(dated):%d %b}; bounced {pct(sum(r['bounced'] for r in rows), len(rows))}")
    h = [r["hours_to_view"] for r in rows if r["hours_to_view"] is not None and r["hours_to_view"] >= 0]
    if h:
        out.append(f"  Time from send day to first view: median {statistics.median(h):.0f}h; "
                   f"{pct(sum(x < 24 for x in h), len(h))} within a day, {pct(sum(x > 72 for x in h), len(h))} after 3+ days")
    d = [r["days_to_reply"] for r in rows if r["days_to_reply"] is not None and r["days_to_reply"] >= 0]
    if d:
        out.append(f"  Days to reply: median {statistics.median(d):.0f}; {pct(sum(x <= 1 for x in d), len(d))} within a day")
    fu = [r for r in rows if r["followed_up"]]
    if fu:
        out.append(f"  Follow-ups: {len(fu)} sent; {sum(r['replied_after_followup'] for r in fu)} replies came after the follow-up "
                   f"({pct(sum(r['replied_after_followup'] for r in fu), sum(bool(r['replied']) for r in rows) or 1)} of all replies)")

    viewers = [r for r in rows if r["viewed"]]
    if viewers:
        out += ["", "WHAT VIEWERS DID (of those who opened their preview)"]
        vc = Counter(min(r["views"], 5) for r in viewers)
        out.append("  Visits: " + ", ".join(f"{k if k < 5 else '5+'}x: {vc[k]}" for k in sorted(vc)))
        secs = [r["seconds"] for r in viewers if r["seconds"]]
        if secs:
            out.append(f"  Time on page (where measured): median {statistics.median(secs):.0f}s; "
                       f"{pct(sum(s < 10 for s in secs), len(secs))} under 10s (glance or link checker), {pct(sum(s >= 60 for s in secs), len(secs))} a minute+")
        sc = [r["scroll"] for r in viewers if r["scroll"]]
        if sc:
            out.append(f"  Scroll depth: median {statistics.median(sc):.0f}%; {pct(sum(s >= 75 for s in sc), len(sc))} reached the bottom quarter")
        reach = Counter(x for r in viewers for x in r["reached"])
        if reach:
            out.append("  Sections reached: " + ", ".join(f"{k} {pct(v, len(viewers))}" for k, v in reach.most_common()))
        taps = Counter(r["choice"] for r in viewers if r["choice"])
        if taps:
            out.append("  One-tap answers: " + ", ".join(f"{k} {v}" for k, v in taps.most_common()))
        rv = [r for r in viewers if r["replied"]]
        out.append(f"  Viewers who replied: {len(rv)} of {len(viewers)} ({pct(len(rv), len(viewers))}); "
                   f"viewed 2+ times with no reply or call yet: {sum(1 for r in viewers if r['views'] >= 2 and not r['replied'] and not r['calls'])} (ring these)")
        if rv and len(viewers) > len(rv):
            def med(rs, key):
                vals = [r[key] for r in rs if r[key]]
                return f"{statistics.median(vals):.0f}" if vals else "-"
            nr = [r for r in viewers if not r["replied"]]
            out.append(f"  Repliers vs non-repliers: time on page {med(rv, 'seconds')}s vs {med(nr, 'seconds')}s; "
                       f"scroll {med(rv, 'scroll')}% vs {med(nr, 'scroll')}%")

    intents = Counter(r["intent"] for r in rows if r["intent"])
    objections = Counter(r["objection"] for r in rows if r["objection"])
    outcomes = Counter(o for r in rows for o in r["calls"])
    if intents or objections or outcomes:
        out += ["", "WHAT PEOPLE SAID"]
        if intents:
            out.append("  Reply intents: " + ", ".join(f"{k} {v}" for k, v in intents.most_common()))
        if objections:
            out.append("  Objections: " + ", ".join(f"{k} {v}" for k, v in objections.most_common()))
        if outcomes:
            out.append("  Call outcomes: " + ", ".join(f"{k} {v}" for k, v in outcomes.most_common()))

    out += ["", "WHAT WORKS - reply rate by each factor (BETTER/WORSE only when beyond chance; groups under "
            f"{MIN_GROUP} sends can't be judged)"]
    dims = list(rows[0]["dims"])
    for dim in dims:
        block = compare("Replies", rows, dim)
        if block:
            out += [""] + block
    if any(r["viewed"] is not None for r in rows):
        out += ["", "WHAT GETS THE PREVIEW OPENED - view rate by the factors the email controls"]
        for dim in ("Subject", "Email version", "First line", "Greeting", "Send time", "Weekday", "Inbox", "Worst issue named"):
            block = compare("Views", rows, dim, metric="viewed")
            if block:
                out += [""] + block

    standouts = []
    usable = [r for r in rows if r["replied"] is not None]
    overall = sum(bool(r["replied"]) for r in usable) / len(usable) if usable else 0
    for dim in dims:
        groups = defaultdict(list)
        for r in rows:
            groups[r["dims"][dim]].append(r)
        for name, rs in groups.items():
            if len(rs) >= MIN_GROUP:
                k = sum(bool(r["replied"]) for r in rs)
                lo, hi = wilson(k, len(rs))
                if lo > overall:
                    standouts.append(f"  + {dim} = {name}: {pct(k, len(rs))} reply ({len(rs)} sent) vs {100 * overall:.1f}% overall")
                elif hi < overall:
                    standouts.append(f"  - {dim} = {name}: {pct(k, len(rs))} reply ({len(rs)} sent) vs {100 * overall:.1f}% overall")
    out += ["", "STANDOUTS (beyond chance)"] + (standouts or ["  None yet - not enough sends for any difference to be real. Keep sending."])
    return out


def main() -> None:
    outreach = eb.outreach_dir()
    rows = build(outreach, eb.preview_views())
    lines = report(rows)
    text = "\n".join(lines) + "\n"
    (outreach / FILE).write_text(text, encoding="utf-8")
    print(text)
    print(f"Saved to {outreach / FILE} - paste it to Claude for advice. No names, emails or websites are in it.")


if __name__ == "__main__":
    main()
