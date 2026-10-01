"""Print-ready letters: one A4 page per firm, with their own QR code to their preview page.

Used by push_prospects.py --letters (the panel's "Make letters"). Writes an
HTML file you open in the browser and print, or save as PDF - no extra
software beyond `segno` for the QR codes (python -m pip install segno).

Layout: the recipient's address sits where a DL window envelope shows it
(left-hand window, A4 folded in three), your details top right, the QR code
and the typed link at the foot of the letter.

The words come from two templates you can edit in the panel (saved in
outreach/): one for firms with a website and a preview page, one for firms
with no website. Placeholders in {braces} are filled per firm; a sentence
whose facts aren't known (no score yet, say) is simply left out - the rule
from the preview pages holds: nothing is claimed that wasn't measured.
"""

from __future__ import annotations

import html
import re
from datetime import date
from pathlib import Path

DEFAULT_TEMPLATE = """Dear {greeting},

I was looking at {website} and ran it through Google's own mobile speed test. {score_sentence} {issue_sentence}

I build fast, hand-coded websites for {trade_plural}, and I've put together a short preview of what a new site for {business} could look like - next to how your current one measures up. Scan the code below with your phone's camera to see it. There's nothing to sign up for.

If it's of interest, I'd be glad to talk it through: reply to {sender_email} or call {sender_phone}.

Kind regards,

{signoff}"""

DEFAULT_TEMPLATE_NO_WEBSITE = """Dear {greeting},

I couldn't find a website for {business}. These days most people check a firm online before they pick up the phone - and without a site, those enquiries go to whoever does have one.

I build fast, hand-coded websites for {trade_plural}: a fixed price, and the site is yours outright. Scan the code below with your phone's camera to see the kind of site I build, and what it costs.

If it's of interest, I'd be glad to talk it through: reply to {sender_email} or call {sender_phone}.

Kind regards,

{signoff}"""

TRADE_PLURALS = {
    "roofing": "roofing firms",
    "loft conversions": "loft conversion firms",
    "driveways & patios": "driveway and patio firms",
    "landscaping": "landscapers",
    "building & extensions": "builders",
}

PLACEHOLDERS = (
    "greeting", "business", "website", "score_sentence", "issue_sentence", "trade_plural",
    "sender_email", "sender_phone", "signoff", "area",
)


def score_sentence(score: float | None) -> str:
    """Google's own bands - the same wording the preview page uses."""
    if score is None:
        return ""
    s = int(score)
    band = "good" if s >= 90 else "needing improvement" if s >= 50 else "poor"
    return f"It scored {s} out of 100 on mobile, which Google itself counts as {band}."


def fill(template: str, values: dict[str, str]) -> str:
    """Known placeholders only; anything else in braces is left exactly as typed."""
    out = template
    for key in PLACEHOLDERS:
        out = out.replace("{" + key + "}", values.get(key, ""))
    # A sentence placeholder that came out empty leaves double spaces behind.
    out = re.sub(r"[ \t]{2,}", " ", out)
    return "\n".join(line.rstrip() for line in out.split("\n"))


def load_templates(outreach: Path) -> tuple[str, str]:
    paths = (outreach / "letter-template.txt", outreach / "letter-template-no-website.txt")
    defaults = (DEFAULT_TEMPLATE, DEFAULT_TEMPLATE_NO_WEBSITE)
    return tuple(p.read_text(encoding="utf-8") if p.exists() else d for p, d in zip(paths, defaults))  # type: ignore[return-value]


def save_templates(outreach: Path, with_site: str, no_site: str) -> None:
    outreach.mkdir(exist_ok=True)
    (outreach / "letter-template.txt").write_text(with_site.replace("\r\n", "\n"), encoding="utf-8")
    (outreach / "letter-template-no-website.txt").write_text(no_site.replace("\r\n", "\n"), encoding="utf-8")


def qr_svg(url: str) -> str:
    import segno

    return segno.make_qr(url, error="m").svg_data_uri(scale=4, border=0, dark="#000")


def address_lines(address: str) -> list[str]:
    parts = [p.strip() for p in re.split(r",|\n", address or "") if p.strip()]
    return parts[:6]


def render(letters: list[dict], sender: dict[str, str], today: date | None = None) -> str:
    """letters: dicts with business, contact, address, url, short_url, body. Returns the HTML page."""
    today = today or date.today()
    dated = f"{today.day} {today.strftime('%B %Y')}"
    sender_block = "<br>".join(html.escape(x) for x in (sender.get("name", ""), sender.get("email", ""), sender.get("phone", ""), sender.get("site", "")) if x)
    pages = []
    for letter in letters:
        to = [letter["contact"]] if letter.get("contact") else []
        to += [letter["business"]] + address_lines(letter.get("address", ""))
        paragraphs = "".join(f"<p>{html.escape(p).replace(chr(10), '<br>')}</p>" for p in re.split(r"\n\s*\n", letter["body"].strip()))
        pages.append(f"""
<section class="letter">
  <div class="from">{sender_block}</div>
  <div class="to">{"<br>".join(html.escape(x) for x in to)}</div>
  <div class="date">{dated}</div>
  <div class="body">{paragraphs}</div>
  <div class="qr">
    <img src="{letter['qr']}" alt="QR code">
    <div>Scan with your phone's camera, or type:<br><b>{html.escape(letter['short_url'])}</b></div>
  </div>
</section>""")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Letters - {len(letters)}</title>
<style>
  @page {{ size: A4; margin: 0; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #888; font: 11pt/1.5 Georgia, 'Times New Roman', serif; color: #111; }}
  .letter {{ width: 210mm; height: 297mm; margin: 10mm auto; background: #fff; position: relative; padding: 20mm 22mm; page-break-after: always; overflow: hidden; }}
  .from {{ position: absolute; top: 18mm; right: 22mm; text-align: right; font: 9.5pt/1.45 Arial, sans-serif; color: #333; }}
  /* DL window envelope, left window: about 20mm in, 45mm down, 90 x 35mm. */
  .to {{ position: absolute; top: 50mm; left: 22mm; width: 90mm; height: 35mm; font: 10.5pt/1.35 Arial, sans-serif; }}
  .date {{ position: absolute; top: 92mm; left: 22mm; }}
  .body {{ position: absolute; top: 104mm; left: 22mm; right: 22mm; }}
  .body p {{ margin: 0 0 3.2mm; }}
  .qr {{ position: absolute; bottom: 20mm; left: 22mm; right: 22mm; display: flex; gap: 6mm; align-items: center; border-top: 0.3mm solid #ccc; padding-top: 5mm; font: 9.5pt/1.4 Arial, sans-serif; color: #333; }}
  .qr img {{ width: 30mm; height: 30mm; }}
  @media print {{ body {{ background: none; }} .letter {{ margin: 0; }} .noprint {{ display: none; }} }}
  .noprint {{ max-width: 210mm; margin: 10mm auto 0; background: #fffbe6; padding: 4mm 6mm; font: 10pt Arial, sans-serif; border-radius: 2mm; }}
</style></head><body>
<div class="noprint"><b>{len(letters)} letters.</b> Print with Ctrl+P - paper A4, margins "None", scale 100%, background graphics off. Fold in three for a DL window envelope. Or choose "Save as PDF".</div>
{"".join(pages)}
</body></html>"""
