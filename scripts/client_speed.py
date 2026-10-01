"""Monthly speed check of every live client site - so a slow-down is caught by you, not by them.

    python scripts/client_speed.py

Every client folder with a publish.json (it's been published) and a real domain in site.json is
measured on Google's mobile test three times; the middle result is kept, so one lucky or unlucky
run can't decide it. Each result is added to outreach/client-speed.csv, and the list shows this
month next to last time:

    kerr-roofing      kerrroofing.co.uk          96   (was 97)
    LOOK AT  smith-drives  smithdriveways.co.uk  84   (was 95)  - under 90

A site under 90, or 5+ points down on last time, is marked LOOK AT - usually a heavy new photo
someone uploaded to the gallery. The sites sell "90+ on Google's mobile speed test", so this is
the promise being kept. With Telegram set up, the LOOK AT lines are texted to you too.

Needs PAGESPEED_API_KEY (the same as the speed checks).
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

LOG = "client-speed.csv"
FIELDS = ["date", "folder", "domain", "mobile_score", "lcp_s"]
PROMISE = 90
DROP = 5
RUNS = 3


def live_sites(outreach: Path) -> list[tuple[str, str]]:
    """(folder, domain) for every client that's been published with a real domain."""
    out = []
    for folder in sorted((outreach / "sites").glob("*/")):
        cfg_path = folder / "site.json"
        if not (folder / "publish.json").exists() or not cfg_path.exists():
            continue
        try:
            domain = str(json.loads(cfg_path.read_text(encoding="utf-8")).get("domain") or "").strip().lower()
        except ValueError:
            continue
        if re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", domain):
            out.append((folder.name, domain))
    return out


def measure(domain: str, key: str, run=None) -> tuple[int, float | None] | None:
    """Median mobile score (and its LCP) of three runs, or None if Google couldn't test it."""
    if run is None:
        from site_teardown import run_pagespeed as run
    results = [r for r in (run(f"https://{domain}/", key) for _ in range(RUNS)) if isinstance(r.get("_mobile_score"), int)]
    if not results:
        return None
    results.sort(key=lambda r: r["_mobile_score"])
    mid = results[len(results) // 2] if len(results) % 2 else results[len(results) // 2 - 1]
    return mid["_mobile_score"], mid.get("_lcp_s")


def last_scores(outreach: Path) -> dict[str, int]:
    path = outreach / LOG
    if not path.exists():
        return {}
    last: dict[str, int] = {}
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                last[row["folder"]] = int(row["mobile_score"])
            except (KeyError, ValueError):
                continue
    return last


def append(outreach: Path, rows: list[dict]) -> None:
    path = outreach / LOG
    new = not path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        if new:
            w.writeheader()
        w.writerows(rows)


def verdict(score: int, before: int | None) -> str:
    """'' if fine, else why it needs a look."""
    if score < PROMISE:
        return f"under {PROMISE}"
    if before is not None and before - score >= DROP:
        return f"down {before - score} since last time"
    return ""


def text_me(lines: list[str]) -> None:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    if not (token and chat and lines):
        return
    body = json.dumps({"chat_id": chat, "text": "Client site speed - worth a look:\n" + "\n".join(lines)}).encode()
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=body, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20).close()
    except OSError:
        print("(Couldn't send the Telegram message - the list above is the same.)")


def run(outreach: Path, key: str, today: date | None = None, run_psi=None) -> int:
    sites = live_sites(outreach)
    if not sites:
        print("No live client sites yet - a site counts once Publish site has put it live (publish.json) with its domain in site.json.")
        return 0
    before = last_scores(outreach)
    rows, flagged, failed = [], [], 0
    day = (today or date.today()).isoformat()
    for folder, domain in sites:
        result = measure(domain, key, run_psi)
        if result is None:
            failed += 1
            print(f"  ??       {folder:<24} {domain:<30} Google couldn't test it - is the site up?")
            continue
        score, lcp = result
        why = verdict(score, before.get(folder))
        was = f"(was {before[folder]})" if folder in before else "(first check)"
        print(f"  {'LOOK AT' if why else 'ok':<8} {folder:<24} {domain:<30} {score:>3}  {was}" + (f"  - {why}" if why else ""))
        if why:
            flagged.append(f"{domain}: {score} - {why}")
        rows.append({"date": day, "folder": folder, "domain": domain, "mobile_score": score, "lcp_s": "" if lcp is None else lcp})
    append(outreach, rows)
    text_me(flagged)
    print(f"Checked {len(rows)} of {len(sites)} client sites: {len(flagged)} to look at. Saved to {LOG}.")
    if flagged:
        print("Usually a heavy photo added to the gallery - the launch report's notes (and Google's own report) say which.")
    return 1 if failed == len(sites) else 0


def main() -> None:
    import reply_scanner

    key = os.environ.get("PAGESPEED_API_KEY", "")
    if not key:
        sys.exit("Add PAGESPEED_API_KEY in Settings first.")
    sys.exit(run(reply_scanner.outreach_dir(), key))


if __name__ == "__main__":
    main()
