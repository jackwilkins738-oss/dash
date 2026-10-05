"""A basic, automated teardown of a prospect's current homepage.

Used by push_prospects.py --teardown. Produces check results only - True =
fine, False = a problem, left out = couldn't be checked - which the website
turns into wording (lib/teardown.ts). Two sources, both things the business
owner can verify for themselves:

  1. Google's PageSpeed Insights (mobile): SEO and accessibility scores,
     readable text size, tap-target size, page title and meta description,
     how much image weight could be saved, total page weight.
     (Not its HTTPS audit: that also fails on a secure site that loads one
     file over http://, which is a different problem - see secureAssets.)
  2. The public HTML of their homepage: a tap-to-call link, a WhatsApp link,
     an enquiry form, local business structured data, the copyright year in
     the footer, and the platform it's built on.

The rule throughout: when in doubt, leave it out. A page that's mostly built
in the browser (little text in the raw HTML) doesn't get the link/form checks
at all, because "we couldn't see one" isn't the same as "there isn't one".
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = "ScalarDigitalSiteCheck/1.0 (+https://www.scalardigital.co.uk)"
MAX_HTML_BYTES = 2_000_000

# Structured-data types that describe a local trade business.
LOCAL_TYPES = re.compile(
    r"LocalBusiness|Contractor|HomeAndConstructionBusiness|Roofing|Plumber|Electrician|"
    r"HousePainter|Locksmith|MovingCompany|HVACBusiness|ProfessionalService|LandscapingService",
    re.I,
)

PLATFORM_MARKERS = [
    ("wix", re.compile(r"static\.wixstatic\.com|<meta[^>]+generator[^>]+wix", re.I)),
    ("squarespace", re.compile(r"static1\.squarespace\.com|<meta[^>]+generator[^>]+squarespace", re.I)),
    ("godaddy", re.compile(r"img1\.wsimg\.com|GoDaddy Website Builder", re.I)),
    ("webflow", re.compile(r"<meta[^>]+generator[^>]+webflow|assets\.website-files\.com", re.I)),
    ("weebly", re.compile(r"editmysite\.com|<meta[^>]+generator[^>]+weebly", re.I)),
    ("duda", re.compile(r"multiscreensite\.com|dudamobile", re.I)),
    ("shopify", re.compile(r"cdn\.shopify\.com", re.I)),
    ("wordpress", re.compile(r"/wp-content/|/wp-includes/|<meta[^>]+generator[^>]+wordpress", re.I)),
]

IMAGE_AUDITS = [
    "uses-optimized-images",
    "modern-image-formats",
    "uses-responsive-images",
    "offscreen-images",
    "image-delivery-insight",
]


# ---------------------------------------------------------------- PageSpeed


def _audit_pass(audits: dict, *ids: str) -> bool | None:
    """True/False for a binary Lighthouse audit, or None if it didn't apply or wasn't run."""
    for audit_id in ids:
        a = audits.get(audit_id)
        if not a:
            continue
        if a.get("scoreDisplayMode") in ("notApplicable", "manual", "error") or a.get("score") is None:
            return None
        return a["score"] >= 0.9
    return None


def psi_error(code: int, body: str) -> str:
    """Google's own reason, in a line (its messages never contain the key)."""
    try:
        message = (json.loads(body).get("error") or {}).get("message") or ""
    except ValueError:
        message = ""
    message = re.sub(r"\s+", " ", message).strip()
    low = message.lower()
    if "api key not valid" in low or "api_key_invalid" in low:
        return "Google says the PAGESPEED_API_KEY isn't valid - check it in Settings"
    if code == 429 or "quota" in low:
        return "Google's speed test quota is used up for today - it resets at midnight Pacific time"
    if "has not been used" in low or "is disabled" in low or "service_disabled" in low:
        return "the PageSpeed Insights API is switched off for this key's Google Cloud project - enable it there"
    if "referer" in low or "referrer" in low or "blocked" in low:
        return "the key is restricted (websites/IPs) so the panel can't use it - allow PageSpeed Insights API without that restriction"
    return f"Google's speed test said: {message[:160] or f'HTTP {code}'}"


