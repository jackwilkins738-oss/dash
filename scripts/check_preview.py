"""Check a preview link: what each part of the system knows about that page, and what's wrong.

The panel's "Check a preview link" (Results card). Paste the link from an email; it shows, side by side:

    the dashboard   what the page is built from: website, speed score, when it was checked, findings
    your sheets     which list the firm is in, and the Website it has there
    the speed log   outreach/teardown-log.csv for that website

and says in plain words what's missing and how to fix it. Read-only - it changes nothing.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import workspace  # noqa: E402 - after the path setup

SLUG = re.compile(r"/for/([a-z0-9]+(?:-[a-z0-9]+)*)")


def slug_from(link: str) -> str | None:
    link = (link or "").strip()
    m = SLUG.search(link)
    if m:
        return m.group(1)
    return link if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", link) else None


def dashboard_row(api: str, secret: str, slug: str, get=None) -> dict | None:
    def _get(url: str) -> dict:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {secret}"})
        with urllib.request.urlopen(req, timeout=20) as res:
            return json.loads(res.read())

    get = get or _get
    try:
        return get(f"{api}/api/prospects/{slug}").get("prospect")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def sheet_matches(outreach: Path, slug: str, secret: str) -> list[dict]:
    """Every sheet row whose preview page is this one."""
    import openpyxl

    from push_prospects import domain_of, make_slug

    out = []
    for path in sorted(outreach.glob("*.xlsx")):
        if path.name.startswith("~$") or path.name.endswith(".tmp.xlsx") or path.name == "outreach-results.xlsx":
            continue
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        except Exception:  # noqa: BLE001 - an odd file never stops the check
            continue
        try:
            for ws in wb.worksheets:
                rows = ws.iter_rows(values_only=True)
                header = [str(h).strip() if h else "" for h in next(rows, ())]
                if "Business" not in header or "Website" not in header:
                    continue
                b, w = header.index("Business"), header.index("Website")
                for r in rows:
                    business = str(r[b] or "").strip() if b < len(r) else ""
                    website = str(r[w] or "").strip() if w < len(r) else ""
                    domain = domain_of(website)
                    if business and domain and make_slug(business, domain, secret) == slug:
                        out.append({"sheet": path.name, "tab": ws.title, "business": business, "website": website, "domain": domain})
        finally:
            wb.close()
    return out


def live_page(slug: str, fetch=None) -> dict | None:
    """What the public page itself shows right now: its score card and findings, or None if it won't load."""
    def _fetch(url: str) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": "ScalarPanel/1.0 (preview check)"})
        with urllib.request.urlopen(req, timeout=30) as res:
            return res.read(3_000_000).decode("utf-8", errors="replace")

    fetch = fetch or _fetch
    try:
        html = fetch(f"https://www.scalardigital.co.uk/for/{slug}")
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return {"score": "/ 100 on mobile" in html, "findings": 'id="findings"' in html}


TROUBLE = re.compile(r"Traceback|Error|error:|WARNING|failed|Import failed|Stopped|exit code|couldn't|still not speed checked|"
                     r"Nothing left|Skipping|left out|List done|Speed checking|Pushed|Logged", re.I)


def last_run(outreach: Path, domain: str | None, business: str | None, most: int = 40) -> list[str]:
    """From the panel's latest run (outreach/last-run-log.txt): its title, the lines that say how it went,
    and every line naming this firm - so one paste shows where it dropped out."""
    path = outreach / "last-run-log.txt"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ["Last run: no saved log yet (v81+ saves one - run the list again, then check)."]
    names = [n.lower() for n in (domain, business) if n]
    keep = [ln for ln in lines[1:] if ln.strip() and (TROUBLE.search(ln) or any(n in ln.lower() for n in names))]
    tail = keep[-most:]
    return [f"Last run: {lines[0] if lines else '?'}", *(f"  | {ln[:200]}" for ln in tail)] + \
        ([f"  | ... {len(keep) - most} earlier lines not shown"] if len(keep) > most else [])


def log_row(outreach: Path, domain: str) -> dict | None:
    path = outreach / "teardown-log.csv"
    if not path.exists():
        return None
    with path.open(encoding="utf-8") as f:
        return next((r for r in csv.DictReader(f) if r.get("website") == domain), None)


