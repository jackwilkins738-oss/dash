"""One click from "they're interested" to a quote they can accept and pay.

Used by the panel's Calls tab ("Quote: Scalar build" / "Quote: landing page").
Asks the dashboard (POST /api/prospects/quote) to record the firm as a lead,
create a numbered quote and mark it sent, and hands back the quote's link -
for you to send from your own email (the panel opens a ready-written one).

Prices, VAT and deposit come from the panel's Settings, defaulting to the
website's own prices (lib/site.ts: £750 landing page, £2,500 Scalar build),
no VAT, no deposit. Each quote carries Scalar's terms of business (terms.py), which the
client agrees to when they accept. Every quote is also kept in outreach/quotes-sent.csv.
"""

from __future__ import annotations

import csv
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

PACKAGES = {
    "build": ("QUOTE_PRICE_BUILD", 2500, "The Scalar build: a fast, hand-coded multi-page website, and yours outright"),
    "landing": ("QUOTE_PRICE_LANDING", 750, "Landing page: a fast, hand-coded single-page website, and yours outright"),
}
DEFAULT_TENANT = "abdc6408-1fd5-4fb6-9c4c-53600b571a6d"


class QuoteFailed(Exception):
    pass


def price(settings: dict[str, str], package: str) -> int:
    key, default, _ = PACKAGES[package]
    try:
        value = int(float(settings.get(key) or default))
    except ValueError:
        value = default
    return value if 1 <= value <= 100_000 else default


# Optional extras on every quote (QUOTE_EXTRAS in Settings): the client ticks the ones they want on
# the quote page before signing, and they're added to the price. One line, "name price; name price",
# prices in pounds before VAT. Blank uses these; "none" turns them off.
DEFAULT_EXTRAS = "Extra page 150; Google Business Profile set up and optimised 150; Logo tidy-up 250; Writing your website's words 200"
MAX_EXTRAS = 8


def extras(settings: dict[str, str]) -> list[dict]:
    """[{description, price_pence}] from the QUOTE_EXTRAS setting - entries without a price are skipped."""
    raw = str(settings.get("QUOTE_EXTRAS") or "").strip() or DEFAULT_EXTRAS
    if raw.lower() in ("none", "off", "-"):
        return []
    out = []
    for part in raw.split(";"):
        m = re.fullmatch(r"\s*(.+?)\s+£?(\d{1,5}(?:\.\d{1,2})?)\s*", part)
        if m:
            out.append({"description": m.group(1)[:120], "price_pence": round(float(m.group(2)) * 100)})
    return [e for e in out if e["price_pence"] > 0][:MAX_EXTRAS]


def quote_body(settings: dict[str, str], package: str, founding: bool = False) -> dict:
    """What any quote for this package says - price, deposit, VAT, payment terms, exclusions, terms of
    business, extras - the same whether you send it or they start it from their preview."""
    import terms

    _, _, description = PACKAGES[package]
    founding = founding and package == "build"
    if founding:
        description += " (founding client)"
    vat = 20 if str(settings.get("QUOTE_VAT_RATE") or "0").strip() == "20" else 0
    try:
        deposit = max(0, min(100, int(float(settings.get("QUOTE_DEPOSIT_PERCENT") or 0))))
    except ValueError:
        deposit = 0
    return {
        "line_items": [{"category": "labour", "description": description, "unit_price_pence": price(settings, package) * 100}],
        "vat_rate": vat,
        "deposit_percent": deposit,
        "payment_terms": terms.payment_terms(deposit),
        "exclusions": terms.EXCLUSIONS,
        "terms": terms.terms(package, deposit, vat, founding),
        "optional_items": extras(settings),
    }


def publish_self_serve(settings: dict[str, str], post=None) -> list[str]:
    """Sends both packages' quotes to the dashboard for "See my quote" on preview pages -> lines for the log.
    Raises QuoteFailed if the dashboard can't take them."""
    post = post or _post_template
    api = (settings.get("DASHBOARD_API_URL") or "https://admin.scalardigital.co.uk").rstrip("/")
    out = []
    for package in PACKAGES:
        body = {"tenant_id": settings.get("SCALAR_TENANT_ID") or DEFAULT_TENANT, "package": package,
                "quote": quote_body(settings, package)}
        post(f"{api}/api/prospects/quote-template", body, settings.get("PROSPECTS_API_SECRET", ""))
        out.append(f"{package}: £{price(settings, package):,} published")
    return out


