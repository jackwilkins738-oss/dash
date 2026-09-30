"""The client-site starter kit: one site.json in, a finished multi-page site out.

The step after "Draft their site". Once the client has confirmed the facts,
they go in outreach/sites/<firm>/site.json (the draft writes a starter one),
and this builds outreach/sites/<firm>/site/ - the folder "Publish site" puts
live. Hand-coded HTML and one small CSS file, no framework, so it loads fast
on a phone and scores 90+ without tuning.

What every build gets, so none of it is forgotten on a client:
  - home, services, gallery, reviews, contact, thanks, privacy and 404 pages
  - a page per town they cover (areas/<town>.html) - how local search finds them
  - the enquiry form wired to the dashboard (photos too), page-view tracking,
    and the dashboard's live gallery and reviews
  - sticky call / WhatsApp / quote bar on phones, tap-to-call everywhere
  - Google's LocalBusiness, FAQ and breadcrumb data, sitemap.xml, robots.txt,
    _redirects (their old URLs) and _headers (caching, security) for Pages
  - the registered company details a limited company must show

And what it refuses to do: go live with anything unconfirmed. Any "[Confirm"
left in site.json stops the build (use --draft to preview it anyway: a
banner, and noindex so Google never sees it). A star rating is only shown
when both the rating and the number of reviews are given - never invented.

    python scripts/site_kit.py init  kerr-roofing           # a starter site.json
    python scripts/site_kit.py build kerr-roofing [--draft]
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
DASH_ORIGIN = "https://admin.scalardigital.co.uk"
PLACEHOLDER = re.compile(r"\[confirm|\btodo\b|lorem ipsum", re.I)
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
SCHEMA_TYPE = {
    "roofing": "RoofingContractor",
    "lofts": "GeneralContractor",
    "extensions": "GeneralContractor",
    "building": "GeneralContractor",
    "driveways": "HomeAndConstructionBusiness",
    "landscaping": "HomeAndConstructionBusiness",
    "plumbing": "Plumber",
    "electrical": "Electrician",
}

STARTER = {
    "business": "[Confirm: trading name]",
    "trade": "roofing",
    "domain": "[Confirm: theirdomain.co.uk]",
    "headline": "[Confirm: one line that says what they do and why they're the one to call]",
    "lede": "[Confirm: two sentences in their voice]",
    "phone": "[Confirm: the number customers should ring]",
    "whatsapp": "",
    "email": "[Confirm: the email enquiries should show]",
    "colour": "#1f5f8b",
    "logo": "",
    "hero_photo": "",
    "hours": "[Confirm: e.g. Mon-Fri 8am-6pm, Sat 9am-1pm]",
    "years_trading": None,
    "guarantee": "",
    "accreditations": [],
    "services": [{"name": "[Confirm: main service]", "summary": "[Confirm]", "details": "", "photo": ""}],
    "areas": [{"town": "[Confirm: main town]", "note": ""}],
    "reviews": {"google_url": "", "rating": None, "count": None, "quotes": []},
    "faqs": [],
    "gallery": {"photos": [], "from_dashboard": True},
    "company": {"legal_name": "", "number": "", "registered_office": "", "vat": ""},
    "dashboard": {"tenant_id": "[Confirm: from /admin]", "site_key": "[Confirm: from /admin]"},
    "redirects": [],
}


class SiteError(Exception):
    """A problem with site.json that has to be fixed before the site can be built."""


# ---------------------------------------------------------------- helpers

esc = html.escape


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "page"


def tel(phone: str) -> str:
    digits = re.sub(r"[^\d+]", "", phone)
    return "+44" + digits[1:] if digits.startswith("0") else digits


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _luminance(h: str) -> float:
    def ch(c: int) -> float:
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = _hex_to_rgb(h)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def readable(h: str) -> str:
    """Their colour, darkened just enough for white text on it to pass (4.5:1)."""
    r, g, b = _hex_to_rgb(h)
    for _ in range(40):
        colour = f"#{r:02x}{g:02x}{b:02x}"
        if (1.05) / (_luminance(colour) + 0.05) >= 4.5:
            return colour
        r, g, b = int(r * 0.92), int(g * 0.92), int(b * 0.92)
    return "#1a1a1a"


def placeholders(value, path: str = "") -> list[str]:
    """Every "[Confirm..." / TODO left anywhere in the config, as dotted paths."""
    if isinstance(value, dict):
        return [p for k, v in value.items() for p in placeholders(v, f"{path}.{k}" if path else k)]
    if isinstance(value, list):
        return [p for i, v in enumerate(value) for p in placeholders(v, f"{path}[{i}]")]
    return [path] if isinstance(value, str) and PLACEHOLDER.search(value) else []


# ---------------------------------------------------------------- config


def load(folder: Path, draft: bool = False) -> dict:
    path = folder / "site.json"
    if not path.exists():
        raise SiteError(f"No site.json in {folder} - run: python scripts/site_kit.py init {folder.name}")
    try:
        cfg = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise SiteError(f"site.json isn't valid JSON: {e}")
    problems = validate(cfg, folder, draft)
    if problems:
        raise SiteError("Fix these in site.json first:\n  - " + "\n  - ".join(problems))
    return cfg


def validate(cfg: dict, folder: Path, draft: bool = False) -> list[str]:
    out: list[str] = []
    for key in ("business", "headline", "phone", "domain"):
        if not str(cfg.get(key) or "").strip():
            out.append(f"{key} is empty")
    if not cfg.get("services"):
        out.append("services: list at least one")
    if not cfg.get("areas"):
        out.append("areas: list at least the main town")
    if not HEX.match(str(cfg.get("colour") or "")):
        out.append('colour: a hex colour like "#1f5f8b"')
    phone_digits = re.sub(r"\D", "", str(cfg.get("phone") or ""))
    if cfg.get("phone") and not PLACEHOLDER.search(str(cfg["phone"])) and not 10 <= len(phone_digits) <= 13:
        out.append("phone: doesn't look like a UK number")
    domain = str(cfg.get("domain") or "")
    if domain and not PLACEHOLDER.search(domain) and not re.fullmatch(r"[a-z0-9.-]+\.[a-z]{2,}", domain):
        out.append('domain: just the domain, e.g. "kerrroofing.co.uk" (no https://, no slash)')
    reviews = cfg.get("reviews") or {}
    if (reviews.get("rating") is None) != (reviews.get("count") is None):
        out.append("reviews: give both rating and count (a rating alone isn't shown to Google), or neither")
    if reviews.get("rating") is not None and not (0 < float(reviews["rating"]) <= 5):
        out.append("reviews.rating: between 0 and 5")
    for key in ("logo", "hero_photo"):
        if cfg.get(key) and not (folder / cfg[key]).is_file():
            out.append(f"{key}: {cfg[key]} not found in {folder.name}/")
    for i, s in enumerate(cfg.get("services") or []):
        if s.get("photo") and not (folder / s["photo"]).is_file():
            out.append(f"services[{i}].photo: {s['photo']} not found")
    for p in (cfg.get("gallery") or {}).get("photos") or []:
        if not (folder / p).is_file():
            out.append(f"gallery.photos: {p} not found")
    dash = cfg.get("dashboard") or {}
    if not draft and not (dash.get("tenant_id") and dash.get("site_key")):
        out.append("dashboard: tenant_id and site_key from /admin - without them the enquiry form goes nowhere")
    if not draft:
        left = placeholders(cfg)
        if left:
            out.append("still to confirm with the client (or use --draft to preview): " + ", ".join(left))
    return out


# ---------------------------------------------------------------- assets


def copy_asset(folder: Path, out: Path, rel: str) -> tuple[str, int | None, int | None]:
    """Copies an image into site/img/ -> (url, width, height). Resized to 1600px wide max with Pillow if present."""
    src = folder / rel
    name = slugify(src.stem) + src.suffix.lower()
    dest = out / "img" / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image  # optional: keeps photos a sensible weight

        with Image.open(src) as im:
            im = im.convert("RGB") if src.suffix.lower() in (".jpg", ".jpeg") else im
            if im.width > 1600:
                im = im.resize((1600, round(im.height * 1600 / im.width)))
            im.save(dest, quality=82, optimize=True) if src.suffix.lower() in (".jpg", ".jpeg", ".webp") else im.save(dest)
            return f"/img/{name}", im.width, im.height
    except ImportError:
        shutil.copyfile(src, dest)
        return f"/img/{name}", None, None


def img(url: str, w: int | None, h: int | None, alt: str, cls: str = "", eager: bool = False) -> str:
    size = f' width="{w}" height="{h}"' if w and h else ""
    load_attr = ' fetchpriority="high"' if eager else ' loading="lazy" decoding="async"'
    return f'<img src="{esc(url)}" alt="{esc(alt)}"{size}{load_attr}{f" class={chr(34)}{cls}{chr(34)}" if cls else ""}>'


# ---------------------------------------------------------------- page parts


def css(colour: str) -> str:
    brand = readable(colour)
    return (HERE / "site_kit.css").read_text(encoding="utf-8").replace("--brand-in: #1f5f8b", f"--brand-in: {brand}")


def page(cfg: dict, *, path: str, title: str, description: str, body: str, crumbs: list[tuple[str, str]] | None = None,
         schema: list[dict] | None = None, draft: bool = False, extra_script: str = "") -> str:
    base = f"https://{cfg['domain']}"
    biz = cfg["business"]
    nav = [("/", "Home"), ("/services.html", "Services"), ("/gallery.html", "Our work"), ("/reviews.html", "Reviews"),
           ("/areas/", "Areas"), ("/contact.html", "Get a quote")]
    nav_html = "".join(
        f'<a href="{href}"{" aria-current=page" if href == path or (href == "/areas/" and path.startswith("/areas/")) else ""}'
        f'{" class=nav-cta" if href == "/contact.html" else ""}>{label}</a>'
        for href, label in nav)
    logo = cfg.get("_logo")
    brand_mark = (img(logo[0], logo[1], logo[2], biz, "logo", eager=True) if logo else f'<span class="wordmark">{esc(biz)}</span>')
    blocks = list(schema or [])
    if crumbs:
        blocks.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": name, "item": base + href} for i, (href, name) in enumerate(crumbs)]})
    ld = "".join('<script type="application/ld+json">' + json.dumps(b, ensure_ascii=False).replace("</", "<\\/") + "</script>" for b in blocks)
    dash = cfg.get("dashboard") or {}
    live = connected(cfg)
    track = (f'<script src="{DASH_ORIGIN}/track.js" data-tenant="{esc(dash["tenant_id"])}" data-site-key="{esc(dash["site_key"])}" defer></script>'
             if live else "")
    # The dashboard's own gallery and reviews, only on the pages that show them.
    if live and 'id="project-gallery"' in body:
        track += f'\n<script src="{DASH_ORIGIN}/gallery.js" data-tenant="{esc(dash["tenant_id"])}" defer></script>'
    if live and 'id="testimonials-list"' in body:
        track += f'\n<script src="{DASH_ORIGIN}/testimonials.js" data-tenant="{esc(dash["tenant_id"])}" defer></script>'
    if extra_script:
        track += f"\n<script>{extra_script}</script>"
    wa = cfg.get("whatsapp")
    bar = (f'<nav class="mobile-bar" aria-label="Contact"><a href="tel:{tel(cfg["phone"])}">Call</a>'
           + (f'<a href="https://wa.me/{esc(re.sub(r"[^0-9]", "", wa))}">WhatsApp</a>' if wa else "")
           + '<a href="/contact.html" class="primary">Free quote</a></nav>')
    company = cfg.get("company") or {}
    legal = ""
    if company.get("number"):
        legal = (f'<p class="legal">{esc(company.get("legal_name") or biz)} is registered in England and Wales, company no. '
                 f'{esc(company["number"])}{". Registered office: " + esc(company["registered_office"]) if company.get("registered_office") else ""}'
                 f'{". VAT no. " + esc(company["vat"]) if company.get("vat") else ""}.</p>')
    banner = ('<div class="draft-banner">Draft for review - not live. Some details still to confirm.</div>' if draft else "")
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{base}{path}">
{'<meta name="robots" content="noindex">' if draft else ''}
<meta name="theme-color" content="{readable(cfg['colour'])}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:type" content="website">
<meta property="og:url" content="{base}{path}">
{f'<meta property="og:image" content="{base}{cfg["_hero"][0]}">' if cfg.get("_hero") else ''}
<link rel="icon" href="{esc(logo[0]) if logo else '/favicon.svg'}">
<link rel="stylesheet" href="/site.css">
{ld}
</head>
<body>
{banner}
<a class="skip" href="#main">Skip to content</a>
<header class="site-header">
  <div class="wrap header-row">
    <a class="brand" href="/">{brand_mark}</a>
    <nav class="main-nav" aria-label="Main">{nav_html}</nav>
    <a class="header-phone" href="tel:{tel(cfg['phone'])}">{esc(cfg['phone'])}</a>
    <details class="mobile-menu"><summary aria-label="Menu"><span></span></summary><nav aria-label="Main">{nav_html}</nav></details>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-footer">
  <div class="wrap footer-grid">
    <div>
      <p class="footer-name">{esc(biz)}</p>
      <p>{esc(cfg.get('hours') or '')}</p>
      <p><a href="tel:{tel(cfg['phone'])}">{esc(cfg['phone'])}</a>{f'<br><a href="mailto:{esc(cfg["email"])}">{esc(cfg["email"])}</a>' if cfg.get('email') else ''}</p>
    </div>
    <div>
      <p class="footer-head">Services</p>
      <ul>{''.join(f'<li><a href="/services.html#{slugify(s["name"])}">{esc(s["name"])}</a></li>' for s in cfg['services'][:6])}</ul>
    </div>
    <div>
      <p class="footer-head">Areas we cover</p>
      <ul>{''.join(f'<li><a href="/areas/{slugify(a["town"])}.html">{esc(a["town"])}</a></li>' for a in cfg['areas'][:8])}</ul>
    </div>
  </div>
  <div class="wrap footer-base">
    {legal}
    <p><a href="/privacy.html">Privacy</a> · Site by <a href="https://www.scalardigital.co.uk" rel="noopener">Scalar Digital</a></p>
  </div>
</footer>
{bar}
{track}
</body>
</html>
"""


