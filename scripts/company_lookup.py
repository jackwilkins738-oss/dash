"""Look up a prospect's company type on Companies House, for the email-or-letter rule.

Used by push_prospects.py --lookup-companies. The sheet's "Company type"
decides the channel: limited companies and LLPs can get a cold email,
sole traders and ordinary partnerships only a letter (PECR). This fills
that column's blanks from the official register (free API key:
https://developer.company-information.service.gov.uk/).

Ways to match, most certain first:
  1. The prospect's own site shows a company number (homepage, or its
     contact / about / privacy / terms pages). UK company websites must,
     so this is the usual case. The company it points to must also share
     a name with the firm, so a Gas Safe or NICEIC number that happens to
     look like one can't match the firm to a stranger.
  2. A name search on the register. Only trusted when the name matches
     exactly (ignoring "Ltd", "&"/"and", punctuation) and one of:
       - a postcode on their homepage is the company's registered postcode
         (this also picks between several same-name companies);
       - it's the only live exact match, and the firm calls itself Ltd -
         in the sheet or on its own homepage ("(c) 2024 Smith Roofing Ltd").
         A sole trader can't legally do that;
       - it's the only live exact match and its registered office is
         local to the firm: the same postcode district as one on their
         site (both GU1 ...), or a town their site names;
       - it's the only live exact match and its registered address
         mentions the prospect's area.
     A plain "Elite Roofing" with none of these could be a sole trader who
     happens to share a name with a company 200 miles away.
  3. The homepage names a different company as the business behind it
     ("(c) 2024 J Smith Building Services Ltd", "a trading name of ...") -
     the usual case for a trading name. That name is looked up instead.

When in doubt it answers "unsure", which is treated as a letter - the
safe side of PECR. Nothing found at all is "no record": also a letter.
"""

from __future__ import annotations

import base64
import html as htmllib
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.company-information.service.gov.uk"
# Bump when matching improves: saved "unsure" / "no record" answers from an older version are looked up again.
LOGIC_VERSION = "3"
USER_AGENT = "ScalarDigitalProspectCheck/1.0 (+https://www.scalardigital.co.uk)"

# Companies House types that are corporate bodies: cold email allowed.
CORPORATE_TYPES = {
    "ltd": "Ltd",
    "private-limited-guarant-nsc": "Ltd",
    "private-limited-guarant-nsc-limited-exemption": "Ltd",
    "private-limited-shares-section-30-exemption": "Ltd",
    "private-unlimited": "Unlimited company",
    "private-unlimited-nsc": "Unlimited company",
    "plc": "PLC",
    "old-public-company": "PLC",
    "llp": "LLP",
}
# Anything else (limited partnerships, charities, overseas entities ...) is
# left to the owner: "unsure", so a letter.

CLOSED_STATUSES = {"dissolved", "liquidation", "converted-closed", "closed", "removed", "insolvency-proceedings"}

SUFFIX_WORDS = {"ltd", "limited", "llp", "plc", "the", "uk", "co", "company"}
CORPORATE_IN_NAME = re.compile(r"\b(ltd|limited|llp|plc)\b\.?", re.I)

# "Company No. 01234567", "Registered in England No: 1234567", "Company number SC123456" ...
NUMBER_ON_SITE = re.compile(
    r"(?:company|registration|registered|reg\.?)\s*(?:no|number|num|nr)?\.?\s*[:#.]?\s*"
    r"(?:in\s+(?:england(?:\s*(?:&|and)\s*wales)?|wales|scotland|northern\s+ireland)\s*"
    r"(?:no|number)?\.?\s*[:#.]?\s*)?"
    r"\b((?:SC|NI|OC|SO|NC|R0)?\d{6,8})\b",
    re.I,
)


def normalise(name: str) -> str:
    s = name.lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(w for w in s.split() if w not in SUFFIX_WORDS)


# Trade bodies and tax numbers whose "registration no." isn't a company number.
NOT_A_COMPANY = re.compile(r"gas\s*safe|niceic|napit|fensa|certass|oftec|hetas|trustmark|chas\b|vat|ico\b|fca\b|charity|waste|carrier|licen[cs]e", re.I)


