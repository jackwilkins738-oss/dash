"""The proposal that goes with a quote: one printable page, personalised to the firm.

Made by the panel's Calls tab "Quote" button alongside the quote itself, and saved as
outreach/sites/<firm>/proposal-<quote number>.html ("Open proposal" opens it; print it to
PDF to attach to your email, or take it to a meeting). It says where their current site
stands (from your speed-check log), exactly what they get, how the build runs, the price
and how it's paid, the link to accept online, and the full terms they'd be agreeing to -
the same terms the quote carries (terms.py), so the paper and the online quote never differ.

Nothing is invented: a fact that isn't known (no speed check, no website) is left out.
"""

from __future__ import annotations

import html
import re
from datetime import date, timedelta
from pathlib import Path

import terms

LABELS = {"build": "The Scalar build", "landing": "Landing page"}
STEPS = [
    ("A plan and a fixed price", "This proposal. The price doesn't move once we start."),
    ("Built from scratch", "Every page hand-coded and written for your business - no page-builder, no theme. "
                           "You see real progress as it happens."),
    ("You check it before it goes live", "On your own phone, before anything is public. Tweaks to what we agreed are included."),
    ("Launch and aftercare", "Live on your domain, then {days} days of free tweaks and fixes. After that it's yours - "
                             "no monthly fee on your website."),
]


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")[:60] or "firm"


def path_for(outreach: Path, business: str, quote_number: str) -> Path:
    return outreach / "sites" / _slug(business) / f"proposal-{_slug(quote_number) or 'quote'}.html"


def _money(pence: int) -> str:
    pounds = pence / 100
    return f"£{pounds:,.0f}" if pounds == int(pounds) else f"£{pounds:,.2f}"


def where_now(before: dict, website: str, trade: str, area: str) -> list[str]:
    """What's true about their current site - only what was measured."""
    out = []
    try:
        score = int(float(before.get("mobile_score") or ""))
    except ValueError:
        score = None
    try:
        lcp = float(before.get("lcp_s") or "")
    except ValueError:
        lcp = None
    if score is not None:
        verdict = "which Google counts as poor" if score < 50 else "which Google counts as needing improvement" if score < 90 else "which is good"
        out.append(f"{website} scores {score}/100 on Google's mobile speed test, {verdict}.")
    if lcp is not None and lcp > 2.5:
        out.append(f"On a phone it takes {lcp:g} seconds to show its main content - Google's own target is 2.5.")
    issue = str(before.get("top_issue") or "").strip()
    if issue:
        out.append(f"The biggest problem found: {issue[0].lower() + issue[1:]}.".replace("..", "."))
    if not website:
        where = f" in {area}" if area else ""
        out.append(f"You don't have a website yet, so people searching for {trade.lower() or 'your trade'}{where} "
                   "can only find the firms that do.")
    return out