def connected(cfg: dict) -> bool:
    """Whether the site is wired to a business on the dashboard (real ids, not placeholders)."""
    dash = cfg.get("dashboard") or {}
    return bool(dash.get("tenant_id") and dash.get("site_key")
                and not PLACEHOLDER.search(str(dash["tenant_id"]) + str(dash["site_key"])))


def cta_band(cfg: dict, heading: str = "Get a free, no-obligation quote") -> str:
    wa = cfg.get("whatsapp")
    return f"""<section class="cta-band"><div class="wrap">
  <h2>{esc(heading)}</h2>
  <p>Tell us about the job and we'll come back to you{', usually the same day' if cfg.get('same_day_reply') else ''}.</p>
  <div class="actions"><a class="btn" href="/contact.html">Request a quote</a><a class="btn ghost" href="tel:{tel(cfg['phone'])}">Call {esc(cfg['phone'])}</a>{f'<a class="btn ghost" href="https://wa.me/{esc(re.sub(r"[^0-9]", "", wa))}">WhatsApp us</a>' if wa else ''}</div>
</div></section>"""


def trust_row(cfg: dict) -> str:
    items = []
    if cfg.get("years_trading"):
        items.append(f"<li><b>{int(cfg['years_trading'])}+ years</b> trading</li>")
    if cfg.get("guarantee"):
        items.append(f"<li><b>Guaranteed</b> {esc(cfg['guarantee'])}</li>")
    rv = cfg.get("reviews") or {}
    if rv.get("rating") is not None and rv.get("count"):
        items.append(f"<li><b>{float(rv['rating']):.1f}★</b> from {int(rv['count'])} reviews</li>")
    items += [f"<li>{esc(a)}</li>" for a in (cfg.get("accreditations") or [])[:3]]
    return f'<ul class="trust">{"".join(items)}</ul>' if items else ""