def diagnose(slug: str, row: dict | None, matches: list[dict], log: dict | None, year: int,
             live: dict | None = None) -> list[str]:
    from findings import all_issues

    out = [f"Preview: {slug}", ""]
    if row is None:
        out.append("Dashboard: no page with this link - it was never pushed, or was removed (opt-out / data request).")
    else:
        issues = all_issues(row.get("teardown"), year) if row.get("teardown") else []
        out += ["Dashboard (what the page shows):",
                f"  Business: {row.get('business_name')}",
                f"  Website:  {row.get('website') or 'NONE'}",
                f"  Score:    {row.get('mobile_score') if row.get('mobile_score') is not None else 'NONE'}",
                f"  Checked:  {(row.get('teardown_at') or 'never')[:16]}",
                f"  Findings: {len(issues)}"]
    out.append("")
    if matches:
        for m in matches:
            out.append(f"Your sheet: {m['sheet']} ({m['tab']}) - Website cell: {m['website']!r} -> {m['domain']}")
    else:
        out.append("Your sheets: no row makes this link (the firm's name or website was changed since, or the list was deleted).")
    domain = matches[0]["domain"] if matches else (row or {}).get("website")
    if domain:
        if log:
            out.append(f"Speed log: {log.get('result')} on {(log.get('checked_at') or '')[:10]}, score "
                       f"{log.get('mobile_score') or 'none'}")
        else:
            out.append(f"Speed log: {domain} has never been speed checked.")
    if live is not None:
        out.append(f"Live page: score {'shown' if live['score'] else 'NOT shown'}, findings {'shown' if live['findings'] else 'NOT shown'}")
    out += ["", "What's wrong:"]
    problems = []
    if live is not None and row is not None and row.get("mobile_score") is not None and not live["score"]:
        problems.append("Your dashboard has the score but the live page doesn't show it - the website is reading a "
                        "different dashboard. In Vercel, the WEBSITE project's DASHBOARD_API_URL must be "
                        "https://admin.scalardigital.co.uk and PROSPECTS_API_SECRET the same as in panel Settings; "
                        "then redeploy the website.")
    if row is not None:
        if not row.get("website") and matches:
            problems.append("The dashboard has no website for this page although your sheet does. Press Run the whole list "
                            "on that sheet to send it again - if it's still missing after that, tell Claude (it's a bug).")
        if row.get("mobile_score") is None:
            if log and log.get("result") == "ok" and log.get("mobile_score"):
                problems.append("The speed log has a score but the dashboard doesn't: Run the whole list on the sheet sends it.")
            elif log and log.get("result") == "failed":
                problems.append("The last speed check failed - press Retry failed speed checks (the log line says why).")
            elif not log:
                where = f" on {matches[0]['sheet']}" if matches else ""
                problems.append(f"Never speed checked - pick the list{where} and press Run the whole list; it checks "
                                "every site in batches until done. (From v79, no email goes out before its check.)")
            else:
                problems.append("No score anywhere yet - Run the whole list re-checks it (v76+).")
        if not row.get("teardown_at"):
            problems.append("No findings have reached the page - Run the whole list re-checks it (v75+).")
    if not matches and row is not None:
        problems.append("No sheet row produces this link any more, so no run will update this page. Use the link the "
                        "current list makes (preview-links-<list>.csv).")
    out += [f"  - {p}" for p in problems] or ["  Nothing - the page has its website, score and findings."]
    return out


def main(argv: list[str] | None = None) -> int:
    from datetime import date

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--link", required=True)
    ap.add_argument("--outreach", type=Path, default=workspace.outreach_dir())
    args = ap.parse_args(argv)
    slug = slug_from(args.link)
    if not slug:
        raise SystemExit("That doesn't look like a preview link - paste one like https://www.scalardigital.co.uk/for/name-abc123")
    secret = os.environ.get("PROSPECTS_API_SECRET", "")
    if not secret:
        raise SystemExit("Add PROSPECTS_API_SECRET in Settings first.")
    api = os.environ.get("DASHBOARD_API_URL", "https://admin.scalardigital.co.uk").rstrip("/")
    try:
        row = dashboard_row(api, secret, slug)
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise SystemExit(f"Couldn't reach the dashboard ({getattr(e, 'reason', e)}).") from e
    matches = sheet_matches(args.outreach, slug, secret)
    domain = matches[0]["domain"] if matches else (row or {}).get("website")
    for line in diagnose(slug, row, matches, log_row(args.outreach, domain) if domain else None, date.today().year,
                         live_page(slug)):
        print(line)
    print("")
    for line in last_run(args.outreach, domain, matches[0]["business"] if matches else (row or {}).get("business_name")):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