def render(facts: dict) -> str:
    """facts: business, contact, website, trade, area, before, package, founding, quote_number, total_pence,
    vat_rate, deposit_percent, quote_url, expires, from_name, from_email, from_phone."""
    e = lambda v: html.escape(str(v or ""), quote=True)  # noqa: E731
    package, founding = facts["package"], bool(facts.get("founding")) and facts["package"] == "build"
    deposit_pct = facts["deposit_percent"]
    total = facts["total_pence"]
    deposit = round(total * deposit_pct / 100) if deposit_pct else 0
    days = terms.AFTERCARE_DAYS[package]
    now = where_now(facts.get("before") or {}, facts.get("website") or "", facts.get("trade") or "", facts.get("area") or "")
    included = terms.included(package, founding)
    full_terms = terms.terms(package, deposit_pct, facts.get("vat_rate", 0), founding)
    greeting = f"Prepared for {e(facts.get('contact'))}, {e(facts['business'])}" if facts.get("contact") else f"Prepared for {e(facts['business'])}"
    contact_bits = " &middot; ".join(e(x) for x in (facts.get("from_email"), facts.get("from_phone")) if x)
    if deposit and deposit < total:
        pay_rows = (f"<tr><td>Deposit on acceptance ({deposit_pct}%)</td><td>{_money(deposit)}</td></tr>"
                    f"<tr><td>Balance when your site is ready to go live</td><td>{_money(total - deposit)}</td></tr>")
    elif deposit:
        pay_rows = f"<tr><td>Paid on acceptance</td><td>{_money(total)}</td></tr>"
    else:
        pay_rows = f"<tr><td>Paid when your site is ready to go live</td><td>{_money(total)}</td></tr>"
    vat_note = "Includes VAT at 20%." if facts.get("vat_rate") == 20 else "No VAT is charged."
    steps = "".join(f"<li><strong>{e(t)}</strong><span>{e(d.format(days=days))}</span></li>" for t, d in STEPS)
    return f"""<!doctype html>
<html lang="en-GB"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Proposal for {e(facts['business'])} - {e(terms.BUSINESS)}</title>
<style>
  @page {{ size: A4; margin: 16mm 16mm 18mm; }}
  :root {{ --ink: #14181f; --muted: #5b6573; --line: #dde2e8; --accent: #1f5f99; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: #f4f5f7; color: var(--ink); font: 15px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
  main {{ max-width: 800px; margin: 24px auto; background: #fff; padding: 48px 56px; box-shadow: 0 10px 40px rgba(20,24,31,.08); }}
  header {{ display: flex; justify-content: space-between; align-items: flex-start; gap: 24px; border-bottom: 2px solid var(--ink); padding-bottom: 20px; }}
  .brand {{ font-weight: 800; letter-spacing: .02em; }}
  .meta {{ text-align: right; color: var(--muted); font-size: 13px; }}
  h1 {{ font-size: 30px; line-height: 1.15; margin: 28px 0 4px; letter-spacing: -.01em; }}
  .for {{ color: var(--muted); margin: 0 0 8px; }}
  h2 {{ font-size: 13px; text-transform: uppercase; letter-spacing: .12em; color: var(--accent); margin: 34px 0 10px; }}
  ul.ticks {{ list-style: none; padding: 0; margin: 0; columns: 2; column-gap: 28px; }}
  ul.ticks li {{ break-inside: avoid; padding: 4px 0 4px 22px; position: relative; }}
  ul.ticks li::before {{ content: "\\2713"; position: absolute; left: 0; color: var(--accent); font-weight: 700; }}
  ol.steps {{ list-style: none; counter-reset: s; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }}
  ol.steps li {{ counter-increment: s; border-top: 2px solid var(--line); padding-top: 10px; font-size: 13px; color: var(--muted); }}
  ol.steps li::before {{ content: counter(s); display: block; font-weight: 800; color: var(--accent); }}
  ol.steps strong {{ display: block; color: var(--ink); font-size: 14px; margin-bottom: 4px; }}
  table {{ width: 100%; border-collapse: collapse; }}
  td {{ padding: 9px 0; border-bottom: 1px solid var(--line); }}
  td:last-child {{ text-align: right; font-variant-numeric: tabular-nums; }}
  tr.total td {{ font-weight: 800; font-size: 18px; border-bottom: 2px solid var(--ink); }}
  .note {{ color: var(--muted); font-size: 13px; margin: 8px 0 0; }}
  .accept {{ margin-top: 30px; padding: 20px 22px; border: 2px solid var(--accent); border-radius: 10px; }}
  .accept a {{ color: var(--accent); word-break: break-all; font-weight: 600; }}
  .terms {{ white-space: pre-line; font-size: 12px; color: #333b46; columns: 2; column-gap: 28px; }}
  .terms-page {{ break-before: page; }}
  footer {{ margin-top: 28px; color: var(--muted); font-size: 12px; border-top: 1px solid var(--line); padding-top: 12px; }}
  @media (max-width: 640px) {{ main {{ margin: 0; padding: 28px 20px; }} ul.ticks, .terms {{ columns: 1; }} ol.steps {{ grid-template-columns: 1fr 1fr; }} }}
  @media print {{ body {{ background: #fff; }} main {{ margin: 0; padding: 0; box-shadow: none; max-width: none; }} }}
</style></head>
<body><main>
<header><div class="brand">{e(terms.BUSINESS)}</div>
<div class="meta">Quote {e(facts.get('quote_number'))}<br>{e(date.today().strftime('%d %B %Y'))}{'<br>Valid until ' + e(facts['expires']) if facts.get('expires') else ''}</div></header>
<h1>A new website for {e(facts['business'])}</h1>
<p class="for">{greeting}</p>
{('<h2>Where you are now</h2>' + ''.join(f'<p>{e(x)}</p>' for x in now)) if now else ''}
<h2>What you get: {e(LABELS[package])}{' - founding client' if founding else ''}</h2>
<ul class="ticks">{''.join(f'<li>{e(i)}</li>' for i in included)}</ul>
<h2>How it runs</h2>
<ol class="steps">{steps}</ol>
<h2>The price</h2>
<table><tr class="total"><td>{e(LABELS[package])} - fixed price</td><td>{_money(total)}</td></tr>{pay_rows}</table>
<p class="note">{e(vat_note)} {e(terms.payment_terms(deposit_pct))} Not included: {e(terms.EXCLUSIONS)}</p>
<div class="accept"><strong>To go ahead, accept online:</strong><br><a href="{e(facts['quote_url'])}">{e(facts['quote_url'])}</a>
<p class="note">You'll see this quote and the terms below, and sign by typing your name. Any questions first, just ask.</p></div>
<footer>{e(facts.get('from_name') or terms.BUSINESS)}{' &middot; ' + contact_bits if contact_bits else ''} &middot; scalardigital.co.uk</footer>
<section class="terms-page"><h2>Terms of business</h2><div class="terms">{e(full_terms)}</div></section>
</main></body></html>
"""