def company_number_on_site(page_html: str) -> str | None:
    """The company number the site shows, padded to 8 characters, or None."""
    text = htmllib.unescape(re.sub(r"<[^>]+>", " ", page_html)).replace("\xa0", " ")
    numbers = {
        m.group(1).upper()
        for m in NUMBER_ON_SITE.finditer(text)
        # The words just before it, back to any earlier number: "Gas Safe Reg 123456, Company No. 0765..."
        if not NOT_A_COMPANY.search(re.split(r"\d", text[max(0, m.start() - 40) : m.start()])[-1] + text[m.start() : m.start() + 12])
    }
    if len(numbers) != 1:
        return None  # none, or several (a group of companies) - don't guess
    number = numbers.pop()
    prefix = re.match(r"[A-Z]*", number).group(0)
    return prefix + number[len(prefix) :].zfill(8 - len(prefix))


def site_text(page_html: str) -> str:
    """The words a visitor sees: no scripts, styles or tags."""
    text = re.sub(r"<(script|style|noscript)\b.*?</\1>", " ", page_html, flags=re.I | re.S)
    text = htmllib.unescape(re.sub(r"<[^>]+>", " ", text)).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text)


POSTCODE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?) ?(\d[A-Z]{2})\b")


def postcodes(text: str) -> set[str]:
    return {a + b for a, b in POSTCODE.findall(text.upper())}


def registered_postcode(item: dict) -> str:
    pc = (item.get("address") or {}).get("postal_code") or ""
    if not pc:
        found = POSTCODE.findall((item.get("address_snippet") or "").upper())
        pc = "".join(found[-1]) if found else ""
    return pc.replace(" ", "").upper()


# "Smith Roofing Ltd": up to 7 capitalised words before Ltd/Limited/LLP.
LTD_NAME = re.compile(r"((?:[A-Z0-9][\w'&.\-]*\s+){0,6}[A-Z0-9][\w'&.\-]*)\s+(?:Ltd|Limited|LLP|L\.L\.P)\b\.?")
LEADING_JUNK = {"copyright", "c", "by", "of", "as", "all", "rights", "reserved", "is", "a", "an", "trading", "name", "style",
                "registered", "company", "in", "england", "wales", "and", "scotland", "office", "t", "ta", "t/a"}
# Where a footer says who the business is.
OWNER_CONTEXT = re.compile(r"©|\(c\)|copyright|trading (?:name|style) of|trading as|\bt/a\b|registered (?:in|office|company)", re.I)
# ...and where it credits someone else.
CREDIT = re.compile(r"design|develop|built by|powered|website by|site by|hosting|seo|marketing|digital|media", re.I)


def _clean_name(raw: str) -> str:
    words = raw.split()
    while words and (words[0].lower().strip(".,:") in LEADING_JUNK or re.fullmatch(r"[\d\-–]+", words[0])):
        words.pop(0)
    return " ".join(words)


def names_called_ltd(text: str) -> set[str]:
    """Every "X Ltd" on the page, normalised - to check whether the firm calls itself Ltd."""
    return {normalise(_clean_name(m.group(1))) for m in LTD_NAME.finditer(text)} - {""}


USEFUL_PAGE = re.compile(r"contact|about|privacy|terms|legal|cookie|imprint|company", re.I)


def useful_links(page_html: str, base_url: str, limit: int = 4) -> list[str]:
    """Same-site pages likely to carry the company details: contact, about, privacy, terms."""
    base = urllib.parse.urlparse(base_url)
    found: list[str] = []
    for href in re.findall(r"<a\b[^>]*\bhref\s*=\s*[\"']([^\"'#]+)", page_html, re.I):
        url = urllib.parse.urljoin(base_url, href.strip())
        parts = urllib.parse.urlparse(url)
        same_site = parts.hostname and base.hostname and parts.hostname.removeprefix("www.") == base.hostname.removeprefix("www.")
        if parts.scheme in ("http", "https") and same_site and USEFUL_PAGE.search(parts.path) and url not in found:
            if not re.search(r"\.(pdf|jpe?g|png|gif|webp|svg|zip|docx?)$", parts.path, re.I):
                found.append(url)
    return found[:limit]


