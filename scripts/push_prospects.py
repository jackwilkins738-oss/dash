"""Push outreach prospects into the dashboard, and write each one's preview link.

Reads the outreach sheet (outreach/outreach-master.xlsx, which is gitignored and
never leaves this machine), sends only public business facts to the dashboard's
/api/prospects/import route, and writes outreach/preview-links.csv with the
private preview URL for every prospect - ready to merge into Mailmeteor as
{{preview_url}} or print on a letter as a QR code.

Nothing personal is sent: no emails, phone numbers or contact names. Those
stay in the sheet and in the CSV this writes, both on this machine only.

Usage (PowerShell):
    $env:PROSPECTS_API_SECRET = "<same value as in Vercel>"
    python scripts/push_prospects.py --dry-run     # check the CSV first
    python scripts/push_prospects.py               # push for real

Options:
    --sheet PATH     outreach workbook (default: outreach/outreach-master.xlsx in this
                     checkout, or in the main checkout when run from a worktree)
    --out PATH       where to write the links CSV (default: preview-links.csv beside the
                     master sheet, preview-links-<sheet name>.csv beside any other sheet)
Outputs, beside the sheet:
    preview-links[-<sheet>].csv   every prospect and their preview link
    mailmeteor[-<sheet>].csv      ready to import into Mailmeteor: email-channel prospects
                                  only (no sole traders, no bad emails), with business,
                                  greeting_name, email, mobile_score, lcp_s, preview_url
    --dry-run        write the CSV, send nothing
    --only TEXT      only prospects whose business name or website contains TEXT
    --limit N        only the first N prospects (after --only)
    --teardown       also run the automated website teardown (site_teardown.py) and
                     push its findings - off by default. Takes ~20-60s per site, so it
                     refuses to run on more than 10 prospects unless --yes-all is given.
    --yes-all        allow --teardown on more than 10 prospects
    --retry-failed   with --teardown: only the sites that couldn't be checked last time.
    --recheck        with --teardown: include sites already checked. Without it, sites
                     listed in outreach/teardown-log.csv are skipped, so repeated
                     `--teardown --limit 10` runs work through the list 10 at a time.
    --guess-trades   for prospects with no Trade in the sheet, read their homepage's title,
                     description and headings and guess one (trade_guess.py). Guesses are
                     kept in outreach/trade-guesses.csv and reused on every later run, so a
                     normal re-run never blanks them. Your sheet is never changed.
    --find-contacts  for firms with a blank Email, Phone or Contact name: read their own site's
                     published email and phone, and take the contact name from their directors
                     on Companies House (when the company lookup confirmed their number). Kept in
                     outreach/contacts-found.csv and reused; the sheet always wins. --recheck redoes.
    --letters        write letters-<sheet>.html: a print-ready A4 letter for every letter-channel
                     firm (and a finder sheet's No website tab), each with a QR code to their
                     preview page. Skips firms already posted one (--letters-all includes them).
                     Needs: python -m pip install segno
    --check-emails   check every email address can receive mail (email_check.py): typo'd,
                     dead or mail-less domains. Bad ones go by letter instead. Results are
                     kept in outreach/email-checks.csv and reused; rechecked after 30 days.
    --lookup-companies
                     for prospects with no Company type in the sheet, look it up on Companies
                     House (company_lookup.py) - this decides email or letter. Kept in
                     outreach/company-lookups.csv and reused (--recheck looks again). Firms
                     the register shows as dissolved or in liquidation are left out.
Never contacted twice, never after a no (contact_rules.py):
    Anyone whose Status in ANY sheet says not interested / unsubscribed, or who
    is in outreach/do-not-contact.csv, is left out of every list. A firm already
    in another sheet (outreach/claims.csv: the first sheet that listed it) is
    left out of this one - no second preview page, no second email.
Env:
    PROSPECTS_API_SECRET  required (also used to make the links unguessable)
    DASHBOARD_API_URL     default https://admin.scalardigital.co.uk
    SCALAR_TENANT_ID      default Scalar Digital's own tenant (already public in
                          the site's track.js snippet)
    SITE_URL              default https://www.scalardigital.co.uk
    PAGESPEED_API_KEY     required for --teardown (the same Google key the site's
                          speed test uses, NEXT_PUBLIC_PAGESPEED_API_KEY in Vercel)
    COMPANIES_HOUSE_API_KEY  required for --lookup-companies (free, from
                          https://developer.company-information.service.gov.uk/)

Try the teardown on one firm first, and check its preview page, before anything else:
    python scripts/push_prospects.py --teardown --only "Smith Roofing" --dry-run
    python scripts/push_prospects.py --teardown --only "Smith Roofing"
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import hmac
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

try:
    import openpyxl
except ImportError:
    sys.exit("Needs openpyxl: python -m pip install openpyxl")

DEFAULT_TENANT = "abdc6408-1fd5-4fb6-9c4c-53600b571a6d"
SKIP_STATUSES = {"Removed - parked / unsuitable", "Lost / not interested"}
LETTER_COMPANY_TYPES = {"sole trader", "partnership", "none", "no record", "unsure"}
EMAIL_RECHECK_DAYS = 30
TEARDOWN_WORKERS = 4


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)[:50].strip("-") or "firm"


def domain_of(website: str) -> str | None:
    raw = (website or "").strip()
    if not raw:
        return None
    url = urlparse(raw if re.match(r"^https?://", raw, re.I) else f"https://{raw}")
    host = (url.hostname or "").lower()
    if "." not in host:
        return None
    return host[4:] if host.startswith("www.") else host


def make_slug(business: str, key: str, secret: str) -> str:
    # HMAC with the secret: stable across runs (a re-push updates the same
    # page), but impossible to work out from a business name without it.
    tag = hmac.new(secret.encode(), key.encode(), hashlib.sha256).hexdigest()[:6]
    return f"{slugify(business)}-{tag}"


def channel_for(row: dict, company_type: str | None = None, email_bad: bool = False) -> str:
    """email or letter. company_type fills a blank sheet column; email_bad is our own email check."""
    company_type = str(row.get("Company type") or company_type or "").strip().lower()
    email = str(row.get("Email") or "").strip()
    status = str(row.get("Status") or "").lower()
    email_ok = (
        "@" in email
        and not email_bad
        and "invalid" not in str(row.get("Email check") or "").lower()
        and "wrong email" not in status
        and "invalid email" not in status
    )
    if company_type in LETTER_COMPANY_TYPES:
        return "letter"  # PECR: no cold email to sole traders or ordinary partnerships
    return "email" if email_ok else "letter"


ADDRESS_PARTS = ["Address 1", "Address line 1", "Address 2", "Address line 2", "Street", "Town", "City", "County", "Postcode"]


def address_of(row: dict) -> str:
    """A postal address from whatever address columns the sheet has."""
    for col in ("Address", "Postal address", "Registered address"):
        if str(row.get(col) or "").strip():
            return str(row[col]).strip()
    return ", ".join(str(row[c]).strip() for c in ADDRESS_PARTS if str(row.get(c) or "").strip())


def score_line(score) -> str:
    """Google's own bands - the same words the preview page and the letters use."""
    if score is None:
        return ""
    s = int(score)
    band = "good" if s >= 90 else "needing improvement" if s >= 50 else "poor"
    return f"It scored {s} out of 100 on Google's mobile speed test, which Google itself counts as {band}."