def _post_template(url: str, body: dict, secret: str) -> None:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=30).close()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise QuoteFailed("your dashboard doesn't have self-serve checkout yet") from e
        detail = e.read(300).decode("utf-8", errors="replace")
        raise QuoteFailed(f"the dashboard said HTTP {e.code} {detail}") from e
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise QuoteFailed(f"couldn't reach the dashboard ({getattr(e, 'reason', e)})") from e


def create_quote(settings: dict[str, str], business: str, email: str, phone: str, package: str,
                 slug: str | None = None, note: str = "", founding: bool = False) -> dict:
    """{quote_number, total_pence, quote_url} from the dashboard, or raises QuoteFailed with the reason."""
    if package not in PACKAGES:
        raise QuoteFailed("unknown package")
    body = {
        "tenant_id": settings.get("SCALAR_TENANT_ID") or DEFAULT_TENANT,
        "slug": slug,
        "client_name": business,
        "email": email or None,
        "phone": phone or None,
        "note": note or "Quoted from the outreach call list",
        **quote_body(settings, package, founding),
    }
    api = (settings.get("DASHBOARD_API_URL") or "https://admin.scalardigital.co.uk").rstrip("/")
    req = urllib.request.Request(
        f"{api}/api/prospects/quote",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {settings.get('PROSPECTS_API_SECRET', '')}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            out = json.loads(res.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise QuoteFailed("your dashboard doesn't have the quote update yet") from e
        detail = e.read(300).decode("utf-8", errors="replace")
        raise QuoteFailed(f"the dashboard said HTTP {e.code} {detail}") from e
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise QuoteFailed(f"couldn't reach the dashboard ({getattr(e, 'reason', e)})") from e
    if not out.get("quote_url"):
        raise QuoteFailed("the dashboard didn't return a quote link")
    return out


def record(outreach: Path, sheet: str, key: str, business: str, package: str, result: dict) -> None:
    path = outreach / "quotes-sent.csv"
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["key", "sheet", "business", "package", "quote_number", "total", "quote_url", "at"])
        if new:
            w.writeheader()
        w.writerow({"key": key, "sheet": sheet, "business": business, "package": package,
                    "quote_number": result.get("quote_number", ""), "total": f"{(result.get('total_pence') or 0) / 100:.2f}",
                    "quote_url": result.get("quote_url", ""), "at": datetime.now(timezone.utc).isoformat(timespec="minutes")})


def email_text(contact: str, business: str, result: dict, signoff: str) -> tuple[str, str]:
    """(subject, body) of the email that sends a client their quote link."""
    first = contact.split()[0] if contact else ""
    total = f"£{(result.get('total_pence') or 0) / 100:,.0f}"
    body = (
        f"Hi {first or 'there'},\n\n"
        f"Thanks for getting back to me. As promised, here's the quote for {business}'s new website ({total}):\n\n"
        f"{result['quote_url']}\n\n"
        "You can read it, and accept it, from that link. Any questions at all, just reply or give me a ring.\n\n"
        f"Kind regards,\n{signoff}"
    )
    subject = f"Your website quote - {business}" + (f" ({result['quote_number']})" if result.get("quote_number") else "")
    return subject, body


def email_link(to: str, contact: str, business: str, result: dict, signoff: str) -> str:
    """A mailto: that opens the same email in your own mail app - the fallback to sending it from the panel."""
    subject, body = email_text(contact, business, result, signoff)
    return f"mailto:{urllib.parse.quote(to or '')}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"


def find_sent(outreach: Path, key: str, quote_number: str) -> dict | None:
    """The quote as recorded when it was made - the link is taken from here, never from the page."""
    path = outreach / "quotes-sent.csv"
    if not path.exists() or not quote_number:
        return None
    with path.open(encoding="utf-8") as f:
        return next((r for r in csv.DictReader(f) if r.get("key") == key and r.get("quote_number") == quote_number), None)