def run_pagespeed(url: str, api_key: str, timeout: int = 180) -> dict:
    """Checks from Google's mobile test. Empty dict if the test couldn't run."""
    params = [("url", url), ("strategy", "mobile"), ("key", api_key)]
    params += [("category", c) for c in ("performance", "seo", "accessibility", "best-practices")]
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(endpoint, timeout=timeout) as res:
            data = json.loads(res.read())
    except urllib.error.HTTPError as e:
        # Say why - a bad key, a used-up quota or a site Google couldn't load all look the same otherwise.
        return {"_psi_error": psi_error(e.code, e.read(2000).decode("utf-8", errors="replace"))}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
        return {"_psi_error": f"couldn't reach Google's speed test ({type(e).__name__})"}

    lh = data.get("lighthouseResult") or {}
    cats = lh.get("categories") or {}
    audits = lh.get("audits") or {}
    out: dict = {"checks": {}}

    # The headline mobile score and LCP, so a new prospect with nothing in
    # the sheet gets both from this one run. Kept under "_" keys: they are
    # prospect fields, not teardown checks, and push_prospects.py moves them.
    perf = (cats.get("performance") or {}).get("score")
    if isinstance(perf, (int, float)):
        out["_mobile_score"] = round(perf * 100)
    lcp = (audits.get("largest-contentful-paint") or {}).get("numericValue")
    if isinstance(lcp, (int, float)):
        out["_lcp_s"] = round(lcp / 1000, 1)

    for key, cat in (("seoScore", "seo"), ("accessibilityScore", "accessibility")):
        score = (cats.get(cat) or {}).get("score")
        if isinstance(score, (int, float)):
            out[key] = round(score * 100)

    for check, ids in (
        ("readableText", ("font-size",)),
        ("tapTargets", ("tap-targets", "target-size")),
        ("pageTitle", ("document-title",)),
        ("metaDescription", ("meta-description",)),
    ):
        result = _audit_pass(audits, *ids)
        if result is not None:
            out["checks"][check] = result

    # The image audits overlap (one oversized JPEG can appear in several), so
    # take the single largest saving rather than adding them up.
    savings = [
        (audits.get(a) or {}).get("details", {}).get("overallSavingsBytes")
        for a in IMAGE_AUDITS
    ]
    savings = [s for s in savings if isinstance(s, (int, float))]
    if savings:
        out["imageSavingsKb"] = round(max(savings) / 1000)

    weight = (audits.get("total-byte-weight") or {}).get("numericValue")
    if isinstance(weight, (int, float)):
        out["pageWeightKb"] = round(weight / 1000)

    # The real thing, not an animation: frames of their site loading on Google's test phone, and
    # how it looks once it has - for the preview page. Only for slow sites (that's the story they
    # tell), and only when Pillow is here to shrink them to a few KB each.
    if isinstance(out.get("_mobile_score"), int) and out["_mobile_score"] < 90:
        out.update(filmstrip(audits))
    return out


FRAMES = 3
FRAME_WIDTH, SHOT_WIDTH = 120, 320
SHOT_MAX = 38_000  # the dashboard keeps screenshots up to 40,000 characters


def shrink(data_uri: str, width: int, quality: int) -> str | None:
    """A Lighthouse screenshot made small enough to store per prospect - or None without Pillow."""
    try:
        import base64
        import io

        from PIL import Image
    except ImportError:
        return None
    try:
        raw = base64.b64decode(data_uri.split(",", 1)[1])
        with Image.open(io.BytesIO(raw)) as im:
            im = im.convert("RGB")
            if im.width > width:
                im = im.resize((width, round(im.height * width / im.width)))
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=quality, optimize=True)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:  # noqa: BLE001 - a screenshot Google sent oddly just isn't shown
        return None