def owner_names(text: str) -> list[str]:
    """Company names the footer gives as the business itself, e.g. "(c) 2024 J Smith Building Services Ltd"."""
    found: list[str] = []
    for ctx in OWNER_CONTEXT.finditer(text):
        window = text[ctx.end() : ctx.end() + 140]
        m = LTD_NAME.search(window)
        if not m or CREDIT.search(window[: m.end()]):
            continue
        name = _clean_name(m.group(1))
        if name and normalise(name) and name not in found:
            found.append(name)
    return found[:3]


# Words too common in trade names to show two names are the same firm.
GENERIC_WORDS = {
    "and", "roofing", "roofers", "roof", "building", "builders", "build", "services", "construction", "contractors",
    "group", "home", "homes", "property", "properties", "solutions", "uk", "london", "surrey", "kent", "sussex",
    "landscaping", "landscapes", "gardens", "driveways", "paving", "scaffolding", "plumbing", "heating", "electrical",
    "lofts", "loft", "conversions", "extensions", "maintenance", "developments", "projects", "south", "north", "east",
    "west", "holdings", "trade", "trades", "brothers", "sons", "son", "family", "local", "specialists",
}


def names_agree(company_name: str, business: str, text: str) -> bool:
    """Whether a register entry plausibly is this firm: a distinctive shared word, or the site calls it by name."""
    reg = normalise(company_name)
    if reg and reg in names_called_ltd(text):
        return True
    words = lambda n: {w for w in normalise(n).split() if len(w) >= 3 and w not in GENERIC_WORDS}
    return bool(words(company_name) & words(business))


def district(postcode: str) -> str:
    """"GU14RR" -> "GU1": the outward code, a few streets to a small town."""
    return postcode[:-3] if len(postcode) >= 5 else ""


def pick_by_name(
    business: str,
    area: str,
    items: list[dict],
    says_ltd: bool = False,
    site_postcodes: set[str] | None = None,
    text: str = "",
) -> tuple[dict | None, str]:
    """The register entry this business is, from a name search - or (None, why not)."""
    want = normalise(business)
    if not want:
        return None, "no name"
    exact = [i for i in items if normalise(i.get("title") or "") == want]
    if not exact:
        return None, "no record"
    live = [i for i in exact if (i.get("company_status") or "") not in CLOSED_STATUSES] or exact
    if site_postcodes:
        same_place = [i for i in live if registered_postcode(i) in site_postcodes]
        if len(same_place) == 1:
            return same_place[0], "name + postcode on their site"
    if len(live) == 1 and CORPORATE_IN_NAME.search(business):
        return live[0], "name (calls itself Ltd)"
    if len(live) == 1 and says_ltd:
        return live[0], "name (their site says Ltd)"
    if len(live) == 1 and site_postcodes and district(registered_postcode(live[0])) in {district(c) for c in site_postcodes}:
        return live[0], "name + registered office in the same postcode district"
    town = ((live[0].get("address") or {}).get("locality") or "").strip() if len(live) == 1 else ""
    if town and len(town) >= 4 and re.search(rf"\b{re.escape(town)}\b", text, re.I):
        return live[0], f"name + registered town ({town}) on their site"
    if len(live) == 1 and area and area.lower() in (live[0].get("address_snippet") or "").lower():
        return live[0], "name + area"
    return None, f"unsure ({len(live)} same-name compan{'y' if len(live) == 1 else 'ies'}, not confirmed)"


KEY_SHAPE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def clean_key(api_key: str) -> str:
    """The key without what copying tends to bring along: quotes, spaces, invisible characters, a 'NAME=' prefix."""
    key = re.sub(r"[\s\u200b-\u200f\u2060\ufeff]", "", api_key or "")
    key = key.split("=", 1)[1] if key.upper().startswith("COMPANIES_HOUSE_API_KEY=") else key
    return key.strip("\"'\u2018\u2019\u201c\u201d")


def key_problem(api_key: str) -> str | None:
    """Why this can't be a Companies House REST key, without repeating the key - or None if it looks right."""
    key = clean_key(api_key)
    if KEY_SHAPE.match(key):
        return None
    return (
        f"the saved COMPANIES_HOUSE_API_KEY doesn't look like one: it's {len(key)} characters, and a REST key is 36, "
        "like 1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d. On developer.company-information.service.gov.uk open your "
        "application and copy the key listed under its keys (not the application ID), then save it in Settings again"
    )


