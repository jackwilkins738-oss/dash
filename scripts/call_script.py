"""A call card for one firm: who to ask for, an opener, the hook from their own numbers, one question, the ask.

Built only from what's already on this PC - their speed check (teardown-log.csv), their Google rating
(google-ratings.json) and the firms above them on Google (rivals.json). A line with no real number
behind it is left out, never guessed. Shown on Telegram's 📞 Calls and the panel's Calls tab.
"""

from __future__ import annotations

import csv
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def load(outreach: Path) -> dict:
    """Everything the cards draw on, read once (the Calls tab builds a card for every firm)."""
    log = {}
    path = outreach / "teardown-log.csv"
    if path.exists():
        with path.open(encoding="utf-8") as f:
            log = {r["website"]: r for r in csv.DictReader(f) if r.get("website")}
    return {"log": log, "ratings": _json(outreach / "google-ratings.json"), "rivals": _json(outreach / "rivals.json")}


def facts(data: dict, website: str) -> dict:
    out: dict = {}
    row = data["log"].get(website) if website else None
    if row and row.get("result", "ok") == "ok":
        try:
            out["score"] = int(float(row.get("mobile_score") or ""))
        except ValueError:
            pass
        if row.get("top_issue") and row["top_issue"] != "?":
            out["issue"] = row["top_issue"].strip().rstrip(".")
    google = (data["ratings"].get(website) or {}).get("google") if website else None
    if isinstance(google, dict) and google.get("rating"):
        out["rating"], out["reviews"] = google["rating"], google.get("reviews", 0)
    for hit in data["rivals"].values():
        order = hit.get("order") or []
        if website and website in order:
            out["query"], out["position"] = hit.get("query", ""), order.index(website) + 1
            mine = out.get("score")
            better = [f for f in hit.get("firms") or [] if f.get("domain") != website and isinstance(f.get("score"), int)
                      and (mine is None or f["score"] > mine)]
            if better:
                out["rival"] = better[0]
            break
    return out


def uk_time(iso: str) -> datetime | None:
    """A UTC timestamp in UK clock time (BST from the last Sunday of March to the last Sunday of October,
    01:00 UTC) - worked out here so it needs no time-zone database on Windows."""
    try:
        t = datetime.fromisoformat((iso or "").replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None

    def last_sunday(month: int) -> datetime:
        d = datetime(t.year, month, 31 if month in (3, 10) else 30, 1, tzinfo=timezone.utc)
        return d - timedelta(days=(d.weekday() + 1) % 7)

    return t + timedelta(hours=1) if last_sunday(3) <= t < last_sunday(10) else t


def best_time(item: dict) -> str:
    """When they opened their preview, as a hint for when to ring: the moments they had their phone out."""
    times = [x for x in (uk_time(item.get("first_viewed", "")), uk_time(item.get("last_viewed", ""))) if x]
    if not times:
        return ""
    hours = sorted({x.hour for x in times})
    label = lambda h: f"{h % 12 or 12}{'am' if h < 12 else 'pm'}"  # noqa: E731
    when = " and ".join(label(h) for h in hours)
    if all(h >= 17 for h in hours):
        tip = "evenings suit them - try 5-7pm"
    elif all(h < 9 for h in hours):
        tip = "early starter - try 7:30-8:30am"
    elif all(12 <= h < 14 for h in hours):
        tip = "lunchtimes - try 12-1:30pm"
    else:
        tip = "try the same time of day"
    return f"When: opened it around {when} - {tip}."


def script(item: dict, outreach: Path, your_name: str = "", data: dict | None = None) -> list[str]:
    from saved_replies import first_name

    f = facts(data or load(outreach), item.get("website") or "")
    name = first_name(item.get("contact", ""))
    me = (your_name or "").split()[0] if (your_name or "").strip() else "<your name>"
    lines = [f"Ask for {item['contact']}." if item.get("contact") else "Ask for the owner."]
    when = best_time(item)
    if when:
        lines.append(when)
    lines.append(f"Open: \"Hi{' ' + name if name != 'there' else ''}, it's {me} from Scalar Digital - I put together a page "
                 f"for {item['business']} and sent it over. Did you get a chance to look?\"")
    if "score" in f:
        hook = f"Hook: their site scores {f['score']}/100 on Google's phone test"
        lines.append(hook + (f" - {f['issue'][0].lower() + f['issue'][1:]}." if f.get("issue") else "."))
    if f.get("rival") and f.get("query"):
        r = f["rival"]
        where = f" (they're #{f['position']})" if f.get("position") else ""
        lines.append(f"Rival: {r['name']} scores {r['score']} for \"{f['query']}\"{where}.")
    if f.get("rating", 0) >= 4.5 and f.get("reviews", 0) >= 10:
        lines.append(f"Praise: {f['rating']}★ from {f['reviews']} Google reviews - \"the site isn't doing that justice\".")
    lines.append("Ask: \"Where does most of your work come from at the moment?\"")
    lines.append("Close: \"Want me to send a fixed price today? No obligation.\"")
    return lines