def service_cards(cfg: dict, link: bool = True) -> str:
    cards = []
    for s in cfg["services"]:
        anchor = f"/services.html#{slugify(s['name'])}"
        photo = s.get("_photo")
        cards.append(f"""<article class="card">
  {img(photo[0], photo[1], photo[2], s['name']) if photo else ''}
  <h3>{f'<a href="{anchor}">{esc(s["name"])}</a>' if link else esc(s['name'])}</h3>
  <p>{esc(s.get('summary') or '')}</p>
</article>""")
    return f'<div class="cards">{"".join(cards)}</div>'


def faq_html(faqs: list[dict]) -> str:
    if not faqs:
        return ""
    items = "".join(f"<details><summary>{esc(f['q'])}</summary><p>{esc(f['a'])}</p></details>" for f in faqs)
    return f'<section class="section"><div class="wrap narrow"><h2>Questions we get asked</h2><div class="faq">{items}</div></div></section>'


def reviews_html(cfg: dict, limit: int | None = None) -> str:
    rv = cfg.get("reviews") or {}
    quotes = (rv.get("quotes") or [])[: limit or None]
    cards = "".join(f'<figure class="review"><blockquote>{esc(q["text"])}</blockquote><figcaption>{esc(q.get("name") or "")}</figcaption></figure>'
                    for q in quotes)
    live = ('<div data-testimonials hidden><div id="testimonials-list" class="reviews"></div></div>' if connected(cfg) and not limit else "")
    more = f'<p><a class="text-link" href="{esc(rv["google_url"])}" rel="noopener">Read all our reviews on Google</a></p>' if rv.get("google_url") else ""
    if not (cards or live or more):
        return ""
    return f'<div class="reviews">{cards}</div>{live}{more}'