class LookupFailed(Exception):
    """Companies House couldn't be asked. The message says why, in plain words."""


def _get(path: str, api_key: str) -> dict:
    """The API's JSON; {} for "not found". Raises PermissionError for a bad key, LookupFailed otherwise."""
    auth = base64.b64encode(f"{clean_key(api_key)}:".encode()).decode()
    req = urllib.request.Request(
        API + path,
        headers={"Authorization": f"Basic {auth}", "Accept": "application/json", "User-Agent": USER_AGENT},
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                return json.loads(res.read())
        except urllib.error.HTTPError as e:
            body = e.read(300).decode("utf-8", errors="replace").strip()
            if e.code == 404:
                return {}
            if e.code == 400 and "authorization" in body.lower():
                raise PermissionError(
                    "Companies House says the key isn't a valid key (400 Invalid Authorization header): "
                    + (key_problem(api_key) or "it has the right shape, so it may be a Stream key or a deleted one - make a new REST key")
                ) from e
            if e.code == 401:
                raise PermissionError(
                    "Companies House rejected the API key (401). Make it a REST key, on an application "
                    "set to Live (not Test), and paste it with nothing else"
                ) from e
            if e.code == 403:
                raise PermissionError(
                    f"Companies House refused the key (403: {body or 'forbidden'}). If you filled in "
                    "'Restricted IPs' on the key, make a new REST key with that left blank"
                ) from e
            if e.code == 429 and attempt < 3:
                time.sleep(60)  # 600 requests per 5 minutes - wait for the window to move on
                continue
            if e.code >= 500 and attempt < 3:
                time.sleep(3)
                continue
            raise LookupFailed(f"HTTP {e.code} {body[:200]}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < 2:
                time.sleep(3)
                continue
            reason = getattr(e, "reason", None) or e
            raise LookupFailed(f"couldn't connect ({reason})") from e
        except ValueError as e:
            raise LookupFailed("got something that wasn't JSON back") from e
    raise LookupFailed("still rate-limited after 3 minutes")


def result_for(entry: dict, how: str) -> dict:
    ch_type = entry.get("company_type") or entry.get("type") or ""
    status = entry.get("company_status") or ""
    if status in CLOSED_STATUSES:
        result, label = "closed", ""
    elif ch_type in CORPORATE_TYPES:
        result, label = "company", CORPORATE_TYPES[ch_type]
    else:
        result, label = "unsure", ""
    return {
        "result": result,
        "company_type": label,
        "number": entry.get("company_number") or "",
        "registered_name": entry.get("company_name") or entry.get("title") or "",
        "status": status,
        "how": f"{how}; type {ch_type}" if result == "unsure" else how,
    }


def lookup(business: str, area: str, page_html: str | None, api_key: str) -> dict:
    """What the register says about this business. Raises LookupFailed / PermissionError if it can't ask."""
    text = site_text(page_html) if page_html else ""
    if page_html:
        number = company_number_on_site(page_html)
        if number:
            entry = _get(f"/company/{number}", api_key)
            if entry and names_agree(entry.get("company_name") or "", business, text):
                return result_for(entry, "number on their site")
    codes = postcodes(text)
    says_ltd = normalise(business) in names_called_ltd(text)

    def search(name: str) -> list[dict]:
        return _get("/search/companies?" + urllib.parse.urlencode({"q": name, "items_per_page": 20}), api_key).get("items") or []

    entry, how = pick_by_name(business, area, search(business), says_ltd, codes, text)
    if entry:
        return result_for(entry, how)
    # A trading name: the footer says which company is behind it.
    for name in owner_names(text):
        if normalise(name) == normalise(business):
            continue
        owner, _ = pick_by_name(name + " Ltd", area, search(name), True, codes, text)
        if owner:
            return result_for(owner, f"company named on their site: {name} Ltd")
    none = how == "no record"
    return {
        "result": "none" if none else "unsure",
        "company_type": "",
        "number": "",
        "registered_name": "",
        "status": "",
        "how": how,
    }
