"""A head start on the build: a client brief and a one-page draft site, for a firm that's said yes.

Used by the panel's Calls tab ("Draft their site"). For one firm it gathers
everything already known - the sheet (Companies House details, contact,
phone, email), the speed check, the found contacts - and reads their current
homepage for what they say about themselves: services, headings, logo,
brand colour and photos. It writes, in outreach/sites/<firm>/:

    brief.md     every fact in one place, and a checklist for the call
    index.html   a single-page draft in their name, colour, services and area

It is a draft, not a finished site. Anything that was guessed or needs the
client's say-so (services, areas, years trading, guarantees, the address to
show) is highlighted in yellow; "Hide highlights" in the draft's top bar
turns them off for showing it to the client. Nothing here is uploaded
anywhere - it stays on this computer, like the rest of outreach/.

    python scripts/site_draft.py outreach/<sheet>.xlsx "no:01234567"
"""

from __future__ import annotations

import argparse
import csv
import html as htmllib
import re
import sys
import urllib.parse
from collections import Counter
from datetime import datetime
from pathlib import Path

import overrides

# Words the firm's own services are picked out by, on top of trade_guess's vocabularies.
SERVICE_WORDS = [
    "roof", "slate", "tile", "tiling", "fascia", "soffit", "gutter", "chimney", "lead", "flat roof", "felt", "epdm", "grp",
    "loft", "dormer", "mansard", "hip to gable", "velux", "skylight",
    "driveway", "paving", "patio", "resin", "tarmac", "block", "imprinted", "kerb", "drainage",
    "landscap", "garden", "turf", "lawn", "fencing", "fence", "decking", "wall", "groundwork", "tree", "hedge",
    "extension", "renovation", "refurb", "conversion", "new build", "kitchen", "bathroom", "brickwork", "plaster",
    "repair", "installation", "maintenance", "restoration", "insulation", "pointing", "cladding", "porch", "garage",
]
NOT_SERVICES = re.compile(r"\b(home|about|contact|blog|news|gallery|portfolio|reviews?|testimonials?|faq|privacy|cookie|"
                          r"terms|login|sign in|menu|call|quote|search|areas?|our work|projects?|careers|jobs)\b", re.I)