def filmstrip(audits: dict) -> dict:
    """{"frames": [{"t": ms, "img": data URI}, ...], "screenshot": data URI} - whatever could be made."""
    out: dict = {}
    items = ((audits.get("screenshot-thumbnails") or {}).get("details") or {}).get("items") or []
    items = [i for i in items if isinstance(i, dict) and str(i.get("data", "")).startswith("data:image/")]
    if len(items) >= FRAMES:
        picks = [items[round(len(items) * k / FRAMES) - 1] for k in range(1, FRAMES + 1)]
        frames = []
        for i in picks:
            img = shrink(i["data"], FRAME_WIDTH, 55)
            if img and isinstance(i.get("timing"), (int, float)):
                frames.append({"t": int(i["timing"]), "img": img})
        if len(frames) == FRAMES:
            out["frames"] = frames
    final = ((audits.get("final-screenshot") or {}).get("details") or {}).get("data")
    if isinstance(final, str) and final.startswith("data:image/"):
        # Sharp enough for a phone frame on the page; a busy, photo-heavy homepage steps down to fit.
        for width, quality in ((SHOT_WIDTH, 60), (SHOT_WIDTH, 45), (240, 50)):
            shot = shrink(final, width, quality)
            if shot and len(shot) <= SHOT_MAX:
                out["screenshot"] = shot
                break
    return out


# --------------------------------------------------------------------- HTML


def fetch_html(url: str, timeout: int = 20) -> tuple[str | None, str | None]:
    """(html, final_url) - or (None, None) if the homepage couldn't be fetched."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            if "html" not in (res.headers.get("Content-Type") or "html"):
                return None, None
            raw = res.read(MAX_HTML_BYTES)
            return raw.decode(res.headers.get_content_charset() or "utf-8", errors="replace"), res.geturl()
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None, None


def visible_text_length(html: str) -> int:
    stripped = re.sub(r"<(script|style|noscript|svg)\b.*?</\1>", " ", html, flags=re.I | re.S)
    stripped = re.sub(r"<[^>]+>", " ", stripped)
    return len(re.sub(r"\s+", " ", stripped).strip())


def _ld_types(html: str) -> list[str]:
    types: list[str] = []

    def walk(node):
        if isinstance(node, dict):
            t = node.get("@type")
            if isinstance(t, str):
                types.append(t)
            elif isinstance(t, list):
                types.extend(x for x in t if isinstance(x, str))
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    for block in re.findall(r"<script[^>]+application/ld\+json[^>]*>(.*?)</script>", html, re.I | re.S):
        try:
            walk(json.loads(block.strip()))
        except json.JSONDecodeError:
            continue
    types += re.findall(r'itemtype\s*=\s*["\']https?://schema\.org/(\w+)', html, re.I)
    return types


def copyright_year(html: str) -> int | None:
    """The latest year written next to a copyright mark, or None if there isn't one in the HTML."""
    years = []
    pattern = r"(?:©|&copy;|&#169;|&#xa9;|copyright)[^<\d]{0,40}((?:19|20)\d{2})(?:\s*(?:-|–|—|&ndash;|&mdash;|to)\s*((?:19|20)\d{2}))?"
    for m in re.finditer(pattern, html, re.I):
        years.extend(int(y) for y in m.groups() if y)
    return max(years) if years else None


TEL_ANYWHERE = re.compile(r"tel:\+?[\d\s().-]{6,}", re.I)
WHATSAPP_ANYWHERE = re.compile(r"wa\.me/|api\.whatsapp\.com|whatsapp://|web\.whatsapp\.com", re.I)


def same_origin_scripts(html: str, base_url: str, limit: int = 6) -> list[str]:
    """Bodies of the page's own script files (same site only, capped), for links added by JavaScript."""
    base = urllib.parse.urlparse(base_url)
    bodies = []
    for src in re.findall(r"<script[^>]+src\s*=\s*[\"']([^\"']+)[\"']", html, re.I):
        url = urllib.parse.urljoin(base_url, src)
        if urllib.parse.urlparse(url).netloc != base.netloc:
            continue
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=15) as res:
                bodies.append(res.read(400_000).decode("utf-8", errors="replace"))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            continue
        if len(bodies) >= limit:
            break
    return bodies


REVIEWS_SHOWN = re.compile(
    r"aggregaterating|trustindex|elfsight|reviews\.io|trustpilot|featurable|reviewsonmywebsite|grwapi|"
    r"google-reviews|googlereviews|widget\.checkatrade|checkatrade\.com/[^\"']*(?:widget|badge)|ratedpeople\.com/[^\"']*widget|"
    r"\u2605{3,}|(?:&#9733;|&#x2605;){3,}|>\s*(?:our\s+|customer\s+|client\s+)?(?:reviews|testimonials)\s*<",
    re.I,
)


