"""The single worst problem a teardown found, as words for an email.

Mirrors the order and titles of teardownFindings() in lib/teardown.ts - the
same "What we found" list the prospect sees on their preview page - so the
email names the problem at the top of that list. If you change the order or
wording there, change it here too.

Used by push_prospects.py for the Mailmeteor file's {{top_issue}} column:
    "I had a look at your website and noticed {{top_issue}}."
"""

from __future__ import annotations

# Thresholds, the same as lib/teardown.ts: a homepage over 4 MB, a server slower than 1.8s to answer
# (Google calls 0.6s the target), and layout shift past Google's "poor" line (0.25).
HEAVY_PAGE_KB = 4000
SLOW_SERVER_MS = 1800
JUMPY_PAGE = 25

HOSTED_BUILDERS = {"wix": "Wix", "squarespace": "Squarespace", "godaddy": "GoDaddy's website builder", "weebly": "Weebly", "duda": "Duda"}


def _mb(kb: float) -> str:
    return f"{kb / 1000:.1f} MB" if kb >= 1000 else f"{round(kb)} KB"


def all_issues(t: dict | None, current_year: int) -> list[str]:
    """Every finding, most important first, phrased to follow "I noticed ..." - plain words a tradesperson
    would use, each something they can check on their own site."""
    if not t:
        return []
    c = t.get("checks") or {}
    out: list[str] = []
    if c.get("indexable") is False:
        out.append("your homepage is set to tell Google not to list it")
    if c.get("mobileViewport") is False:
        out.append("your site isn't set up for phones - it shows the desktop page shrunk down")
    if c.get("phoneShown") is False:
        out.append("there's no phone number on your homepage")
    elif c.get("tapToCall") is False:
        out.append("your phone number isn't tap-to-call on a mobile")
    if c.get("contactForm") is False:
        out.append("there's no enquiry form on your homepage")
    if c.get("showsReviews") is False:
        out.append("your homepage doesn't show any customer reviews")
    weight = t.get("pageWeightKb") or 0
    if weight >= HEAVY_PAGE_KB:
        out.append(f"your homepage is {_mb(weight)} to download on a phone")
    elif (t.get("imageSavingsKb") or 0) >= 500:
        out.append(f"your images could be {_mb(t['imageSavingsKb'])} lighter, which slows the site on a phone")
    if (t.get("serverResponseMs") or 0) >= SLOW_SERVER_MS:
        out.append(f"your web server takes {t['serverResponseMs'] / 1000:.1f}s before the page even starts to load")
    if (t.get("layoutShift100") or 0) >= JUMPY_PAGE:
        out.append("the page jumps about while it loads, so it's easy to tap the wrong thing")
    if c.get("readableText") is False:
        out.append("some of the text on your site is too small to read on a phone")
    if c.get("tapTargets") is False:
        out.append("some buttons and links on your site are too small to tap on a phone")
    if c.get("imageAlt") is False:
        out.append("your photos have no descriptions, so Google can't tell what work they show")
    year = t.get("copyrightYear")
    if year is not None and year < current_year - 1:
        out.append(f"your website footer still says © {year}")
    if c.get("businessEmail") is False:
        out.append("your site gives a Gmail/Hotmail-style email rather than one at your own web address")
    if c.get("localSchema") is False:
        out.append("your site doesn't tell Google your trade and area the way it reads them for local searches")
    if c.get("pageTitle") is False:
        out.append("your homepage has no proper title for Google")
    elif c.get("metaDescription") is False:
        out.append("your homepage has no description for Google to show")
    seo = t.get("seoScore")
    if seo is not None and seo < 80:
        out.append(f"Google's own SEO check scores your homepage {seo}/100")
    platform = t.get("platform")
    if platform in HOSTED_BUILDERS:
        out.append(f"your site is on {HOSTED_BUILDERS[platform]}, a subscription you don't own")
    elif platform == "wordpress" and (t.get("wpPluginCount") or 0) >= 10:
        out.append(f"your homepage loads {t['wpPluginCount']} WordPress plugins")
    if c.get("whatsapp") is False:
        out.append("there's no WhatsApp link on your site")
    if c.get("secureAssets") is False and c.get("https") is not False:
        out.append("your homepage loads some files over an insecure connection")
    if c.get("https") is False:
        out.append("browsers show your site as \"Not secure\"")
    return out


def top_issue(t: dict | None, current_year: int) -> str:
    issues = all_issues(t, current_year)
    return issues[0] if issues else ""