# Customer-facing copy per trade: written to speak to their customers, not to the firm.
# The services are only used when their own site doesn't list any.
TRADE_COPY: dict[str, dict] = {
    "roofing": {
        "headline": "Roofing done properly, first time.",
        "lede": "New roofs, repairs and everything in between, from a local team that turns up when it says it will.",
        "services": [
            ("Roof repairs", "Leaks, slipped slates and storm damage found and fixed, not patched over."),
            ("Re-roofing", "Full strip and re-roof in slate or tile, with the old roof taken away."),
            ("Flat roofs", "Long-lasting flat roofs for extensions, garages and dormers."),
            ("Chimneys and leadwork", "Rebuilds, repointing, flashing and lead valleys."),
            ("Fascias, soffits and guttering", "Replacement roofline in uPVC, and gutters cleared or renewed."),
        ],
        "faqs": [
            ("Do you give free quotes?", "[Confirm with the client: free quotes, and how soon they can visit.]"),
            ("Can you help with an emergency leak?", "[Confirm with the client: whether they do emergency call-outs, and the hours.]"),
            ("Is the work guaranteed?", "[Confirm with the client: the guarantee they genuinely give, in years.]"),
        ],
    },
    "lofts": {
        "headline": "More room, without moving house.",
        "lede": "Loft conversions designed, built and signed off, with one team from first visit to finished room.",
        "services": [
            ("Dormer loft conversions", "The most popular way to add full-height space and a new bedroom."),
            ("Hip to gable conversions", "Opens up the side of the roof for a bigger, brighter room."),
            ("Mansard conversions", "The most space a loft can give, where planning allows."),
            ("Velux and roof-light conversions", "The simplest conversion, keeping the roof shape as it is."),
        ],
        "faqs": [
            ("Do I need planning permission?", "Many loft conversions fall under permitted development, but not all. [Confirm with the client: whether they handle planning and building control.]"),
            ("How long does a loft conversion take?", "[Confirm with the client: their typical timescale.]"),
            ("Can we stay in the house during the work?", "[Confirm with the client.]"),
        ],
    },
    "driveways": {
        "headline": "A driveway that makes the whole house look better.",
        "lede": "Block paving, resin, tarmac and patios, laid on a proper base so they stay flat for years.",
        "services": [
            ("Block paving", "Hard-wearing driveways in a wide choice of colours and patterns."),
            ("Resin driveways", "A smooth, permeable finish that drains and needs little upkeep."),
            ("Tarmac", "A tidy, cost-effective surface for drives of any size."),
            ("Patios", "Natural stone and porcelain patios, laid level and properly drained."),
        ],
        "faqs": [
            ("Do you give free quotes?", "[Confirm with the client.]"),
            ("Do I need planning permission for a new driveway?", "Not usually, if the surface is permeable or drains onto your own ground. [Confirm with the client how they handle this.]"),
            ("Is the work guaranteed?", "[Confirm with the client: the guarantee they genuinely give.]"),
        ],
    },
    "landscaping": {
        "headline": "Gardens designed and built to be used.",
        "lede": "Patios, lawns, fencing and planting, from a local team that leaves the place tidy.",
        "services": [
            ("Garden design and landscaping", "A complete garden planned around how you want to use it."),
            ("Patios and paths", "Stone and porcelain, laid level with proper drainage."),
            ("Fencing and gates", "Panel, closeboard and bespoke fencing, put up to last."),
            ("Turf and planting", "New lawns and planting that suit your soil and the light."),
        ],
        "faqs": [
            ("Do you give free quotes?", "[Confirm with the client.]"),
            ("Do you do garden maintenance as well?", "[Confirm with the client.]"),
            ("How far ahead are you booked?", "[Confirm with the client.]"),
        ],
    },
    "building": {
        "headline": "Extensions and building work, done properly.",
        "lede": "Extensions, renovations and conversions, from a local builder that manages the job start to finish.",
        "services": [
            ("House extensions", "Single and double-storey extensions, from the foundations up."),
            ("Renovations", "Whole-house refurbishments and the structural work behind them."),
            ("Garage conversions", "Turn an unused garage into a room you'll use every day."),
            ("General building work", "Brickwork, walls, structural alterations and repairs."),
        ],
        "faqs": [
            ("Do you give free quotes?", "[Confirm with the client.]"),
            ("Do you handle planning and building control?", "[Confirm with the client.]"),
            ("Is the work guaranteed?", "[Confirm with the client: the guarantee they genuinely give.]"),
        ],
    },
    "general": {
        "headline": "Quality work from a local team you can rely on.",
        "lede": "[Confirm with the client: one line on what they do and who for.]",
        "services": [("[Their main service]", "[Confirm with the client.]"), ("[Their second service]", "[Confirm with the client.]"),
                     ("[Their third service]", "[Confirm with the client.]")],
        "faqs": [("Do you give free quotes?", "[Confirm with the client.]")],
    },
}


def trade_key(label: str) -> str:
    t = (label or "").lower()
    for key, words in (("lofts", ["loft"]), ("roofing", ["roof"]), ("driveways", ["drive", "paving", "patio"]),
                       ("landscaping", ["landscap", "garden"]), ("building", ["build", "extension", "construct"])):
        if any(w in t for w in words):
            return key
    return "general"


# ---------------------------------------------------------------- the firm's row


def find_row(outreach: Path, sheet: str, key: str) -> dict | None:
    """The firm's row from any tab of the sheet, with your review decisions applied."""
    import openpyxl

    path = outreach / sheet
    if not path.exists():
        return None
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    decided = overrides.load(outreach, sheet)
    try:
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                continue
            header = [str(h).strip() if h else "" for h in rows[0]]
            for values in rows[1:]:
                row = {h: v for h, v in zip(header, values) if h}
                if overrides.row_key(row) == key:
                    return overrides.apply(row, decided.get(key, {})) or row
    finally:
        wb.close()
    return None