def analyse_html(html: str, final_url: str | None, script_bodies: list[str] | None = None) -> dict:
    out: dict = {"checks": {}}
    checks = out["checks"]

    # Link and form checks only when the HTML actually carries the page's
    # content. A shell that builds itself in the browser would otherwise read
    # as "no phone link, no form" when both may well be there.
    if visible_text_length(html) >= 400:
        # A call or WhatsApp button is often added by JavaScript (a sticky
        # bar, a plugin), so "missing" is only concluded after also checking
        # inline scripts and the site's own script files.
        scripts = " ".join(script_bodies or [])
        checks["tapToCall"] = bool(
            re.search(r"href\s*=\s*[\"']\s*tel:", html, re.I) or TEL_ANYWHERE.search(html) or TEL_ANYWHERE.search(scripts)
        )
        checks["whatsapp"] = bool(WHATSAPP_ANYWHERE.search(html) or WHATSAPP_ANYWHERE.search(scripts))
        has_form = bool(re.search(r"<form\b", html, re.I)) and bool(
            re.search(r"<textarea\b|type\s*=\s*[\"']?(email|tel)\b", html, re.I)
        )
        embedded_form = bool(re.search(r"typeform\.com|jotform|formspree|wpforms|contact-form-7|gravityforms|hsforms", html, re.I))
        checks["contactForm"] = has_form or embedded_form
        # Reviews on the homepage: a review widget, rating markup, a row of stars, or a Reviews /
        # Testimonials heading or link. Only "none of these anywhere" counts as not showing them.
        checks["showsReviews"] = bool(REVIEWS_SHOWN.search(html) or REVIEWS_SHOWN.search(scripts))

    checks["localSchema"] = any(LOCAL_TYPES.search(t) for t in _ld_types(html))

    year = copyright_year(html)
    if year is not None:
        out["copyrightYear"] = year

    for name, marker in PLATFORM_MARKERS:
        if marker.search(html):
            out["platform"] = name
            break
    if out.get("platform") == "wordpress":
        plugins = set(p.lower() for p in re.findall(r"/wp-content/plugins/([A-Za-z0-9_-]+)/", html))
        out["wpPluginCount"] = len(plugins)

    # Their own service names and brand colour, for the preview page's concept
    # (only when fairly sure - see site_draft.for_preview).
    from site_draft import for_preview, read_site

    out.update(for_preview(read_site(html, final_url or "")))

    # HTTPS is judged on where the homepage actually ended up, nothing else.
    if final_url:
        checks["https"] = final_url.lower().startswith("https://")

    # On a secure page, files requested over plain http:// get blocked or
    # upgraded by the browser ("mixed content"). Only resources the page
    # loads count - an ordinary link to another http:// site is fine.
    if final_url and final_url.lower().startswith("https://"):
        insecure = re.findall(r"<(?:script|img|iframe|source|video|audio)\b[^>]*\bsrc\s*=\s*[\"']http://", html, re.I)
        insecure += [
            tag
            for tag in re.findall(r"<link\b[^>]*>", html, re.I)
            if re.search(r"rel\s*=\s*[\"']?stylesheet", tag, re.I) and re.search(r"href\s*=\s*[\"']http://", tag, re.I)
        ]
        checks["secureAssets"] = not insecure
    return out


# -------------------------------------------------------------------- merge


def teardown(domain: str, api_key: str) -> dict | None:
    """Run both halves and merge. None when neither could run at all."""
    url = f"https://{domain}/"
    psi = run_pagespeed(url, api_key)
    html, final_url = fetch_html(url)
    if html is None:
        html, final_url = fetch_html(f"http://{domain}/")
    scripts = same_origin_scripts(html, final_url or url) if html else []
    page = analyse_html(html, final_url, scripts) if html else {"checks": {}}

    if not psi.get("checks") and not page.get("checks") and len(psi) <= 1 and len(page) <= 1:
        return None

    # Google's results win where both have an answer (HTTPS): the HTML-side
    # check only fills in when Google's test didn't run.
    merged = {"v": 1, "checks": {**page.get("checks", {}), **psi.get("checks", {})}}
    for source in (page, psi):
        for k, v in source.items():
            if k != "checks":
                merged[k] = v
    return merged
