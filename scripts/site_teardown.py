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


def run_pagespeed(url: str, api_key: str, timeout: int = 180) -> dict:
    """Checks from Google's mobile test. Empty dict if the test couldn't run."""
    params = [("url", url), ("strategy", "mobile"), ("key", api_key)]
    params += [("category", c) for c in ("performance", "seo", "accessibility", "best-practices")]
    endpoint = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(endpoint, timeout=timeout) as res:
            data = json.loads(res.read())
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return {}

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