def csv_row(path: Path, column: str, value: str) -> dict:
    if not value or not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return next((r for r in csv.DictReader(f) if (r.get(column) or "").lower() == value.lower()), {})


# ---------------------------------------------------------------- their current site


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", fragment))).strip()


def _grey(hexcode: str) -> bool:
    h = hexcode.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return max(r, g, b) - min(r, g, b) < 40 or max(r, g, b) < 35 or min(r, g, b) > 225


def read_site(page: str, base_url: str) -> dict:
    """What their homepage says about them: services, headings, logo, colour, photos, years trading."""
    body = re.sub(r"<(script|noscript|svg)\b.*?</\1>", " ", page, flags=re.I | re.S)
    title_m = re.search(r"<title[^>]*>(.*?)</title>", body, re.I | re.S)
    desc = ""
    for tag in re.findall(r"<meta[^>]+>", body, re.I):
        if re.search(r"name\s*=\s*[\"']description[\"']", tag, re.I):
            c = re.search(r"content\s*=\s*[\"']([^\"']*)", tag, re.I)
            desc = htmllib.unescape(c.group(1)).strip() if c else ""
    headings = []
    for h in re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", body, re.I | re.S):
        t = _text(h)
        if 3 <= len(t) <= 90 and t not in headings:
            headings.append(t)

    # Services: short link and heading texts that name a job.
    candidates = [_text(a) for a in re.findall(r"<a\b[^>]*>(.*?)</a>", body, re.I | re.S)] + headings
    services: list[str] = []
    for c in candidates:
        c = c.strip(" -|>»•")
        low = c.lower()
        if not (3 <= len(c) <= 40) or NOT_SERVICES.search(c) or not any(w in low for w in SERVICE_WORDS):
            continue
        if re.search(r"\b(in|near|across|around|throughout)\s+[A-Z]", c):  # "Roofing in Guildford" is a tagline, not a service
            continue
        if low not in (s.lower() for s in services):
            services.append(c[0].upper() + c[1:])
    services = services[:8]

    # Brand colour: theme-color, else the commonest non-grey colour in their inline CSS.
    colour = ""
    theme = re.search(r"<meta[^>]+name\s*=\s*[\"']theme-color[\"'][^>]*>", body, re.I)
    if theme:
        m = re.search(r"#[0-9a-f]{6}\b|#[0-9a-f]{3}\b", theme.group(0), re.I)
        colour = m.group(0) if m and not _grey(m.group(0)) else ""
    css = " ".join(re.findall(r"<style[^>]*>(.*?)</style>", page, re.I | re.S)) + " ".join(re.findall(r"style\s*=\s*\"([^\"]*)\"", page, re.I))
    counts = Counter(c.lower() for c in re.findall(r"#[0-9a-f]{6}\b|#[0-9a-f]{3}\b", css, re.I) if not _grey(c))
    if not colour and counts:
        colour = counts.most_common(1)[0][0]

    # Logo and photos (their own - listed in the brief, to ask for the originals).
    logo, photos = "", []
    for tag in re.findall(r"<img\b[^>]*>", page, re.I):
        src = re.search(r"\s(?:data-src|src)\s*=\s*[\"']([^\"']+)", tag, re.I)
        if not src or src.group(1).startswith("data:"):
            continue
        url = urllib.parse.urljoin(base_url, htmllib.unescape(src.group(1)))
        if not logo and re.search(r"logo", tag, re.I):
            logo = url
        elif re.search(r"\.(jpe?g|webp|png)(\?|$)", url, re.I) and not re.search(r"icon|logo|badge|sprite|pixel|avatar", url, re.I):
            if url not in photos:
                photos.append(url)

    text = _text(body)
    years = ""
    m = re.search(r"\b(?:established|est\.?|since|founded)\s+(?:in\s+)?((?:19|20)\d\d)\b", text, re.I)
    if m:
        years = f"since {m.group(1)}"
    else:
        m = re.search(r"\b(\d{1,2})\+?\s+years'?\s+(?:of\s+)?experience\b", text, re.I)
        years = f"{m.group(1)}+ years' experience" if m else ""
    accreditations = sorted({a for a in re.findall(r"\b(Checkatrade|TrustMark|FMB|Federation of Master Builders|NFRC|CompetentRoofer|"
                                                    r"Which\? Trusted Trader|Rated People|MyBuilder|Gas Safe|NICEIC|CITB|CSCS|Marshalls Register|"
                                                    r"Trading Standards|Buy With Confidence|Guild of Master Craftsmen)\b", text, re.I)})
    return {
        "title": _text(title_m.group(1)) if title_m else "", "description": desc, "headings": headings[:12],
        "services": services, "colour": colour, "logo": logo, "photos": photos[:15], "years": years,
        "accreditations": accreditations,
    }


