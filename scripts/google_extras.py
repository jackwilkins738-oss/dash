"""Two things for the preview page that only Google knows, added during the speed check.

    Their Google reviews   "4.8 from 63 Google reviews" - a firm that's earned that and doesn't show it
                           on its homepage is leaving its best selling point out. Google Maps lists
                           already carry the rating; other lists ask Places once per firm, and only a
                           result whose website is theirs is used, so it can't be another firm's.
    Who they're up against The top firms on Google Maps for "roofer in Guildford" and their own Google
                           mobile scores, next to theirs. One search and three speed checks per trade
                           and town, shared by every firm in it and kept 30 days.

Both go into the teardown the dashboard stores (google, rivals). Nothing here is shown unless it's real:
no rating -> no line; fewer than two rivals measured -> no comparison.

Needs GOOGLE_PLACES_API_KEY (or PAGESPEED_API_KEY from a project with Places API (New) enabled).
"""

from __future__ import annotations

import json
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

RATINGS_FILE = "google-ratings.json"
RIVALS_FILE = "rivals.json"
FRESH_DAYS = 30
RIVALS_SHOWN = 3
PSI = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?"
NAME_OK = re.compile(r"[^A-Za-z0-9 &'()./,+-]")
TRADE_WORDS = [  # what people type, by the words in a firm's trade
    (re.compile(r"loft", re.I), "loft conversion company"),
    (re.compile(r"drive|paving|patio", re.I), "driveway contractor"),
    (re.compile(r"roof", re.I), "roofer"),
    (re.compile(r"landscap|garden", re.I), "landscaper"),
    (re.compile(r"build|extension|construct", re.I), "builder"),
]
_lock = threading.Lock()


def search_words(trade: str) -> str:
    for pattern, words in TRADE_WORDS:
        if pattern.search(trade or ""):
            return words
    return (trade or "").strip().lower()


def clean_name(name: str) -> str:
    return re.sub(r"\s+", " ", NAME_OK.sub("", name or "")).strip()[:60]


def _fresh(at: str) -> bool:
    try:
        return (date.today() - date.fromisoformat(at[:10])).days < FRESH_DAYS
    except (TypeError, ValueError):
        return False


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _save(path: Path, data: dict) -> None:
    with _lock:
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=1), encoding="utf-8")
        tmp.replace(path)


def rating_from_sheet(rating, reviews) -> dict | None:
    """A Google Maps list's own columns, when it has them."""
    try:
        r, n = float(rating), int(float(reviews))
    except (TypeError, ValueError):
        return None
    return {"rating": round(r, 1), "reviews": n} if 1 <= r <= 5 and n > 0 else None


def rating(business: str, area: str, domain: str, key: str, outreach: Path, post=None) -> dict | None:
    """Their Google rating, only from a Places result whose website is theirs. Cached 30 days."""
    from places_finder import search
    from push_prospects import domain_of

    path = outreach / RATINGS_FILE
    cache = _load(path)
    hit = cache.get(domain)
    if hit and _fresh(hit.get("at", "")):
        return hit.get("google")
    found = None
    for place in search(f"{business} {area}".strip(), key, post, pages=1)[:10]:
        if domain_of(place.get("websiteUri") or "") == domain:
            found = rating_from_sheet(place.get("rating"), place.get("userRatingCount"))
            break
    cache[domain] = {"at": date.today().isoformat(), "google": found}
    _save(path, cache)
    return found


def mobile_score(domain: str, key: str, timeout: int = 120) -> int | None:
    """Just Google's mobile performance score - the same number the prospect's own score is."""
    q = urllib.parse.urlencode([("url", f"https://{domain}/"), ("strategy", "mobile"), ("category", "performance"), ("key", key)])
    try:
        with urllib.request.urlopen(PSI + q, timeout=timeout) as res:
            data = json.loads(res.read())
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None
    score = (((data.get("lighthouseResult") or {}).get("categories") or {}).get("performance") or {}).get("score")
    return round(score * 100) if isinstance(score, (int, float)) else None


def rivals_for_query(query: str, places_key: str, psi_key: str, outreach: Path, post=None, score=None) -> dict | None:
    """The search's firms in Google's order (domains), and speed scores for the first few with a site."""
    from places_finder import keep, own_site, search
    from push_prospects import domain_of

    score = score or mobile_score
    path = outreach / RIVALS_FILE
    cache = _load(path)
    hit = cache.get(query)
    if hit and _fresh(hit.get("at", "")):
        return hit
    order, firms = [], []
    for place in search(query, places_key, post, pages=1)[:20]:
        if not keep(place, [], []):
            continue
        d = domain_of(own_site(place.get("websiteUri") or "")) if place.get("websiteUri") else None
        order.append(d or "")
        name = clean_name((place.get("displayName") or {}).get("text") or "")
        if d and name and len(firms) < RIVALS_SHOWN + 2:  # two spare, in case one of them is the prospect
            firms.append({"name": name, "domain": d})
    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=8) as pool:
        for f, s in zip(firms, pool.map(lambda f: score(f["domain"], psi_key), firms)):
            f["score"] = s
    out = {"at": date.today().isoformat(), "query": query, "order": order, "firms": firms}
    cache[query] = out
    _save(path, cache)
    return out


def rivals(trade: str, area: str, domain: str, places_key: str, psi_key: str, outreach: Path, post=None,
           score=None) -> dict | None:
    """What the preview shows: the search, where they came, and up to three others' scores."""
    words, town = search_words(trade), (area or "").strip()
    if not words or not town:
        return None
    query = f"{words} in {town.title()}"
    found = rivals_for_query(query, places_key, psi_key, outreach, post, score)
    if not found:
        return None
    items = [{"name": f["name"], "score": f["score"]} for f in found["firms"]
             if f["domain"] != domain and isinstance(f.get("score"), int)][:RIVALS_SHOWN]
    if len(items) < 2:
        return None
    position = found["order"].index(domain) + 1 if domain in found["order"] else None
    return {"query": query[:80], "items": items, **({"position": position} if position else {}),
            "checkedAt": found["at"]}


def add_to(prospects: list[dict], outreach: Path, places_key: str, psi_key: str, post=None, score=None,
           log=print) -> None:
    """Fills teardown["google"] and teardown["rivals"] for every prospect just speed checked."""
    from places_finder import PlacesError

    todo = [p for p in prospects if p.get("teardown")]
    if not todo:
        return
    if not places_key:
        log("Google reviews and competitor scores skipped - add GOOGLE_PLACES_API_KEY in Settings to get them.")
        return
    reviews = compared = 0
    try:
        for p in todo:
            google = p.get("_google") or rating(p["business_name"], p.get("area") or "", p["website"], places_key, outreach, post)
            if google:
                p["teardown"]["google"] = google
                reviews += 1
            r = rivals(p.get("trade") or "", p.get("area") or "", p["website"], places_key, psi_key, outreach, post, score)
            if r:
                p["teardown"]["rivals"] = r
                compared += 1
    except PlacesError as e:
        log(f"Google reviews and competitor scores stopped: {e} The speed checks themselves are fine.")
        return
    log(f"Google: {reviews} rating(s) and {compared} competitor comparison(s) added to the previews.")