# ---------------------------------------------------------------- pages


def local_business(cfg: dict) -> dict:
    base = f"https://{cfg['domain']}"
    data: dict = {
        "@context": "https://schema.org",
        "@type": SCHEMA_TYPE.get(cfg.get("trade", ""), "HomeAndConstructionBusiness"),
        "@id": f"{base}/#business",
        "name": cfg["business"],
        "url": base + "/",
        "telephone": tel(cfg["phone"]),
        "areaServed": [{"@type": "City", "name": a["town"]} for a in cfg["areas"]],
        "makesOffer": [{"@type": "Offer", "itemOffered": {"@type": "Service", "name": s["name"]}} for s in cfg["services"]],
    }
    if cfg.get("email"):
        data["email"] = cfg["email"]
    if cfg.get("_logo"):
        data["logo"] = base + cfg["_logo"][0]
    if cfg.get("_hero"):
        data["image"] = base + cfg["_hero"][0]
    addr = cfg.get("address") or {}
    if addr.get("show") and addr.get("town"):
        data["address"] = {"@type": "PostalAddress", "streetAddress": addr.get("street", ""), "addressLocality": addr["town"],
                           "postalCode": addr.get("postcode", ""), "addressCountry": "GB"}
    rv = cfg.get("reviews") or {}
    if rv.get("rating") is not None and rv.get("count"):
        data["aggregateRating"] = {"@type": "AggregateRating", "ratingValue": float(rv["rating"]), "reviewCount": int(rv["count"])}
    same = [u for u in [rv.get("google_url")] + list(cfg.get("social") or []) if u]
    if same:
        data["sameAs"] = same
    return data


def faq_schema(faqs: list[dict]) -> list[dict]:
    if not faqs:
        return []
    return [{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": [
        {"@type": "Question", "name": f["q"], "acceptedAnswer": {"@type": "Answer", "text": f["a"]}} for f in faqs]}]


def home(cfg: dict, draft: bool) -> str:
    hero = cfg.get("_hero")
    main_town = cfg["areas"][0]["town"]
    body = f"""<section class="hero{' has-photo' if hero else ''}">
  {img(hero[0], hero[1], hero[2], cfg['business'] + ' - recent work', 'hero-photo', eager=True) if hero else ''}
  <div class="wrap hero-inner">
    <p class="eyebrow">{esc(cfg.get('trade_label') or 'Serving ' + main_town + ' and surrounding areas')}</p>
    <h1>{esc(cfg['headline'])}</h1>
    <p class="lede">{esc(cfg.get('lede') or '')}</p>
    <div class="actions"><a class="btn" href="/contact.html">Get a free quote</a><a class="btn ghost" href="tel:{tel(cfg['phone'])}">Call {esc(cfg['phone'])}</a></div>
    {trust_row(cfg)}
  </div>
</section>
<section class="section"><div class="wrap">
  <h2>What we do</h2>
  {service_cards(cfg)}
</div></section>
{gallery_section(cfg, limit=6, heading='Recent work', more=True)}
{('<section class="section alt"><div class="wrap"><h2>What customers say</h2>' + reviews_html(cfg, limit=3) + '</div></section>') if reviews_html(cfg, 3) else ''}
<section class="section"><div class="wrap">
  <h2>Areas we cover</h2>
  <ul class="chips">{''.join(f'<li><a href="/areas/{slugify(a["town"])}.html">{esc(a["town"])}</a></li>' for a in cfg['areas'])}</ul>
</div></section>
{faq_html(cfg.get('faqs') or [])}
{cta_band(cfg)}"""
    town = cfg["areas"][0]["town"]
    return page(cfg, path="/", title=f"{cfg['business']} | {cfg.get('title_trade') or 'Local trade specialists'} in {town}",
                description=cfg.get("lede") or cfg["headline"], body=body,
                schema=[local_business(cfg)] + faq_schema(cfg.get("faqs") or []), draft=draft)


