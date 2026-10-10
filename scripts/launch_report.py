"""Before-and-after launch report: what their old site measured, and what the new one does now.

    python scripts/launch_report.py --old kerrroofing.co.uk [--new kerrroofing.co.uk]

The "before" is what was measured when you first contacted them - kept on the
dashboard (their preview page's data) and in outreach/teardown-log.csv - so it
still works when the new site has replaced the old one on the same domain.
The "after" is measured now: Google's mobile test three times (the middle
result is used, so one lucky run can't flatter it) plus the same homepage
checks the preview pages use.

Writes, for the firm:
    outreach/sites/<firm>/launch-report.html   a one-page report for the client (prints to PDF)
    outreach/case-studies.csv                  one line per launch - your proof, for your own site
                                               (ask the client before naming them publicly)

Needs PAGESPEED_API_KEY; PROSPECTS_API_SECRET for the full "before" from the dashboard.
"""

from __future__ import annotations

import argparse
import csv
import html as htmllib
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from findings import all_issues  # noqa: E402
from push_prospects import domain_of, make_slug  # noqa: E402

CASE_FIELDS = ["business", "trade", "area", "launched", "old_site", "new_site", "score_before", "score_after",
               "lcp_before", "lcp_after", "weight_before_kb", "weight_after_kb", "fixed", "report"]


def outreach_dir() -> Path:
    import workspace

    return workspace.outreach_dir()


def find_business(outreach: Path, domain: str) -> dict:
    """The firm's row (Business, Trade, Area) from whichever sheet lists that website."""
    import openpyxl

    for path in sorted(outreach.glob("*.xlsx")):
        if path.name.startswith("~$") or path.name == "outreach-results.xlsx":
            continue
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        except Exception:  # open in Excel, not a sheet
            continue
        try:
            for ws in wb.worksheets:
                rows = ws.iter_rows(values_only=True)
                header = [str(h).strip() if h else "" for h in next(rows, [])]
                for values in rows:
                    row = dict(zip(header, values))
                    if domain_of(str(row.get("Website") or "")) == domain and str(row.get("Business") or "").strip():
                        return {k: str(row.get(k) or "").strip() for k in ("Business", "Trade", "Area")}
        finally:
            wb.close()
    return {}