def number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def main() -> None:
    here = Path(__file__).resolve().parent
    default_sheet = here.parent / "outreach" / "outreach-master.xlsx"
    if not default_sheet.exists():
        # Running from a git worktree: the sheet lives in the main checkout.
        for parent in here.parents:
            candidate = parent / "outreach" / "outreach-master.xlsx"
            if candidate.exists():
                default_sheet = candidate
                break

    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", type=Path, default=default_sheet)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--teardown", action="store_true")
    ap.add_argument("--yes-all", action="store_true")
    ap.add_argument("--guess-trades", action="store_true")
    ap.add_argument("--recheck", action="store_true")
    ap.add_argument("--retry-failed", action="store_true", help="with --teardown: only the sites that couldn't be checked before")
    ap.add_argument("--find-contacts", action="store_true")
    ap.add_argument("--letters", action="store_true")
    ap.add_argument("--letters-all", action="store_true", help="with --letters: include firms already posted a letter")
    ap.add_argument("--check-emails", action="store_true")
    ap.add_argument("--lookup-companies", action="store_true")
    args = ap.parse_args()

    secret = os.environ.get("PROSPECTS_API_SECRET", "")
    if len(secret) < 32:
        sys.exit("Set PROSPECTS_API_SECRET (32+ characters, same value as in Vercel) first.")
    api = os.environ.get("DASHBOARD_API_URL", "https://admin.scalardigital.co.uk").rstrip("/")
    tenant = os.environ.get("SCALAR_TENANT_ID", DEFAULT_TENANT)
    site = os.environ.get("SITE_URL", "https://www.scalardigital.co.uk").rstrip("/")

    if not args.sheet.exists():
        sys.exit(f"Can't find the sheet at {args.sheet} - pass --sheet PATH")

    import overrides  # same folder as this script

    wb = openpyxl.load_workbook(args.sheet, read_only=True, data_only=True)

    def tab_rows(tab: str) -> list[dict]:
        if tab not in wb.sheetnames:
            return []
        rows = list(wb[tab].iter_rows(values_only=True))
        if not rows:
            return []
        header = [str(h).strip() if h else "" for h in rows[0]]
        return [dict(zip(header, values)) for values in rows[1:]]

    # Decisions from the panel's Review tab, applied without touching the sheet.
    decisions = overrides.load(args.sheet.parent, args.sheet.name)
    sheet_rows, reviewed_out = [], 0
    for row in tab_rows("Outreach"):
        fixed = overrides.apply(row, decisions.get(overrides.row_key(row), {}))
        if fixed is None:
            reviewed_out += 1
        else:
            sheet_rows.append(fixed)
    # A finder sheet's "Check website" rows join once their website is confirmed in Review.
    for row in tab_rows("Check website"):
        d = decisions.get(overrides.row_key(row), {})
        if d.get("website"):
            fixed = overrides.apply(row, d)
            if fixed is not None:
                sheet_rows.append(fixed)
    no_website_rows = tab_rows("No website")  # letters only
    wb.close()

    # ---- this machine's notes: saved results reused on every run ---------
    # Each is keyed on the website (or email domain), filled by an option,
    # and saved even on a dry run. The sheet's own column always wins.
    guesses_path = args.sheet.parent / "trade-guesses.csv"
    lookups_path = args.sheet.parent / "company-lookups.csv"
    emails_path = args.sheet.parent / "email-checks.csv"
    contacts_path = args.sheet.parent / "contacts-found.csv"
    CONTACT_FIELDS = ["website", "email", "phone", "contact", "address", "checked_at"]
    LOOKUP_FIELDS = ["website", "business", "result", "company_type", "number", "registered_name", "status", "how", "checked_at", "logic"]
    EMAIL_FIELDS = ["email", "result", "checked_at"]

    def read_csv(path: Path, key: str) -> dict[str, dict]:
        if not path.exists():
            return {}
        with path.open(encoding="utf-8") as f:
            return {r[key]: r for r in csv.DictReader(f) if r.get(key)}

    def write_csv(path: Path, fields: list[str], rows: dict[str, dict]) -> None:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(r for _, r in sorted(rows.items()))

    guesses: dict[str, str] = {w: r["trade"] for w, r in read_csv(guesses_path, "website").items() if r.get("trade")}
    lookups = read_csv(lookups_path, "website")
    email_checks = read_csv(emails_path, "email")
    contacts_found = read_csv(contacts_path, "website")

    def email_result(email: str) -> str:
        return (email_checks.get(email.strip().lower()) or {}).get("result") or ""

    from contact_rules import Claims, load_blocklist  # same folder as this script

    listed: dict[str, set[str]] = {}
    blocklist = load_blocklist(args.sheet.parent, domain_of, listed)
    claims = Claims(args.sheet.parent, listed)
    left_out: dict[str, list[str]] = {"blocked": [], "elsewhere": []}

    def build() -> tuple[list[dict], int, int]:
        """Prospects from the sheet plus the saved notes: (prospects, skipped, closed)."""
        from email_check import is_bad  # same folder as this script

        out, seen, skipped, closed = [], set(), 0, 0
        left_out["blocked"], left_out["elsewhere"] = [], []
        for row in sheet_rows:
            business = str(row.get("Business") or "").strip()
            domain = domain_of(str(row.get("Website") or ""))
            if not business or not domain or str(row.get("Status") or "") in SKIP_STATUSES:
                skipped += 1
                continue
            why = blocklist.why(domain, str(row.get("Email") or ""), business)
            if why:
                left_out["blocked"].append(f"{business}: {why}")
                continue
            owner = claims.other_owner(domain, args.sheet.name)
            if owner:
                left_out["elsewhere"].append(f"{business}: already in {owner}")
                continue
            slug = make_slug(business, domain, secret)
            if slug in seen:
                skipped += 1
                continue
            seen.add(slug)
            sheet_type = str(row.get("Company type") or "").strip()
            lookup = lookups.get(domain) if not sheet_type else None
            if lookup and lookup.get("result") == "closed":
                closed += 1
                continue
            looked_up_type = None
            if lookup:
                looked_up_type = {"company": lookup.get("company_type"), "none": "no record", "unsure": "unsure"}.get(
                    lookup.get("result") or ""
                )
            # The sheet wins; what --find-contacts found only fills blanks.
            found = contacts_found.get(domain) or {}
            email = str(row.get("Email") or "").strip() or (found.get("email") or "").strip()
            if email and not row.get("Email"):
                row = {**row, "Email": email}
            channel = channel_for(row, looked_up_type, is_bad(email_result(email)) if email else False)
            contact = str(row.get("Contact name") or "").strip() or (found.get("contact") or "").strip()
            out.append(
                {
                    "slug": slug,
                    "business_name": business,
                    # The sheet's own Trade always wins; a saved guess only fills a blank.
                    "trade": row.get("Trade") or guesses.get(domain) or None,
                    "area": row.get("Area") or None,
                    "website": domain,
                    "mobile_score": number(row.get("Mobile score")),
                    "lcp_s": number(row.get("LCP (s)")),
                    "channel": channel,
                    "_sheet_trade": bool(row.get("Trade")),
                    "_sheet_type": bool(sheet_type),
                    "_email": email,
                    "_status": row.get("Status") or "",
                    "_greeting": contact.split()[0] if contact else "there",
                    "_contact": contact,
                    "_key": overrides.row_key(row),
                    "_address": address_of(row) or (found.get("address") or "").strip(),
                    "_phone": str(row.get("Phone") or "").strip() or (found.get("phone") or "").strip(),
                }
            )
        return out, skipped, closed

    prospects, skipped, closed = build()
    # This sheet now owns every firm it lists that no other sheet had first.
    claims.claim([p["website"] for p in prospects], args.sheet.name)

    # One set of output files per sheet, so running a second list (e.g. the
    # loft-conversions workbook) never overwrites the master list's links.
    suffix = "" if args.sheet.stem == "outreach-master" else f"-{args.sheet.stem}"
    out = args.out or args.sheet.parent / f"preview-links{suffix}.csv"

    # ---- teardown log: what's been checked, and the scores it found ------
    # Columns: website, checked_at, result (ok|failed), mobile_score, lcp_s.
    # The scores are kept here because a new list's sheet has none: without
    # them every export would blank earlier batches' scores, and every plain
    # push would overwrite the dashboard's copy with nothing.
    log_path = args.sheet.parent / "teardown-log.csv"
    log: dict[str, dict] = {}
    if log_path.exists():
        with log_path.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                log[r["website"]] = {
                    "checked_at": r.get("checked_at") or "",
                    "result": r.get("result") or "ok",
                    "mobile_score": number(r.get("mobile_score")),
                    "lcp_s": number(r.get("lcp_s")),
                    # None = not known yet (checked before this column existed); "" = nothing found.
                    "top_issue": r.get("top_issue") if "top_issue" in r and r.get("top_issue") != "?" else None,
                    "issue_count": r.get("issue_count") or "",
                }

    def save_log() -> None:
        with log_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=["website", "checked_at", "result", "mobile_score", "lcp_s", "top_issue", "issue_count"]
            )
            writer.writeheader()
            for w, e in sorted(log.items()):
                writer.writerow(
                    {
                        "website": w,
                        "checked_at": e["checked_at"],
                        "result": e["result"],
                        "mobile_score": "" if e["mobile_score"] is None else int(e["mobile_score"]),
                        "lcp_s": "" if e["lcp_s"] is None else e["lcp_s"],
                        "top_issue": "?" if e.get("top_issue") is None else e["top_issue"],
                        "issue_count": e.get("issue_count", ""),
                    }
                )

    def note_findings(entry: dict, teardown: dict | None, checked_at: str | None) -> None:
        from findings import all_issues

        year = int((checked_at or datetime.now(timezone.utc).isoformat())[:4])
        issues = all_issues(teardown, year)
        entry["top_issue"] = issues[0] if issues else ""
        entry["issue_count"] = len(issues)

    def fill_scores() -> None:
        # Fill blanks from the log; for sites checked before the log kept
        # scores (or findings), fetch them once from the dashboard's record.
        fetched = 0
        for p in prospects:
            entry = log.get(p["website"])
            if not entry or entry["result"] != "ok":
                continue
            need_score = p.get("mobile_score") is None and entry["mobile_score"] is None
            if need_score or entry.get("top_issue") is None:
                try:
                    req = urllib.request.Request(
                        f"{api}/api/prospects/{p['slug']}", headers={"Authorization": f"Bearer {secret}"}
                    )
                    with urllib.request.urlopen(req, timeout=20) as res:
                        row = json.loads(res.read()).get("prospect") or {}
                    if entry["mobile_score"] is None:
                        entry["mobile_score"], entry["lcp_s"] = row.get("mobile_score"), row.get("lcp_s")
                    if entry.get("top_issue") is None:
                        # No saved teardown on the dashboard either: "" so it's never asked again.
                        note_findings(entry, row.get("teardown"), row.get("teardown_at"))
                    fetched += 1
                except (urllib.error.URLError, TimeoutError, OSError, ValueError):
                    pass
            p["_top_issue"] = entry.get("top_issue") or ""
            if p.get("mobile_score") is None:
                p["mobile_score"] = entry["mobile_score"]
            if p.get("lcp_s") is None:
                p["lcp_s"] = entry["lcp_s"]
        if fetched:
            save_log()
            print(f"Recovered {fetched} scores / findings from the dashboard into {log_path.name}")

    fill_scores()

    def write_outputs() -> None:
        with out.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["Business", "Email", "Channel", "Status", "preview_url"])
            writer.writeheader()
            for p in prospects:
                writer.writerow(
                    {
                        "Business": p["business_name"],
                        "Email": p["_email"],
                        "Channel": p["channel"],
                        "Status": p["_status"],
                        "preview_url": preview_url(p),
                    }
                )
        mm = out.parent / f"mailmeteor{suffix}.csv"
        with mm.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "business", "greeting_name", "email", "mobile_score", "lcp_s", "preview_url", "status",
                    "trade", "area", "top_issue", "score_line", "issue_line",
                ],
            )
            writer.writeheader()
            for p in prospects:
                if p["channel"] != "email":
                    continue
                score = p.get("mobile_score")
                writer.writerow(
                    {
                        "business": p["business_name"],
                        "greeting_name": p["_greeting"],
                        "email": p["_email"],
                        "mobile_score": "" if score is None else int(score),
                        "lcp_s": "" if p.get("lcp_s") is None else p["lcp_s"],
                        "preview_url": preview_url(p),
                        "status": p["_status"],
                        "trade": (p.get("trade") or "").lower(),
                        "area": p.get("area") or "",
                        "top_issue": p.get("_top_issue") or "",
                        # Whole sentences, empty when the fact isn't known - so an email template
                        # using {{score_line}} {{issue_line}} never reads "...and noticed ."
                        "score_line": score_line(score),
                        "issue_line": f"I also noticed {p['_top_issue']}." if p.get("_top_issue") else "",
                    }
                )
        print(f"Wrote {out.name} and {mm.name}")

    def make_letters() -> None:
        try:
            import letters
        except ImportError:
            sys.exit("Letters need one extra piece: python -m pip install segno  (the panel has an Install button).")
        try:
            import segno  # noqa: F401
        except ImportError:
            sys.exit("Letters need one extra piece: python -m pip install segno  (the panel has an Install button).")
        from company_lookup import LookupFailed, _get

        outreach = args.sheet.parent
        sent = read_csv(outreach / "letters-sent.csv", "key")
        with_site_t, no_site_t = letters.load_templates(outreach)
        sender = {
            "name": os.environ.get("LETTER_SIGNOFF", "") or "Scalar Digital",
            "email": os.environ.get("LETTER_EMAIL", "") or "hello@scalardigital.co.uk",
            "phone": os.environ.get("LETTER_PHONE", "") or "07401 696272",
            "site": site.removeprefix("https://").removeprefix("http://"),
        }
        ch_key = os.environ.get("COMPANIES_HOUSE_API_KEY", "")

        def registered_office(p_website: str) -> str:
            found = lookups.get(p_website) or {}
            if not (ch_key and found.get("number") and found.get("result") == "company"):
                return ""
            try:
                office = _get(f"/company/{found['number']}", ch_key).get("registered_office_address") or {}
            except (LookupFailed, PermissionError):
                return ""
            return ", ".join(str(office[k]).strip() for k in ("address_line_1", "address_line_2", "locality", "region", "postal_code") if office.get(k))

        def values(business: str, contact: str, website: str, trade: str, area: str, score, issue: str) -> dict:
            return {
                "greeting": contact.split()[0] if contact else "Sir or Madam",
                "business": business, "website": website, "area": area,
                "score_sentence": letters.score_sentence(score),
                "issue_sentence": f"I also noticed {issue}." if issue else "",
                "trade_plural": letters.TRADE_PLURALS.get((trade or "").lower(), "trade businesses"),
                "sender_email": sender["email"], "sender_phone": sender["phone"], "signoff": sender["name"],
            }

        batch, no_address, already = [], [], 0
        for p in prospects:
            if p["channel"] != "letter":
                continue
            if p["_key"] in sent and not args.letters_all:
                already += 1
                continue
            address = p["_address"]
            if not address:
                address = registered_office(p["website"])
                if address:
                    contacts_found.setdefault(p["website"], {"website": p["website"]})["address"] = address
            if not address:
                no_address.append(p["business_name"])
                continue
            url = f"{site}/for/{p['slug']}?src=letter"
            body = letters.fill(with_site_t, values(p["business_name"], p["_contact"], p["website"], p.get("trade") or "",
                                                    p.get("area") or "", p.get("mobile_score"), p.get("_top_issue") or ""))
            batch.append({"key": p["_key"], "business": p["business_name"], "contact": p["_contact"], "address": address,
                          "url": url, "short_url": url.split("://", 1)[-1].split("?")[0], "body": body})
        # A finder sheet's No website tab: no preview page, so the code goes to the website itself.
        for row in no_website_rows:
            d = decisions.get(overrides.row_key(row), {})
            fixed = overrides.apply(row, d)
            business = str(row.get("Business") or "").strip()
            if fixed is None or not business or str(row.get("Status") or "") in SKIP_STATUSES:
                continue
            if blocklist.why(None, str(row.get("Email") or ""), business):
                continue
            key = overrides.row_key(row)
            if key in sent and not args.letters_all:
                already += 1
                continue
            address = address_of(row)
            if not address:
                no_address.append(business)
                continue
            url = f"{site}/?src=letter"
            contact = str(row.get("Contact name") or "").strip()
            body = letters.fill(no_site_t, values(business, contact, "", str(row.get("Trade") or ""), str(row.get("Area") or ""), None, ""))
            batch.append({"key": key, "business": business, "contact": contact, "address": address,
                          "url": url, "short_url": url.split("://", 1)[-1].split("?")[0], "body": body})

        if contacts_found:
            write_csv(contacts_path, CONTACT_FIELDS, contacts_found)
        batch.sort(key=lambda l: l["business"].lower())
        page = outreach / f"letters-{args.sheet.stem}.html"
        batch_file = outreach / f"letters-batch-{args.sheet.stem}.csv"
        if not batch:
            print(f"No letters to make ({already} already posted, {len(no_address)} with no address).")
            return
        for l in batch:
            l["qr"] = letters.qr_svg(l["url"])
        page.write_text(letters.render(batch, sender), encoding="utf-8")
        with batch_file.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["key", "business", "sheet"])
            writer.writeheader()
            writer.writerows({"key": l["key"], "business": l["business"], "sheet": args.sheet.name} for l in batch)
        print(f"Wrote {page.name}: {len(batch)} letter{'s' if len(batch) != 1 else ''} ready to print.")
        if already:
            print(f"  {already} left out - already posted a letter (tick 'Include firms already sent one' to redo)")
        if no_address:
            print(f"  {len(no_address)} have no postal address, so no letter: " + ", ".join(no_address[:8]) + (" ..." if len(no_address) > 8 else ""))
        if args.dry_run:
            print("  Dry run: nothing pushed, so new firms' preview pages may not exist yet - run it without Dry run before posting.")

    def preview_url(p: dict) -> str:
        src = "email" if p["channel"] == "email" else "letter"
        return f"{site}/for/{p['slug']}?src={src}"

    def report() -> None:
        by_channel = {c: sum(1 for p in prospects if p["channel"] == c) for c in ("email", "letter")}
        gone = f", {closed} left out (dissolved / in liquidation)" if closed else ""
        gone += f", {reviewed_out} left out in Review" if reviewed_out else ""
        print(f"{len(prospects)} prospects ({by_channel['email']} email, {by_channel['letter']} letter), {skipped} skipped{gone}")
        if left_out["blocked"]:
            print(f"{len(left_out['blocked'])} left out - they said no (do-not-contact):")
            for line in left_out["blocked"][:10]:
                print(f"    {line}")
        if left_out["elsewhere"]:
            print(f"{len(left_out['elsewhere'])} left out - already in another list:")
            for line in left_out["elsewhere"][:10]:
                print(f"    {line}")

    write_outputs()
    report()

    # --only / --limit narrow what gets checked and pushed. The links CSV
    # above always covers everyone, so it never loses rows.
    selected = prospects
    if args.teardown and args.retry_failed:
        selected = [p for p in selected if log.get(p["website"], {}).get("result") == "failed"]
        print(f"Retrying {len(selected)} sites that couldn't be checked before")
    elif args.teardown and not args.recheck and not args.only:
        before = len(selected)
        # Failed sites are skipped too - otherwise every batch would retry
        # the same unreachable sites and never move on.
        selected = [p for p in selected if p["website"] not in log]
        if before != len(selected):
            failed = sum(1 for p in prospects if log.get(p["website"], {}).get("result") == "failed")
            print(
                f"Skipping {before - len(selected)} already checked ({failed} of them couldn't be checked; "
                f"--recheck to try everything again)"
            )
    if args.only:
        needle = args.only.lower()
        selected = [p for p in selected if needle in p["business_name"].lower() or needle in p["website"]]
    if args.limit is not None:
        selected = selected[: max(0, args.limit)]
    if args.only or args.limit is not None:
        print(f"Selected {len(selected)}: " + ", ".join(p["business_name"] for p in selected[:10]) + (" ..." if len(selected) > 10 else ""))
    if not selected:
        sys.exit("Nothing selected.")

    homepages: dict[str, tuple[str | None, str | None]] = {}

    def fetch_homepage(domain: str) -> tuple[str | None, str | None]:
        """The prospect's homepage HTML and where it ended up, fetched once per run."""
        from site_teardown import fetch_html  # same folder as this script

        if domain not in homepages:
            html, final = fetch_html(f"https://{domain}/")
            if html is None:
                html, final = fetch_html(f"http://{domain}/")
            homepages[domain] = (html, final)
        return homepages[domain]

    def homepage(domain: str) -> str | None:
        return fetch_homepage(domain)[0]

    def company_pages(domain: str) -> str | None:
        """Homepage plus its contact / about / privacy / terms pages - where company details usually sit."""
        from company_lookup import useful_links
        from site_teardown import fetch_html

        html, final = fetch_homepage(domain)
        if html is None:
            return None
        pages = [html]
        for url in useful_links(html, final or f"https://{domain}/"):
            extra, _ = fetch_html(url, timeout=15)
            if extra:
                pages.append(extra)
        return "\n".join(pages)

    if args.lookup_companies:
        ch_key = os.environ.get("COMPANIES_HOUSE_API_KEY", "")
        if not ch_key:
            sys.exit("--lookup-companies needs COMPANIES_HOUSE_API_KEY (free: developer.company-information.service.gov.uk).")
        from company_lookup import LOGIC_VERSION, LookupFailed, key_problem, lookup

        problem = key_problem(ch_key)
        if problem:
            sys.exit(f"Can't look up companies: {problem}.")

        def needs_lookup(p: dict) -> bool:
            saved = lookups.get(p["website"])
            if args.recheck or not saved:
                return True
            if (saved.get("logic") or "1") == LOGIC_VERSION:
                return False
            # Matching has improved since this answer: try the unsure / not-found ones again, and
            # re-confirm company numbers (an older version could take a Gas Safe number for one).
            return saved.get("result") in ("unsure", "none") or saved.get("how") == "number on their site"

        todo = [p for p in selected if not p["_sheet_type"] and needs_lookup(p)]
        print(f"Looking up {len(todo)} firms with no Company type in the sheet on Companies House ...")
        counts: dict[str, int] = {}
        failures_in_a_row = 0
        for i, p in enumerate(todo, 1):
            try:
                found = lookup(p["business_name"], p.get("area") or "", company_pages(p["website"]), ch_key)
            except PermissionError as e:
                write_csv(lookups_path, LOOKUP_FIELDS, lookups)
                sys.exit(f"{e}.")
            except LookupFailed as e:
                print(f"    {p['business_name']}: Companies House didn't answer - {e}")
                failures_in_a_row += 1
                if failures_in_a_row >= 3:
                    write_csv(lookups_path, LOOKUP_FIELDS, lookups)
                    sys.exit(f"Stopped: Companies House failed 3 times in a row ({e}). Nothing is lost - run it again later.")
                continue
            failures_in_a_row = 0
            lookups[p["website"]] = {
                "website": p["website"],
                "business": p["business_name"],
                **found,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "logic": LOGIC_VERSION,
            }
            counts[found["result"]] = counts.get(found["result"], 0) + 1
            label = found["company_type"] or {"none": "no record -> letter", "unsure": "unsure -> letter", "closed": f"{found['status']} -> left out"}[found["result"]]
            print(f"    [{i}/{len(todo)}] {p['business_name']}: {label}  ({found['how']})")
            if i % 25 == 0:
                write_csv(lookups_path, LOOKUP_FIELDS, lookups)
        write_csv(lookups_path, LOOKUP_FIELDS, lookups)
        print(
            f"{counts.get('company', 0)} companies, {counts.get('none', 0)} not on the register, "
            f"{counts.get('unsure', 0)} unsure (letter - put the real type in the sheet if you know it), "
            f"{counts.get('closed', 0)} dissolved. Saved to {lookups_path.name}"
        )

    if args.find_contacts:
        from concurrent.futures import ThreadPoolExecutor

        from find_prospects import find_email, find_phone, pick_director

        ch_key = os.environ.get("COMPANIES_HOUSE_API_KEY", "")
        todo = [
            p for p in selected
            if not (p["_email"] and p["_contact"] and p["_phone"]) and (args.recheck or p["website"] not in contacts_found)
        ]
        print(f"Looking for missing emails, phones and contact names for {len(todo)} firms ...")

        def contacts_for(p: dict) -> dict:
            pages = company_pages(p["website"]) or ""
            email = find_email(pages, p["website"]) if pages else ""
            phone = find_phone(pages) if pages else ""
            contact = ""
            number = (lookups.get(p["website"]) or {}).get("number") or ""
            confirmed = (lookups.get(p["website"]) or {}).get("result") == "company"
            if ch_key and number and confirmed:
                from company_lookup import LookupFailed, _get

                try:
                    contact, _ = pick_director(_get(f"/company/{number}/officers?items_per_page=50", ch_key))
                except (LookupFailed, PermissionError):
                    pass
            return {"website": p["website"], "email": email, "phone": phone, "contact": contact,
                    "checked_at": datetime.now(timezone.utc).isoformat()}

        added = {"email": 0, "phone": 0, "contact": 0}
        with ThreadPoolExecutor(max_workers=6) as pool:
            for i, (p, found) in enumerate(zip(todo, pool.map(contacts_for, todo)), 1):
                contacts_found[p["website"]] = found
                new = []
                if found["email"] and not p["_email"]:
                    p["_email"] = found["email"]
                    added["email"] += 1
                    new.append(found["email"])
                if found["phone"] and not p["_phone"]:
                    added["phone"] += 1
                    new.append(found["phone"])
                if found["contact"] and not p["_contact"]:
                    added["contact"] += 1
                    new.append(found["contact"])
                print(f"    [{i}/{len(todo)}] {p['business_name']}: {' · '.join(new) or 'nothing new found'}", flush=True)
                if i % 25 == 0:
                    write_csv(contacts_path, CONTACT_FIELDS, contacts_found)
        write_csv(contacts_path, CONTACT_FIELDS, contacts_found)
        print(
            f"Found {added['email']} emails, {added['phone']} phone numbers and {added['contact']} contact names. "
            f"Saved to {contacts_path.name} - your sheet is unchanged."
        )

    if args.check_emails:
        from email_check import check, is_bad

        now = datetime.now(timezone.utc)
        domain_cache: dict[str, str] = {}
        todo = []
        for p in selected:
            email = p["_email"].strip().lower()
            if not email or "@" not in email:
                continue
            saved = email_checks.get(email)
            if saved and not args.recheck:
                try:
                    age = now - datetime.fromisoformat(saved.get("checked_at") or "")
                    if age.days < EMAIL_RECHECK_DAYS:
                        continue
                except ValueError:
                    pass
            todo.append((p, email))
        print(f"Checking {len(todo)} email addresses ...")
        bad = 0
        for p, email in todo:
            result = check(email, domain_cache)
            if result == "unknown":
                print(f"    {email}: couldn't check just now - left as it was")
                continue
            email_checks[email] = {"email": email, "result": result, "checked_at": now.isoformat()}
            if is_bad(result):
                bad += 1
                print(f"    {p['business_name']}: {email} - {result}")
        write_csv(emails_path, EMAIL_FIELDS, email_checks)
        print(f"{bad} won't take mail - they'll go by letter. Saved to {emails_path.name}")

    if args.guess_trades:
        from trade_guess import guess_trade, page_text_for_guess

        # Every prospect without a Trade in the sheet - including ones guessed
        # before, so an improved guesser corrects earlier guesses.
        blanks = [p for p in selected if not p["_sheet_trade"]]
        print(f"Guessing trades for {len(blanks)} prospects with none in the sheet ...")
        new_guesses = 0
        for p in blanks:
            html = homepage(p["website"])
            guess = guess_trade(page_text_for_guess(html), p["business_name"]) if html else guess_trade("", p["business_name"])
            previous = guesses.get(p["website"])
            changed = f"  (was: {previous})" if previous and guess and previous != guess else ""
            print(f"    {p['business_name']}: {guess or 'no guess'}{changed}")
            if guess:
                guesses[p["website"]] = guess
                new_guesses += 1
        # Saved even on a dry run: it's only this machine's notes, and it
        # means the real run doesn't have to read every homepage again.
        write_csv(guesses_path, ["website", "trade"], {w: {"website": w, "trade": t} for w, t in guesses.items()})
        print(f"{new_guesses} guessed; saved to {guesses_path}")

    if args.find_contacts or args.check_emails or args.lookup_companies or args.guess_trades:
        # Rebuild from the updated notes, so channels, trades and the CSVs
        # reflect what was just found. Dissolved firms drop out here.
        chosen = [p["slug"] for p in selected]
        prospects, skipped, closed = build()
        fill_scores()
        by_slug = {p["slug"]: p for p in prospects}
        selected = [by_slug[s] for s in chosen if s in by_slug]
        write_outputs()
        report()
        if not selected:
            sys.exit("Nothing left to push.")

    if args.teardown:
        if len(selected) > 10 and not args.yes_all:
            sys.exit(f"--teardown would check {len(selected)} sites. Narrow it with --only/--limit, or add --yes-all.")
        psi_key = os.environ.get("PAGESPEED_API_KEY", "")
        if not psi_key:
            sys.exit("--teardown needs PAGESPEED_API_KEY (the Google key the site's speed test uses).")
        from concurrent.futures import ThreadPoolExecutor, as_completed

        from findings import all_issues
        from site_teardown import teardown  # same folder as this script

        # Four at once: each check is mostly waiting on Google, and four stays
        # well inside the PageSpeed API's limits.
        print(f"Speed checking {len(selected)} sites, {TEARDOWN_WORKERS} at a time ...", flush=True)
        with ThreadPoolExecutor(max_workers=TEARDOWN_WORKERS) as pool:
            futures = {pool.submit(teardown, p["website"], psi_key): p for p in selected}
            for i, future in enumerate(as_completed(futures), 1):
                p = futures[future]
                try:
                    result = future.result()
                except Exception as e:  # one broken site never stops the batch
                    print(f"[{i}/{len(selected)}] {p['website']}: check failed ({type(e).__name__})", flush=True)
                    result = None
                if result is None:
                    print(f"[{i}/{len(selected)}] {p['website']}: couldn't check - logged, skipped next time", flush=True)
                    p["_teardown_failed"] = True
                    continue
                # Google's headline score and LCP fill the prospect's own fields
                # when the sheet has none (new lists); the sheet's figures win.
                score, lcp = result.pop("_mobile_score", None), result.pop("_lcp_s", None)
                if p.get("mobile_score") is None and score is not None:
                    p["mobile_score"] = score
                if p.get("lcp_s") is None and lcp is not None:
                    p["lcp_s"] = lcp
                p["teardown"] = result
                p["teardown_at"] = datetime.now(timezone.utc).isoformat()
                issues = all_issues(result, datetime.now(timezone.utc).year)
                p["_top_issue"] = issues[0] if issues else ""
                p["_issue_count"] = len(issues)
                score_txt = f"{int(p['mobile_score'])}/100" if p.get("mobile_score") is not None else "no score"
                print(
                    f"[{i}/{len(selected)}] {p['website']}: {score_txt}, {len(issues)} issue{'s' if len(issues) != 1 else ''}"
                    + (f" - worst: {issues[0]}" if issues else ""),
                    flush=True,
                )

    # Rewritten after the teardown, so new scores reach the Mailmeteor file.
    if args.teardown:
        write_outputs()

    if args.letters:
        make_letters()

    if args.dry_run:
        print("Dry run: nothing sent.")
        return

    for start in range(0, len(selected), 500):
        batch = selected[start : start + 500]
        req = urllib.request.Request(
            f"{api}/api/prospects/import",
            data=json.dumps(
                {"tenant_id": tenant, "prospects": [{k: v for k, v in p.items() if not k.startswith("_")} for p in batch]}
            ).encode(),
            headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                body = json.loads(res.read())
        except urllib.error.HTTPError as e:
            sys.exit(f"Import failed: HTTP {e.code} {e.read().decode(errors='replace')}")
        print(f"Pushed {body.get('upserted')} (rejected: {body.get('rejected')})")

    # Only now - after the dashboard has accepted them - are these sites
    # logged. A dry run or a failed push logs nothing.
    if args.teardown:
        now = datetime.now(timezone.utc).isoformat()
        ok = failed = 0
        for p in selected:
            if p.get("teardown_at"):
                log[p["website"]] = {
                    "checked_at": p["teardown_at"],
                    "result": "ok",
                    "mobile_score": p.get("mobile_score"),
                    "lcp_s": p.get("lcp_s"),
                    "top_issue": p.get("_top_issue", ""),
                    "issue_count": p.get("_issue_count", ""),
                }
                ok += 1
            elif p.get("_teardown_failed"):
                log[p["website"]] = {
                    "checked_at": now, "result": "failed", "mobile_score": None, "lcp_s": None, "top_issue": "", "issue_count": "",
                }
                failed += 1
        save_log()
        remaining = sum(1 for p in prospects if p["website"] not in log)
        print(f"Logged {ok} checked, {failed} couldn't be checked; {remaining} still to check.")


if __name__ == "__main__":
    main()