def gallery_section(cfg: dict, limit: int | None = None, heading: str = "Our work", more: bool = False) -> str:
    photos = cfg.get("_gallery") or []
    shown = photos[:limit] if limit else photos
    tiles = "".join(f'<figure>{img(u, w, h, cfg["business"] + " - completed job")}</figure>' for u, w, h in shown)
    live = ('<div data-project-gallery hidden><div id="project-gallery" class="gallery"></div></div>'
            if (cfg.get("gallery") or {}).get("from_dashboard", True) and connected(cfg) and not limit else "")
    if not (tiles or live):
        return ""
    link = '<p><a class="text-link" href="/gallery.html">See more of our work</a></p>' if more else ""
    return f'<section class="section"><div class="wrap"><h2>{esc(heading)}</h2><div class="gallery">{tiles}</div>{live}{link}</div></section>'


def services_page(cfg: dict, draft: bool) -> str:
    rows = []
    for s in cfg["services"]:
        photo = s.get("_photo")
        rows.append(f"""<article class="service" id="{slugify(s['name'])}">
  {img(photo[0], photo[1], photo[2], s['name']) if photo else ''}
  <div><h2>{esc(s['name'])}</h2><p class="lede">{esc(s.get('summary') or '')}</p>
  {''.join(f'<p>{esc(p)}</p>' for p in str(s.get('details') or '').split(chr(10)) if p.strip())}
  <a class="btn small" href="/contact.html?service={slugify(s['name'])}">Quote for {esc(s['name'].lower())}</a></div>
</article>""")
    body = f"""<section class="page-head"><div class="wrap"><h1>Our services</h1><p class="lede">Everything we do, across {esc(cfg['areas'][0]['town'])} and the surrounding area.</p></div></section>
<section class="section"><div class="wrap services">{''.join(rows)}</div></section>
{faq_html(cfg.get('faqs') or [])}
{cta_band(cfg)}"""
    return page(cfg, path="/services.html", title=f"Services | {cfg['business']}", description=f"{cfg['business']}: " + ", ".join(s['name'] for s in cfg['services'][:5]) + ".",
                body=body, crumbs=[("/", "Home"), ("/services.html", "Services")], schema=faq_schema(cfg.get("faqs") or []), draft=draft)


def area_page(cfg: dict, area: dict, draft: bool) -> str:
    town = area["town"]
    note = area.get("note") or ""
    others = [a for a in cfg["areas"] if a is not area][:8]
    body = f"""<section class="page-head"><div class="wrap">
  <p class="eyebrow">Areas we cover</p>
  <h1>{esc(cfg.get('title_trade') or 'Trusted local trades')} in {esc(town)}</h1>
  <p class="lede">{esc(note) if note else f"{esc(cfg['business'])} works across {esc(town)} - " + esc(', '.join(s['name'].lower() for s in cfg['services'][:3])) + ", and more."}</p>
  <div class="actions"><a class="btn" href="/contact.html?area={slugify(town)}">Get a free quote in {esc(town)}</a><a class="btn ghost" href="tel:{tel(cfg['phone'])}">Call {esc(cfg['phone'])}</a></div>
</div></section>
<section class="section"><div class="wrap"><h2>What we do in {esc(town)}</h2>{service_cards(cfg)}</div></section>
{('<section class="section alt"><div class="wrap"><h2>What customers say</h2>' + reviews_html(cfg, limit=3) + '</div></section>') if reviews_html(cfg, 3) else ''}
{('<section class="section"><div class="wrap"><h2>Also nearby</h2><ul class="chips">' + ''.join(f'<li><a href="/areas/{slugify(a["town"])}.html">{esc(a["town"])}</a></li>' for a in others) + '</ul></div></section>') if others else ''}
{cta_band(cfg, f'Need a quote in {town}?')}"""
    path = f"/areas/{slugify(town)}.html"
    return page(cfg, path=path, title=f"{cfg.get('title_trade') or 'Local trades'} in {town} | {cfg['business']}",
                description=f"{cfg['business']} in {town}: " + ", ".join(s['name'].lower() for s in cfg['services'][:4]) + ". Free quotes.",
                body=body, crumbs=[("/", "Home"), ("/areas/", "Areas"), (path, town)], draft=draft)