def before_from_dashboard(settings: dict, business: str, domain: str) -> dict | None:
    secret = settings.get("PROSPECTS_API_SECRET", "")
    if len(secret) < 32 or not business:
        return None
    api = (settings.get("DASHBOARD_API_URL") or "https://admin.scalardigital.co.uk").rstrip("/")
    req = urllib.request.Request(f"{api}/api/prospects/{make_slug(business, domain, secret)}",
                                 headers={"Authorization": f"Bearer {secret}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read()).get("prospect")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def before_from_log(outreach: Path, domain: str) -> dict:
    path = outreach / "teardown-log.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return next((r for r in csv.DictReader(f) if r.get("website") == domain), {})


def _num(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def measure_after(domain: str, api_key: str, runs: int = 3) -> dict:
    """The new site now: homepage checks once, Google's mobile test `runs` times - the median score and load time."""
    from site_teardown import run_pagespeed, teardown

    first = teardown(domain, api_key) or {"v": 1, "checks": {}}
    scores = [first.get("_mobile_score")] if first.get("_mobile_score") is not None else []
    lcps = [first.get("_lcp_s")] if first.get("_lcp_s") is not None else []
    for _ in range(runs - 1):
        extra = run_pagespeed(f"https://{domain}/", api_key)
        if extra.get("_mobile_score") is not None:
            scores.append(extra["_mobile_score"])
        if extra.get("_lcp_s") is not None:
            lcps.append(extra["_lcp_s"])
    first["_mobile_score"] = round(statistics.median(scores)) if scores else None
    first["_lcp_s"] = round(statistics.median(lcps), 1) if lcps else None
    first["_runs"] = len(scores)
    return first


def _key(issue: str) -> str:
    """An issue with its numbers taken out, so "images could be 2.1 MB lighter" matches "... 0.6 MB lighter"."""
    return re.sub(r"[\d.,]+(\s*(KB|MB|s)\b)?", "#", issue)


def compare(before: dict, after: dict, before_year: int, after_year: int) -> dict:
    was = all_issues(before.get("teardown"), before_year)
    now = all_issues(after, after_year)
    now_keys = {_key(i) for i in now}
    return {
        "score": (_num(before.get("mobile_score")), _num(after.get("_mobile_score"))),
        "lcp": (_num(before.get("lcp_s")), _num(after.get("_lcp_s"))),
        "weight": (_num((before.get("teardown") or {}).get("pageWeightKb")), _num(after.get("pageWeightKb"))),
        "seo": (_num((before.get("teardown") or {}).get("seoScore")), _num(after.get("seoScore"))),
        "access": (_num((before.get("teardown") or {}).get("accessibilityScore")), _num(after.get("accessibilityScore"))),
        "fixed": [i for i in was if _key(i) not in now_keys],
        "still": now,
        "top_issue_before": before.get("top_issue") or "",
    }


def _fmt(v: float | None, kind: str) -> str:
    if v is None:
        return "-"
    if kind == "lcp":
        return f"{v:.1f}s"
    if kind == "weight":
        return f"{v / 1000:.1f} MB" if v >= 1000 else f"{round(v)} KB"
    return str(round(v))


def report_html(business: str, old: str, new: str, c: dict, checked_before: str, runs: int, today: date) -> str:
    esc = htmllib.escape
    rows = []
    for key, label, better in (("score", "Google mobile speed score (out of 100)", "up"), ("lcp", "Time until the page shows on a phone", "down"),
                               ("weight", "Page size to download", "down"), ("seo", "Google SEO check (out of 100)", "up"),
                               ("access", "Accessibility check (out of 100)", "up")):
        b, a = c[key]
        if a is None and b is None:
            continue
        improved = b is not None and a is not None and ((a > b) if better == "up" else (a < b))
        rows.append(f'<tr><td>{esc(label)}</td><td class="b">{_fmt(b, key)}</td><td class="a{" win" if improved else ""}">{_fmt(a, key)}</td></tr>')
    fixed = "".join(f"<li>{esc(i[0].upper() + i[1:])}</li>" for i in c["fixed"])
    if not fixed and c["top_issue_before"]:
        fixed = f"<li>{esc(c['top_issue_before'][0].upper() + c['top_issue_before'][1:])}</li>"
    still = "".join(f"<li>{esc(i[0].upper() + i[1:])}</li>" for i in c["still"])
    headline = ""
    b, a = c["score"]
    if b is not None and a is not None:
        headline = f"Speed score {round(b)} &rarr; {round(a)}"
        lb, la = c["lcp"]
        if lb is not None and la is not None and la < lb:
            headline += f", showing in {la:.1f}s instead of {lb:.1f}s"
    return f"""<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(business)} - your new website, before and after</title>
<style>
body {{ margin: 0; font: 16px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: #1c1f23; background: #f5f6f8; }}
.page {{ max-width: 760px; margin: 24px auto; background: #fff; padding: 40px; border-radius: 14px; }}
.eyebrow {{ font-size: 12px; letter-spacing: .12em; text-transform: uppercase; color: #5b636d; }}
h1 {{ font-size: 30px; line-height: 1.2; margin: 6px 0 4px; }}
.headline {{ font-size: 20px; color: #0a7a3d; font-weight: 700; margin: 10px 0 24px; }}
table {{ width: 100%; border-collapse: collapse; margin: 8px 0 28px; }}
th, td {{ text-align: left; padding: 12px 8px; border-bottom: 1px solid #e3e6ea; }}
th {{ font-size: 12px; text-transform: uppercase; letter-spacing: .08em; color: #5b636d; }}
td.b {{ color: #8a929c; }} td.a {{ font-weight: 700; }} td.win {{ color: #0a7a3d; }}
h2 {{ font-size: 18px; margin: 24px 0 8px; }}
li {{ margin: 4px 0; }}
ul.fixed {{ list-style: none; padding-left: 0; }}
ul.fixed li::before {{ content: "\\2713"; color: #0a7a3d; font-weight: 700; margin-right: 10px; }}
.note {{ font-size: 13px; color: #5b636d; border-top: 1px solid #e3e6ea; margin-top: 28px; padding-top: 14px; }}
@media print {{ body {{ background: #fff; }} .page {{ margin: 0; padding: 0; }} }}
@media (max-width: 600px) {{ .page {{ padding: 22px; margin: 0; border-radius: 0; }} }}
</style></head><body><div class="page">
<p class="eyebrow">Launch report · {today.strftime("%d %B %Y")}</p>
<h1>{esc(business)}: your new website, before and after</h1>
<p>{esc(old)} before, measured {esc(checked_before) or "when we first looked"} &middot; {esc(new)} now</p>
{f'<p class="headline">{headline}</p>' if headline else ""}
<table><thead><tr><th></th><th>Before</th><th>Now</th></tr></thead><tbody>{"".join(rows)}</tbody></table>
{f'<h2>What was wrong with the old site - now fixed</h2><ul class="fixed">{fixed}</ul>' if fixed else ""}
{f"<h2>Still worth doing</h2><ul>{still}</ul>" if still else "<h2>Still worth doing</h2><p>Nothing flagged by these checks.</p>"}
<p class="note">Measured with Google PageSpeed Insights on mobile (the middle of {runs} runs today) and a check of the public homepage -
the same tests used before. Scores move a little from run to run; you can re-run Google's test yourself at pagespeed.web.dev.</p>
</div></body></html>
"""


def case_study_snippet(business: str, trade: str, area: str, launched: str, site: str, c: dict) -> str | None:
    """The launch as an entry for lib/case-studies.ts, ready to paste - or None if a number is missing.

    permission starts false: the site only shows it once the client has said yes."""
    (sb, sa), (lb, la) = c["score"], c["lcp"]
    if None in (sb, sa, lb, la):
        return None
    fixed = [i[0].upper() + i[1:] for i in c["fixed"]][:4]
    return "\n".join([
        "  {",
        f"    business: {json.dumps(business)},",
        f"    trade: {json.dumps(trade or 'TRADE')},",
        f"    area: {json.dumps(area or 'AREA')},",
        f"    launched: {json.dumps(launched)},",
        f"    site: {json.dumps(site)},",
        f"    scoreBefore: {round(sb)},",
        f"    scoreAfter: {round(sa)},",
        f"    loadBefore: {round(lb, 1)},",
        f"    loadAfter: {round(la, 1)},",
        f"    fixed: {json.dumps(fixed)},",
        "    permission: false, // true once they've agreed to be named",
        "  },",
    ])


def record_case_study(outreach: Path, row: dict) -> None:
    path = outreach / "case-studies.csv"
    rows = []
    if path.exists():
        with path.open(encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if r.get("new_site") != row["new_site"]]
    rows.append(row)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CASE_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--old", required=True, help="their website when you first contacted them")
    ap.add_argument("--new", help="the new site (default: the same domain)")
    ap.add_argument("--business", help="only needed if the website isn't in any sheet")
    args = ap.parse_args()
    old, new = domain_of(args.old), domain_of(args.new or args.old)
    if not old or not new:
        sys.exit("Give the websites as domains, e.g. kerrroofing.co.uk")
    key = os.environ.get("PAGESPEED_API_KEY", "")
    if not key:
        sys.exit("Add PAGESPEED_API_KEY in Settings first.")
    outreach = outreach_dir()
    settings = {k: os.environ.get(k, "") for k in ("PROSPECTS_API_SECRET", "DASHBOARD_API_URL")}

    firm = find_business(outreach, old)
    business = args.business or firm.get("Business") or ""
    if not business:
        sys.exit(f"{old} isn't in any sheet in outreach/ - add --business \"Their Name\".")
    print(f"{business}: getting the 'before' from when {old} was first checked ...", flush=True)
    before = before_from_dashboard(settings, business, old)
    if before:
        checked = before.get("teardown_at") or ""
    else:
        log = before_from_log(outreach, old)
        if not log:
            sys.exit(f"No earlier measurement of {old} found - a before-and-after needs the original speed check.")
        before = {"mobile_score": log.get("mobile_score"), "lcp_s": log.get("lcp_s"), "top_issue": log.get("top_issue")}
        checked = log.get("checked_at") or ""
        print("  (the dashboard didn't have it - using your local speed-check log, which has the score but not every check)")
    try:
        before_year = datetime.fromisoformat(checked.replace("Z", "+00:00")).year if checked else date.today().year
        checked_label = datetime.fromisoformat(checked.replace("Z", "+00:00")).strftime("%d %B %Y") if checked else ""
    except ValueError:
        before_year, checked_label = date.today().year, ""

    print(f"Measuring {new} now: Google's mobile test three times, and the homepage checks (a minute or two) ...", flush=True)
    after = measure_after(new, key)
    if after.get("_mobile_score") is None:
        sys.exit(f"Google's test couldn't reach {new} - is the new site live? Try again in a few minutes.")
    today = date.today()
    c = compare(before, after, before_year, today.year)

    from site_draft import _slugify

    folder = outreach / "sites" / _slugify(business)
    folder.mkdir(parents=True, exist_ok=True)
    report = folder / "launch-report.html"
    report.write_text(report_html(business, old, new, c, checked_label, after.get("_runs") or 1, today), encoding="utf-8")
    record_case_study(outreach, {
        "business": business, "trade": (before.get("trade") or firm.get("Trade") or ""), "area": (before.get("area") or firm.get("Area") or ""),
        "launched": today.isoformat(), "old_site": old, "new_site": new,
        "score_before": _fmt(c["score"][0], "score"), "score_after": _fmt(c["score"][1], "score"),
        "lcp_before": _fmt(c["lcp"][0], "lcp"), "lcp_after": _fmt(c["lcp"][1], "lcp"),
        "weight_before_kb": _fmt(c["weight"][0], "score"), "weight_after_kb": _fmt(c["weight"][1], "score"),
        "fixed": "; ".join(c["fixed"]), "report": str(report.relative_to(outreach)),
    })
    b, a = c["score"]
    print(f"Speed score {_fmt(b, 'score')} -> {_fmt(a, 'score')}; loads in {_fmt(c['lcp'][1], 'lcp')} (was {_fmt(c['lcp'][0], 'lcp')}); "
          f"{len(c['fixed'])} problem(s) fixed, {len(c['still'])} still flagged.")
    print(f"READY: {report.relative_to(outreach)} - send it to them (open it and print to PDF). Added to case-studies.csv.")
    snippet = case_study_snippet(business, before.get("trade") or firm.get("Trade") or "", before.get("area") or firm.get("Area") or "",
                                 today.isoformat(), new, c)
    if snippet:
        print("\nFor your website's results section - once they're happy to be named, paste this into")
        print("CASE_STUDIES in lib/case-studies.ts and set permission to true:\n")
        print(snippet)
    if a is not None and a < 90:
        print("  NOTE: under 90 - worth fixing before you send it (images, fonts, third-party scripts are the usual causes).")


if __name__ == "__main__":
    main()
