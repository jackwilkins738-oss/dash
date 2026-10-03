"""The research card: who you're about to ring, in ten seconds, before you dial.

The panel's Calls tab has a Research button on every firm. It puts together, from free sources only:

    Companies House   how old the company is, whether it's active, its directors (the name to ask for)
    their homepage    years trading, what they say they do, accreditations, insurance or guarantees
    your speed check  their mobile score and the worst thing it found
    Google reviews    a one-tap search link - their rating isn't fetched (that needs a paid Google key)

Kept in outreach/research.json for 30 days, so a second look is instant. Sole traders and
partnerships aren't on Companies House; the card says so rather than guessing.
"""

from __future__ import annotations

import csv
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote_plus

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

FILE = "research.json"
FRESH_DAYS = 30
INSURED = re.compile(r"\b(fully insured|public liability|insured)\b", re.I)
GUARANTEE = re.compile(r"\b(\d{1,2}[- ]year (?:guarantee|warranty)|guarantee[ds]?|warrant(?:y|ied))\b", re.I)
FAMILY = re.compile(r"\b(family[- ]run|family business|family[- ]owned)\b", re.I)


def _age(created: str, today: date) -> str:
    try:
        d = date.fromisoformat(created)
    except ValueError:
        return ""
    years = today.year - d.year - ((today.month, today.day) < (d.month, d.day))
    return f"{years} year{'s' if years != 1 else ''}" if years else "under a year"


def _cached_lookup(outreach: Path, website: str) -> dict:
    path = outreach / "company-lookups.csv"
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return next((r for r in csv.DictReader(f) if r.get("website") == website), {})


def company(outreach: Path, business: str, website: str, area: str, html: str | None, key: str, get=None,
            today: date | None = None) -> list[str]:
    import company_lookup

    today = today or date.today()
    get = get or company_lookup._get
    # Only a confident match - an "unsure" one could be a different firm, and the wrong director's
    # name is worse on a call than none.
    found = _cached_lookup(outreach, website)
    number = (found.get("number") or "").strip() if found.get("result") in ("company", "closed") else ""
    if not number and key:
        try:
            hit = company_lookup.lookup(business, area, html, key)
            number = (hit.get("number") or "").strip() if hit.get("result") in ("company", "closed") else ""
        except Exception:  # noqa: BLE001 - a lookup hiccup just means no company line
            number = ""
    if not number:
        return ["Companies House: not found - probably a sole trader or partnership, so no directors listed."]
    if not key:
        return [f"Companies House: company {number} (add COMPANIES_HOUSE_API_KEY in Settings for age and directors)."]
    try:
        profile = get(f"/company/{number}", key) or {}
        officers = get(f"/company/{number}/officers?items_per_page=20", key) or {}
    except Exception as e:  # noqa: BLE001
        return [f"Companies House: company {number} - couldn't read it just now ({type(e).__name__})."]
    lines = []
    name = profile.get("company_name") or found.get("registered_name") or number
    status = (profile.get("company_status") or "").replace("-", " ")
    age = _age(profile.get("date_of_creation") or "", today)
    lines.append(f"Company: {name} ({number})" + (f", {status}" if status else "") + (f", {age} old" if age else ""))
    if status and status != "active":
        lines.append(f"Heads up: Companies House says '{status}' - check they're still trading before you pitch.")
    directors = []
    for o in officers.get("items") or []:
        if o.get("officer_role") == "director" and not o.get("resigned_on"):
            raw = o.get("name") or ""
            last, _, first = raw.partition(",")
            directors.append(f"{first.strip().title()} {last.strip().title()}".strip())
    if directors:
        lines.append("Directors: " + ", ".join(directors[:4]) + (f" (+{len(directors) - 4} more)" if len(directors) > 4 else ""))
    return lines


def homepage(website: str, fetch=None) -> tuple[list[str], str | None]:
    from site_draft import _text, read_site
    from site_teardown import fetch_html

    fetch = fetch or fetch_html
    url = website if website.startswith("http") else f"https://{website}"
    html, final = fetch(url)
    if not html:
        return ["Their site: couldn't load it just now."], None
    site = read_site(html, final or url)
    body = re.sub(r"<(script|style|noscript|svg)\b.*?</\1>", " ", html, flags=re.I | re.S)
    text = _text(body)
    lines = []
    facts = [site.get("years") or ""]
    if FAMILY.search(text):
        facts.append("family-run")
    if INSURED.search(text):
        facts.append("says they're insured")
    g = GUARANTEE.search(text)
    if g:
        facts.append(f"mentions a {g.group(1).lower()}" if "year" in g.group(1).lower() else "mentions a guarantee")
    facts = [f for f in facts if f]
    if facts:
        lines.append("Their site says: " + ", ".join(facts) + ".")
    if site.get("services"):
        lines.append("They do: " + ", ".join(site["services"][:6]) + ".")
    if site.get("accreditations"):
        lines.append("Accredited: " + ", ".join(site["accreditations"]) + ".")
    return lines or ["Their site: nothing specific about them on the homepage."], html


def speed(outreach: Path, website: str) -> list[str]:
    path = outreach / "teardown-log.csv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        row = next((r for r in csv.DictReader(f) if r.get("website") == website), None)
    if not row or row.get("result") != "ok":
        return []
    bits = []
    if row.get("mobile_score"):
        bits.append(f"{int(float(row['mobile_score']))}/100 on mobile")
    if row.get("lcp_s"):
        bits.append(f"{row['lcp_s']}s to load")
    line = "Speed check: " + ", ".join(bits) if bits else ""
    if row.get("top_issue"):
        line = (line + " - worst: " if line else "Worst thing we found: ") + row["top_issue"]
    return [line] if line else []


def research(outreach: Path, business: str, website: str, area: str, settings: dict, fresh: bool = False,
             fetch=None, get=None, today: date | None = None) -> dict:
    cache_path = outreach / FILE
    try:
        cache = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        cache = {}
    hit = cache.get(website)
    if hit and not fresh:
        try:
            if (datetime.now() - datetime.fromisoformat(hit["at"])).days < FRESH_DAYS:
                return hit
        except (KeyError, ValueError):
            pass
    site_lines, html = homepage(website, fetch)
    lines = company(outreach, business, website, area, html, (settings.get("COMPANIES_HOUSE_API_KEY") or "").strip(), get, today)
    lines += site_lines + speed(outreach, website)
    out = {"lines": lines, "google": "https://www.google.com/search?q=" + quote_plus(f"{business} {area} reviews".strip()),
           "at": datetime.now().isoformat(timespec="minutes")}
    cache[website] = out
    try:
        cache_path.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    except OSError:
        pass
    return out