def areas_index(cfg: dict, draft: bool) -> str:
    body = f"""<section class="page-head"><div class="wrap"><h1>Areas we cover</h1><p class="lede">Based in {esc(cfg['areas'][0]['town'])}, working across:</p></div></section>
<section class="section"><div class="wrap"><ul class="chips big">{''.join(f'<li><a href="/areas/{slugify(a["town"])}.html">{esc(a["town"])}</a></li>' for a in cfg['areas'])}</ul>
<p>Not on the list? <a class="text-link" href="/contact.html">Ask us</a> - we often travel further for the right job.</p></div></section>
{cta_band(cfg)}"""
    return page(cfg, path="/areas/", title=f"Areas we cover | {cfg['business']}", description=f"{cfg['business']} covers " + ", ".join(a['town'] for a in cfg['areas'][:8]) + ".",
                body=body, crumbs=[("/", "Home"), ("/areas/", "Areas")], draft=draft)


def gallery_page(cfg: dict, draft: bool) -> str:
    section = gallery_section(cfg) or '<section class="section"><div class="wrap"><p>Photos of recent jobs are on their way.</p></div></section>'
    body = f'<section class="page-head"><div class="wrap"><h1>Our work</h1><p class="lede">Recent jobs, photographed on site.</p></div></section>{section}{cta_band(cfg)}'
    return page(cfg, path="/gallery.html", title=f"Our work | {cfg['business']}", description=f"Recent work by {cfg['business']}.",
                body=body, crumbs=[("/", "Home"), ("/gallery.html", "Our work")], draft=draft)


def reviews_page(cfg: dict, draft: bool) -> str:
    content = reviews_html(cfg) or "<p>Reviews from recent customers are on their way.</p>"
    body = f'<section class="page-head"><div class="wrap"><h1>Reviews</h1>{trust_row(cfg)}</div></section><section class="section"><div class="wrap">{content}</div></section>{cta_band(cfg)}'
    return page(cfg, path="/reviews.html", title=f"Reviews | {cfg['business']}", description=f"What customers say about {cfg['business']}.",
                body=body, crumbs=[("/", "Home"), ("/reviews.html", "Reviews")], draft=draft)


def contact_page(cfg: dict, draft: bool) -> str:
    services = "".join(f'<option value="{esc(s["name"])}" data-slug="{slugify(s["name"])}">{esc(s["name"])}</option>' for s in cfg["services"])
    wa = cfg.get("whatsapp")
    body = f"""<section class="page-head"><div class="wrap"><h1>Get a free quote</h1><p class="lede">Tell us about the job. Photos help us price it without a visit.</p></div></section>
<section class="section"><div class="wrap contact-grid">
  <form class="quote-form" data-lead-form data-lead-redirect="/thanks.html" method="post" action="/thanks.html">
    <label>Your name<input name="name" autocomplete="name" required></label>
    <label>Phone<input name="phone" type="tel" autocomplete="tel" required></label>
    <label>Email<input name="email" type="email" autocomplete="email"></label>
    <label>What do you need?<select name="job_type"><option value="">Choose one</option>{services}<option value="Something else">Something else</option></select></label>
    <label>About the job<textarea name="message" rows="5" placeholder="Where, roughly how big, and anything we should know"></textarea></label>
    <label>Photos (optional, up to 5)<input type="file" name="photos" multiple accept="image/*"></label>
    <button class="btn" type="submit">Send my enquiry</button>
    <p class="small">We only use your details to reply to this enquiry. <a href="/privacy.html">Privacy</a></p>
  </form>
  <aside class="contact-side">
    <h2>Rather talk?</h2>
    <p><a class="big-link" href="tel:{tel(cfg['phone'])}">{esc(cfg['phone'])}</a></p>
    {f'<p><a class="btn ghost" href="https://wa.me/{esc(re.sub(r"[^0-9]", "", wa))}">Message us on WhatsApp</a></p>' if wa else ''}
    {f'<p><a href="mailto:{esc(cfg["email"])}">{esc(cfg["email"])}</a></p>' if cfg.get('email') else ''}
    <p>{esc(cfg.get('hours') or '')}</p>
  </aside>
</div></section>"""
    # The dashboard takes name/email/phone/message, so the job type rides in the
    # message. A window capture listener runs before track.js's own (document)
    # one, so the message it sends already has it.
    script = ("(function(){var f=document.querySelector('.quote-form');if(!f)return;var sel=f.elements.job_type;"
              "var want=new URLSearchParams(location.search).get('service');if(want){for(var i=0;i<sel.options.length;i++){"
              "if(sel.options[i].getAttribute('data-slug')===want)sel.selectedIndex=i;}}"
              "window.addEventListener('submit',function(e){if(e.target!==f||f.dataset.done)return;var m=f.elements.message;"
              "if(sel.value){m.value='Job: '+sel.value+(m.value?'\\n'+m.value:'');}f.dataset.done='1';},true);})();")
    return page(cfg, path="/contact.html", title=f"Get a free quote | {cfg['business']}", description=f"Request a free quote from {cfg['business']}.",
                body=body, crumbs=[("/", "Home"), ("/contact.html", "Get a quote")], draft=draft, extra_script=script)


def simple_page(cfg: dict, path: str, title: str, heading: str, html_body: str, draft: bool, index: bool = True) -> str:
    body = f'<section class="page-head"><div class="wrap narrow"><h1>{esc(heading)}</h1></div></section><section class="section"><div class="wrap narrow prose">{html_body}</div></section>'
    out = page(cfg, path=path, title=f"{title} | {cfg['business']}", description=title, body=body, draft=draft)
    return out if index else out.replace("<meta charset=\"utf-8\">", "<meta charset=\"utf-8\">\n<meta name=\"robots\" content=\"noindex\">", 1)