# ---------------------------------------------------------------- the draft


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "firm"


def _darker(hexcode: str, factor: float = 0.7) -> str:
    h = hexcode.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + "".join(f"{int(int(h[i:i + 2], 16) * factor):02x}" for i in (0, 2, 4))


def _confirm(text: str) -> str:
    """Escaped text, with any [Confirm ...] or [...] placeholders highlighted."""
    return re.sub(r"\[([^\]]+)\]", r'<mark class="confirm">\1</mark>', htmllib.escape(text))


def facts(row: dict, contacts: dict, teardown: dict, site: dict | None) -> dict:
    get = lambda k: str(row.get(k) or "").strip()  # noqa: E731
    phone = get("Phone") or contacts.get("phone", "")
    email = get("Email") or contacts.get("email", "")
    return {
        "business": get("Business"), "trade": get("Trade"), "area": get("Area"), "phone": phone, "email": email,
        "contact": get("Contact name") or contacts.get("contact", ""), "website": get("Website"),
        "company_number": get("Company number"), "registered_name": get("Registered name"),
        "address": get("Registered address"), "incorporated": get("Incorporated"), "company_type": get("Company type"),
        "score": teardown.get("mobile_score", ""), "lcp": teardown.get("lcp_s", ""), "top_issue": teardown.get("top_issue", ""),
        "site": site or {},
    }


def draft_html(f: dict) -> str:
    copy = TRADE_COPY[trade_key(f["trade"])]
    site = f["site"]
    esc = htmllib.escape
    name = esc(f["business"])
    brand = site.get("colour") or "#1f4e79"
    area = f["area"]
    tel = re.sub(r"[^\d+]", "", f["phone"])
    call = (f'<a class="btn" href="tel:{esc(tel)}">Call {esc(f["phone"])}</a>' if tel
            else '<a class="btn" href="#quote"><mark class="confirm">Phone number</mark></a>')
    serving = (f'Serving {esc(area)} <mark class="confirm">and surrounding areas - which towns?</mark>' if area
               else '<mark class="confirm">Areas covered - which towns?</mark>')

    if site.get("services"):
        cards = "".join(f'<div class="card"><h3>{esc(s)}</h3><p><mark class="confirm">One line about this, in their words.</mark></p></div>'
                        for s in site["services"][:6])
        services_note = "Taken from their current site - check the list with them."
    else:
        cards = "".join(f'<div class="card"><h3>{_confirm(t)}</h3><p>{_confirm(b)}</p></div>' for t, b in copy["services"])
        services_note = "Usual services for the trade - their site didn't list any. Check with them."
    trust = []
    if site.get("years"):
        trust.append(f'<li><b>Trading {esc(site["years"])}</b></li>')
    elif f["incorporated"]:
        trust.append(f'<li><b>Established {esc(f["incorporated"][:4])}</b> <mark class="confirm">(company date - ask how long they\'ve traded)</mark></li>')
    trust += [f'<li><b>{esc(a)}</b> <mark class="confirm">member? check it\'s current</mark></li>' for a in site.get("accreditations", [])]
    trust += ['<li><b>Fixed, written quotes</b> <mark class="confirm">confirm</mark></li>',
              '<li><b>Guaranteed work</b> <mark class="confirm">how many years?</mark></li>',
              '<li><b>Fully insured</b> <mark class="confirm">confirm public liability cover</mark></li>']
    faqs = "".join(f"<details><summary>{esc(q)}</summary><p>{_confirm(a)}</p></details>" for q, a in copy["faqs"])
    # If their logo won't load (moved, hotlink-blocked), the name shows instead - as text, never as HTML.
    swap = "var b=document.createElement('b');b.textContent=this.alt;this.replaceWith(b)"
    logo = (f'<img src="{esc(site["logo"])}" alt="{name}" class="logo" onerror="{swap}">' if site.get("logo") else f"<b>{name}</b>")
    reg = []
    if f["registered_name"] and f["company_number"]:
        reg.append(f'{esc(f["registered_name"])} · Registered in England &amp; Wales, company no. {esc(f["company_number"])}')
    if f["address"]:
        reg.append(f'Registered office: {esc(f["address"])} <mark class="confirm">(show this address? it may be an accountant\'s)</mark>')
    email = f'<a href="mailto:{esc(f["email"])}">{esc(f["email"])}</a>' if f["email"] else '<mark class="confirm">email address</mark>'
    photos = "".join(f'<div class="ph"><mark class="confirm">Photo of their work #{i}</mark></div>' for i in range(1, 7))

    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{name}{" | " + esc(f["trade"]) + " in " + esc(area) if f["trade"] and area else ""}</title>