def make(outreach: Path, sheet: str, key: str, business: str, package: str, result: dict, settings: dict,
         founding: bool = False, fallback: dict | None = None) -> Path:
    """Writes the proposal for a quote just made; returns its path."""
    from launch_report import before_from_log
    from push_prospects import domain_of
    from site_draft import find_row

    fb = fallback or {}
    try:
        row = find_row(outreach, sheet, key) or {}
    except Exception:  # an unreadable sheet shouldn't cost them the proposal
        row = {}
    get = lambda col, k: str(row.get(col) or fb.get(k) or "").strip()  # noqa: E731
    website = domain_of(get("Website", "website"))
    vat = 20 if str(settings.get("QUOTE_VAT_RATE") or "0").strip() == "20" else 0
    try:
        deposit = max(0, min(100, int(float(settings.get("QUOTE_DEPOSIT_PERCENT") or 0))))
    except ValueError:
        deposit = 0
    facts = {
        "business": business, "contact": get("Contact name", "contact"), "website": website,
        "trade": get("Trade", "trade"), "area": get("Area", "area"),
        "before": before_from_log(outreach, website) if website else {},
        "package": package, "founding": founding, "quote_number": result.get("quote_number") or "",
        "total_pence": int(result.get("total_pence") or 0), "vat_rate": vat, "deposit_percent": deposit,
        "quote_url": result["quote_url"],
        # The dashboard's default life for a quote (app/api/prospects/quote: expires_days 30).
        "expires": (date.today() + timedelta(days=30)).strftime("%d %B %Y"),
        "from_name": settings.get("MAIL_FROM_NAME") or settings.get("LETTER_SIGNOFF") or "",
        "from_email": settings.get("LETTER_EMAIL") or settings.get("MAIL_ADDRESS") or "",
        "from_phone": settings.get("LETTER_PHONE") or "",
    }
    path = path_for(outreach, business, facts["quote_number"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(facts), encoding="utf-8")
    return path