def privacy_html(cfg: dict) -> str:
    company = cfg.get("company") or {}
    who = esc(company.get("legal_name") or cfg["business"])
    return f"""<p>{who} ("we") uses the details you send through this website only to reply to your enquiry and, if you go ahead, to carry out and invoice the work.</p>
<h2>What we collect</h2><p>The name, phone number, email, message and any photos you send us, and anonymous counts of which pages are visited (no cookies, no advertising trackers).</p>
<h2>Where it's kept</h2><p>Enquiries are stored securely in our customer system, run for us by Scalar Digital, with servers in the EU. We never sell or share your details for marketing.</p>
<h2>How long</h2><p>Enquiries that don't go ahead are deleted within 24 months. Records of work we carry out are kept for as long as the law requires (usually 6 years).</p>
<h2>Your rights</h2><p>You can ask to see, correct or delete your details at any time: {f'<a href="mailto:{esc(cfg["email"])}">{esc(cfg["email"])}</a> or ' if cfg.get('email') else ''}<a href="tel:{tel(cfg['phone'])}">{esc(cfg['phone'])}</a>. You can also complain to the Information Commissioner's Office (ico.org.uk).</p>
<p class="small">Last updated {date.today().strftime('%B %Y')}.</p>"""


# ---------------------------------------------------------------- build


def build(folder: Path, draft: bool = False) -> dict:
    """Builds folder/site/ from folder/site.json -> a summary of what was written."""
    cfg = load(folder, draft)
    out = folder / "site"
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    cfg["_logo"] = copy_asset(folder, out, cfg["logo"]) if cfg.get("logo") else None
    cfg["_hero"] = copy_asset(folder, out, cfg["hero_photo"]) if cfg.get("hero_photo") else None
    for s in cfg["services"]:
        s["_photo"] = copy_asset(folder, out, s["photo"]) if s.get("photo") else None
    cfg["_gallery"] = [copy_asset(folder, out, p) for p in (cfg.get("gallery") or {}).get("photos") or []]

    pages: dict[str, str] = {
        "index.html": home(cfg, draft),
        "services.html": services_page(cfg, draft),
        "gallery.html": gallery_page(cfg, draft),
        "reviews.html": reviews_page(cfg, draft),
        "contact.html": contact_page(cfg, draft),
        "areas/index.html": areas_index(cfg, draft),
        "thanks.html": simple_page(cfg, "/thanks.html", "Thank you", "Thanks - we've got your enquiry",
                                   f'<p>We\'ll be in touch shortly. If it\'s urgent, call <a href="tel:{tel(cfg["phone"])}">{esc(cfg["phone"])}</a>.</p><p><a class="btn" href="/">Back to the home page</a></p>',
                                   draft, index=False),
        "privacy.html": simple_page(cfg, "/privacy.html", "Privacy", "Privacy", privacy_html(cfg), draft),
        "404.html": simple_page(cfg, "/404.html", "Page not found", "Sorry, that page isn't here",
                                '<p>It may have moved. Try the <a href="/">home page</a> or <a href="/services.html">our services</a>.</p>', draft, index=False),
    }
    for a in cfg["areas"]:
        pages[f"areas/{slugify(a['town'])}.html"] = area_page(cfg, a, draft)

    for rel, text in pages.items():
        (out / rel).parent.mkdir(parents=True, exist_ok=True)
        (out / rel).write_text(text, encoding="utf-8")
    (out / "site.css").write_text(css(cfg["colour"]), encoding="utf-8")
    (out / "favicon.svg").write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="{readable(cfg["colour"])}"/>'
        f'<text x="32" y="43" font-family="Arial,sans-serif" font-size="34" font-weight="700" fill="#fff" text-anchor="middle">{esc(cfg["business"][:1].upper())}</text></svg>',
        encoding="utf-8")

    base = f"https://{cfg['domain']}"
    indexed = [p for p in pages if p not in ("thanks.html", "404.html")]
    urls = ["/" if p == "index.html" else "/" + p.replace("index.html", "") for p in indexed]
    (out / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{base}{u}</loc><lastmod>{date.today().isoformat()}</lastmod></url>\n" for u in urls)
        + "</urlset>\n", encoding="utf-8")
    (out / "robots.txt").write_text("User-agent: *\n" + ("Disallow: /\n" if draft else f"Allow: /\n\nSitemap: {base}/sitemap.xml\n"), encoding="utf-8")
    redirects = [f"{src} {dst} 301" for src, dst in (cfg.get("redirects") or [])]
    redirects += ["/index.html / 301", "/areas /areas/ 301"]
    (out / "_redirects").write_text("\n".join(redirects) + "\n", encoding="utf-8")
    (out / "_headers").write_text("""/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  X-Frame-Options: SAMEORIGIN
/img/*
  Cache-Control: public, max-age=31536000, immutable
/site.css
  Cache-Control: public, max-age=86400
""", encoding="utf-8")
    return {"folder": str(out), "pages": sorted(pages), "draft": draft}