<meta name="description" content="{esc(copy['lede'] if not copy['lede'].startswith('[') else f['business'])}">
<meta name="robots" content="noindex">
<style>
:root {{ --brand: {esc(brand)}; --brand-dark: {esc(_darker(brand))}; --ink: #1c1f23; --dim: #5b636d; --line: #e3e6ea; --bg: #fff; --soft: #f5f6f8; }}
* {{ box-sizing: border-box; }}
body {{ margin: 0; font: 17px/1.6 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; color: var(--ink); background: var(--bg); }}
a {{ color: var(--brand-dark); }}
.wrap {{ max-width: 1080px; margin: 0 auto; padding: 0 20px; }}
.draftbar {{ background: #fff3b0; color: #5a4a00; font-size: 14px; padding: 8px 20px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }}
.draftbar button {{ font: inherit; padding: 4px 10px; border: 1px solid #b89b00; background: #fff; border-radius: 6px; cursor: pointer; }}
mark.confirm {{ background: #fff3b0; color: #5a4a00; padding: 0 3px; border-radius: 3px; }}
body.clean mark.confirm {{ background: none; color: inherit; padding: 0; }}
body.clean .draftbar {{ display: none; }}
header {{ position: sticky; top: 0; z-index: 5; background: #fff; border-bottom: 1px solid var(--line); }}
header .wrap {{ display: flex; align-items: center; justify-content: space-between; gap: 12px; min-height: 64px; }}
.logo {{ max-height: 44px; max-width: 180px; }}
.btn {{ display: inline-block; background: var(--brand); color: #fff; text-decoration: none; font-weight: 600; padding: 12px 20px; border-radius: 8px; border: 0; font-size: 17px; cursor: pointer; }}
.btn.alt {{ background: #fff; color: var(--brand-dark); border: 2px solid var(--brand); }}
.hero {{ background: linear-gradient(135deg, var(--brand-dark), var(--brand)); color: #fff; padding: 72px 0 64px; }}
.hero h1 {{ font-size: clamp(30px, 5vw, 48px); line-height: 1.15; margin: 0 0 14px; max-width: 18ch; }}
.hero p {{ font-size: 19px; max-width: 46ch; margin: 0 0 8px; opacity: .95; }}
.hero .btns {{ display: flex; gap: 12px; flex-wrap: wrap; margin-top: 24px; }}
.hero .btn {{ background: #fff; color: var(--brand-dark); }}
.hero .btn.alt {{ background: transparent; color: #fff; border-color: #fff; }}
section {{ padding: 56px 0; }}
section.soft {{ background: var(--soft); }}
h2 {{ font-size: clamp(24px, 3.5vw, 32px); margin: 0 0 8px; }}
.note {{ color: var(--dim); font-size: 14px; margin: 0 0 24px; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 16px; }}
.card {{ background: #fff; border: 1px solid var(--line); border-radius: 12px; padding: 20px; }}
.card h3 {{ margin: 0 0 6px; font-size: 19px; }}
.card p {{ margin: 0; color: var(--dim); }}
.trust {{ list-style: none; padding: 0; display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }}
.trust li {{ background: #fff; border-left: 4px solid var(--brand); padding: 14px 16px; border-radius: 6px; }}
.ph {{ aspect-ratio: 4/3; background: var(--soft); border: 2px dashed var(--line); border-radius: 10px; display: grid; place-items: center; text-align: center; font-size: 14px; }}
details {{ border-bottom: 1px solid var(--line); padding: 14px 0; }}
summary {{ font-weight: 600; cursor: pointer; }}
form {{ display: grid; gap: 12px; max-width: 520px; }}
input, textarea {{ font: inherit; padding: 12px; border: 1px solid #c9ced4; border-radius: 8px; width: 100%; }}
footer {{ background: #15181c; color: #c9ced4; padding: 40px 0 90px; font-size: 14px; }}
footer a {{ color: #fff; }}
.callbar {{ position: fixed; left: 0; right: 0; bottom: 0; display: none; background: var(--brand); text-align: center; padding: 12px; z-index: 6; }}
.callbar a {{ color: #fff; font-weight: 700; text-decoration: none; font-size: 18px; }}
@media (max-width: 700px) {{ .callbar {{ display: block; }} header .btn {{ display: none; }} section {{ padding: 44px 0; }} }}
</style>
</head>
<body>
<div class="draftbar">Draft for {name}: yellow = to confirm with them. <button type="button" onclick="document.body.classList.add('clean')">Hide highlights</button></div>
<header><div class="wrap">{logo}{call}</div></header>

<div class="hero"><div class="wrap">
  <h1>{_confirm(copy["headline"])}</h1>
  <p>{_confirm(copy["lede"])}</p>
  <p>{serving}</p>
  <div class="btns">{call}<a class="btn alt" href="#quote">Get a free quote</a></div>
</div></div>

<section><div class="wrap">
  <h2>What we do</h2>
  <p class="note"><mark class="confirm">{esc(services_note)}</mark></p>
  <div class="grid">{cards}</div>
</div></section>

<section class="soft"><div class="wrap">
  <h2>Why {name}</h2>
  <ul class="trust">{"".join(trust)}</ul>
</div></section>

<section><div class="wrap">
  <h2>Recent work</h2>
  <p class="note"><mark class="confirm">Ask for 6-12 photos of their own jobs - before and after if they have them.</mark></p>
  <div class="grid">{photos}</div>
</div></section>

<section class="soft"><div class="wrap">
  <h2>Questions people ask</h2>
  {faqs}
</div></section>

<section id="quote"><div class="wrap">
  <h2>Get a free quote</h2>
  <p class="note">Tell us about the job and we'll get back to you. <mark class="confirm">How quickly - same day?</mark></p>
  <form onsubmit="event.preventDefault(); alert('Draft only - the real form sends the enquiry straight to their dashboard.');">
    <input placeholder="Your name" required><input placeholder="Phone number" type="tel" required>
    <input placeholder="Postcode"><textarea rows="4" placeholder="What do you need doing?"></textarea>
    <button class="btn" type="submit">Send</button>
  </form>
</div></section>

<footer><div class="wrap">
  <p><b style="color:#fff">{name}</b>{" · " + esc(f["phone"]) if f["phone"] else ""} · {email}</p>
  <p>{"<br>".join(reg)}</p>
</div></footer>
<div class="callbar">{f'<a href="tel:{esc(tel)}">Call {esc(f["phone"])}</a>' if tel else '<a href="#quote">Get a free quote</a>'}</div>
</body>
</html>
"""


def brief_md(f: dict, draft_path: str) -> str:
    site = f["site"]
    line = lambda label, value: f"- **{label}:** {value}" if value else f"- **{label}:** _not known - ask_"  # noqa: E731
    out = [f"# {f['business']} - client brief", "", f"_Made {datetime.now().strftime('%d %B %Y %H:%M')}. Draft site: {draft_path}_", "",
           "## The firm", line("Trade", f["trade"]), line("Area", f["area"]), line("Contact", f["contact"]),
           line("Phone", f["phone"]), line("Email", f["email"]), line("Current website", f["website"]),
           line("Registered name", f["registered_name"]), line("Company number", f["company_number"]),
           line("Company type", f["company_type"]), line("Incorporated", f["incorporated"]),
           line("Registered office", f["address"]), ""]
    out += ["## Their current site"]
    if f["score"] or f["top_issue"]:
        out += [line("Mobile speed score", f["score"]), line("Largest content paint (s)", f["lcp"]),
                line("Biggest problem found", f["top_issue"])]
    if site:
        out += [line("Title", site.get("title")), line("Description", site.get("description")),
                line("Trading", site.get("years")), line("Brand colour (guessed)", site.get("colour")),
                line("Logo", site.get("logo")),
                line("Accreditations named on their site", ", ".join(site.get("accreditations", []))), "",
                "**Services they list:** " + (", ".join(site.get("services", [])) or "_none found - ask_"), "",
                "**Their headings:**", *([f"- {h}" for h in site.get("headings", [])] or ["- _none_"]), "",
                "**Photos on their site** (ask for the originals - don't reuse without their say-so):",
                *([f"- {p}" for p in site.get("photos", [])] or ["- _none found_"])]
    else:
        out.append("- _Couldn't read their homepage - everything below needs asking._")
    out += ["", "## Ask on the call",
            "- [ ] Services: which to show, and the one they most want more of",
            "- [ ] Towns and areas they genuinely cover",
            "- [ ] How long they've been trading",
            "- [ ] Guarantee (years), insurance, and any memberships they currently hold - only real ones go on the site",
            "- [ ] 6-12 photos of their own work, and their logo as a file",
            "- [ ] 3-5 reviews they're happy to show, or their Google/Checkatrade profile link",
            "- [ ] Address to show on the site (the registered office may be their accountant's)",
            "- [ ] Who has the domain login (registrar) and where their email is hosted - so nothing breaks at switch-over",
            "- [ ] Google Business Profile: do they have one, and who can log in",
            "- [ ] Where enquiries should go (email/phone/WhatsApp) and how fast they reply", ""]
    return "\n".join(out)


def make(outreach: Path, sheet: str, key: str, fallback: dict | None = None, fetch: bool = True) -> Path:
    """Writes outreach/sites/<firm>/{brief.md,index.html}; returns the folder."""
    from push_prospects import domain_of

    row = find_row(outreach, sheet, key) or {}
    fb = fallback or {}
    for col, k in (("Business", "business"), ("Website", "website"), ("Email", "email"), ("Phone", "phone"), ("Contact name", "contact")):
        if not str(row.get(col) or "").strip() and fb.get(k):
            row[col] = fb[k]
    if not str(row.get("Business") or "").strip():
        raise ValueError("couldn't find that firm")
    domain = domain_of(str(row.get("Website") or ""))
    contacts = csv_row(outreach / "contacts-found.csv", "website", domain)
    teardown = csv_row(outreach / "teardown-log.csv", "website", domain)
    site = None
    if fetch and domain:
        from site_teardown import fetch_html

        page, final = fetch_html(f"https://{domain}")
        if page is None:
            page, final = fetch_html(f"http://{domain}")
        if page:
            site = read_site(page, final or f"https://{domain}")
    f = facts(row, contacts, teardown, site)
    folder = outreach / "sites" / _slugify(f["business"])
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "index.html").write_text(draft_html(f), encoding="utf-8")
    (folder / "brief.md").write_text(brief_md(f, str(folder / "index.html")), encoding="utf-8")
    return folder


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sheet", type=Path)
    ap.add_argument("key", help='the firm\'s key, e.g. "no:01234567" or "name:acme roofing"')
    args = ap.parse_args()
    try:
        folder = make(args.sheet.parent, args.sheet.name, args.key)
    except ValueError as e:
        sys.exit(str(e))
    print(f"Wrote {folder / 'index.html'} and {folder / 'brief.md'}")


if __name__ == "__main__":
    main()