def starter_config(f: dict) -> dict:
    """A site.json from what "Draft their site" already knows (site_draft.facts plus the client's onboarding
    answers, if they've sent them). Whatever the client told us is taken as confirmed; whatever was only
    guessed from their old site is marked [Confirm ...], so it can't go live until someone has checked it."""
    told = f.get("told") or {}
    site = f.get("site") or {}
    files = f.get("files") or []
    lines = lambda text: [x.strip(" -*•\t") for x in re.split(r"[\n,;]+", str(text or "")) if x.strip(" -*•\t")]  # noqa: E731
    confirm = lambda v, what: v if v else f"[Confirm: {what}]"  # noqa: E731
    cfg = json.loads(json.dumps(STARTER))
    cfg["business"] = f.get("business") or cfg["business"]
    cfg["trade"] = re.sub(r"[^a-z]", "", str(f.get("trade") or "").lower().split(" ")[0]) or "building"
    from urllib.parse import urlparse

    website = str(f.get("website") or "")
    cfg["domain"] = confirm((urlparse(website if "//" in website else "//" + website).hostname or "").removeprefix("www."),
                            "their domain")
    cfg["phone"] = told.get("phone") or confirm(f.get("phone"), "the number customers should ring")
    cfg["email"] = told.get("enquiry_email") or confirm(f.get("email"), "the email to show")
    cfg["hours"] = told.get("hours") or cfg["hours"]
    if site.get("colour") and HEX.match(str(site["colour"])):
        cfg["colour"] = site["colour"]
    if told.get("years_trading") and str(told["years_trading"]).isdigit():
        cfg["years_trading"] = int(told["years_trading"])
    cfg["guarantee"] = told.get("guarantee") or ""
    extras = [told.get("memberships"), (f"£{told['insurance_amount']} public liability" if told.get("insurance_amount") else told.get("insurance"))]
    cfg["accreditations"] = [x for x in (lines(extras[0]) + [extras[1]]) if x][:3]
    services = lines(told.get("services")) or [f"[Confirm: {x}]" for x in (site.get("services") or [])[:6]]
    if services:
        cfg["services"] = [{"name": n, "summary": "[Confirm: one line about it]", "details": "", "photo": ""} for n in services]
    areas = lines(told.get("areas")) or ([f"[Confirm: {f['area']}]"] if f.get("area") else [])
    if areas:
        cfg["areas"] = [{"town": a, "note": ""} for a in areas]
    # The trade's own copy from site_draft (TRADE_COPY): a headline and lede written for their
    # customers, one-liners for the services it recognises, and the usual questions - whose
    # answers are still [Confirm ...] until the client gives them.
    copy = f.get("copy") or {}
    if copy.get("headline"):
        cfg["headline"] = copy["headline"]
    if copy.get("lede"):
        cfg["lede"] = copy["lede"]
    known = {name.lower(): line for name, line in copy.get("services") or []}
    for svc in cfg["services"]:
        name = re.sub(r"^\[Confirm: |\]$", "", svc["name"]).lower()
        match = known.get(name) or next((line for k, line in known.items() if k in name or name in k), None)
        if match:
            svc["summary"] = match
    cfg["faqs"] = [{"q": q, "a": a} for q, a in copy.get("faqs") or []]
    if told.get("about"):
        cfg["lede"] = str(told["about"]).strip()[:300]
    logo = next((x["path"] for x in files if x.get("kind") == "logo"), "")
    photos = [x["path"] for x in files if x.get("kind") == "photo"]
    cfg["logo"] = logo
    cfg["hero_photo"] = photos[0] if photos else ""
    cfg["gallery"]["photos"] = photos[1:13]
    if f.get("company_number"):
        cfg["company"] = {"legal_name": f.get("registered_name") or "", "number": f["company_number"],
                          "registered_office": f.get("address") or "", "vat": ""}
    cfg["address"] = {"show": str(told.get("show_address") or "").lower() in ("yes", "true", "1")}
    return cfg


def init(folder: Path, facts: dict | None = None) -> Path:
    path = folder / "site.json"
    if path.exists():
        raise SiteError(f"{path} already exists - edit it rather than starting again.")
    folder.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(starter_config(facts) if facts else STARTER, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def outreach_dir() -> Path:
    for parent in [HERE.parent, *HERE.parents]:
        if (parent / "outreach").is_dir():
            return parent / "outreach"
    return HERE.parent / "outreach"


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a client's site from outreach/sites/<firm>/site.json.")
    ap.add_argument("command", choices=["init", "build"])
    ap.add_argument("firm", help="the folder name under outreach/sites, e.g. kerr-roofing")
    ap.add_argument("--draft", action="store_true", help="build even with details still to confirm (marked as a draft, hidden from Google)")
    args = ap.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,80}", args.firm):
        sys.exit("The folder name is lowercase letters, numbers and dashes, e.g. kerr-roofing.")
    folder = outreach_dir() / "sites" / args.firm
    try:
        if args.command == "init":
            print(f"Starter written: {init(folder)}\nFill it in with the client's confirmed details, then build.")
            return
        result = build(folder, draft=args.draft)
    except SiteError as e:
        sys.exit(str(e))
    print(f"{'DRAFT ' if result['draft'] else ''}Site built: {result['folder']} ({len(result['pages'])} pages)")
    for p in result["pages"]:
        print(f"  {p}")
    print("READY to publish." if not result["draft"] else "Draft only - finish site.json and build again before publishing.")


if __name__ == "__main__":
    main()
