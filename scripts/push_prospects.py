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
    --out PATH       where to write the links CSV (default: preview-links.csv beside the sheet)
    --dry-run        write the CSV, send nothing
Env:
    PROSPECTS_API_SECRET  required (also used to make the links unguessable)
    DASHBOARD_API_URL     default https://admin.scalardigital.co.uk
    SCALAR_TENANT_ID      default Scalar Digital's own tenant (already public in
                          the site's track.js snippet)
    SITE_URL              default https://www.scalardigital.co.uk
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
from pathlib import Path
from urllib.parse import urlparse

try:
    import openpyxl
except ImportError:
    sys.exit("Needs openpyxl: python -m pip install openpyxl")

DEFAULT_TENANT = "abdc6408-1fd5-4fb6-9c4c-53600b571a6d"
SKIP_STATUSES = {"Removed - parked / unsuitable", "Lost / not interested"}
LETTER_COMPANY_TYPES = {"sole trader", "partnership", "none", "no record"}


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


def channel_for(row: dict) -> str:
    company_type = str(row.get("Company type") or "").strip().lower()
    email = str(row.get("Email") or "").strip()
    status = str(row.get("Status") or "").lower()
    email_ok = (
        "@" in email
        and "invalid" not in str(row.get("Email check") or "").lower()
        and "wrong email" not in status
        and "invalid email" not in status
    )
    if company_type in LETTER_COMPANY_TYPES:
        return "letter"  # PECR: no cold email to sole traders or ordinary partnerships
    return "email" if email_ok else "letter"


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
    args = ap.parse_args()

    secret = os.environ.get("PROSPECTS_API_SECRET", "")
    if len(secret) < 32:
        sys.exit("Set PROSPECTS_API_SECRET (32+ characters, same value as in Vercel) first.")
    api = os.environ.get("DASHBOARD_API_URL", "https://admin.scalardigital.co.uk").rstrip("/")
    tenant = os.environ.get("SCALAR_TENANT_ID", DEFAULT_TENANT)
    site = os.environ.get("SITE_URL", "https://www.scalardigital.co.uk").rstrip("/")

    if not args.sheet.exists():
        sys.exit(f"Can't find the sheet at {args.sheet} - pass --sheet PATH")

    wb = openpyxl.load_workbook(args.sheet, read_only=True, data_only=True)
    rows = list(wb["Outreach"].iter_rows(values_only=True))
    header = [str(h).strip() if h else "" for h in rows[0]]

    prospects, links, skipped = [], [], 0
    seen = set()
    for values in rows[1:]:
        row = dict(zip(header, values))
        business = str(row.get("Business") or "").strip()
        domain = domain_of(str(row.get("Website") or ""))
        if not business or not domain or str(row.get("Status") or "") in SKIP_STATUSES:
            skipped += 1
            continue
        slug = make_slug(business, domain, secret)
        if slug in seen:
            skipped += 1
            continue
        seen.add(slug)
        channel = channel_for(row)
        prospects.append(
            {
                "slug": slug,
                "business_name": business,
                "trade": row.get("Trade") or None,
                "area": row.get("Area") or None,
                "website": domain,
                "mobile_score": number(row.get("Mobile score")),
                "lcp_s": number(row.get("LCP (s)")),
                "channel": channel,
            }
        )
        src = "email" if channel == "email" else "letter"
        links.append(
            {
                "Business": business,
                "Email": row.get("Email") or "",
                "Channel": channel,
                "Status": row.get("Status") or "",
                "preview_url": f"{site}/for/{slug}?src={src}",
            }
        )

    out = args.out or args.sheet.parent / "preview-links.csv"
    with out.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["Business", "Email", "Channel", "Status", "preview_url"])
        writer.writeheader()
        writer.writerows(links)

    by_channel = {c: sum(1 for p in prospects if p["channel"] == c) for c in ("email", "letter")}
    print(f"{len(prospects)} prospects ({by_channel['email']} email, {by_channel['letter']} letter), {skipped} skipped")
    print(f"Wrote {out}")

    if args.dry_run:
        print("Dry run: nothing sent.")
        return

    for start in range(0, len(prospects), 500):
        batch = prospects[start : start + 500]
        req = urllib.request.Request(
            f"{api}/api/prospects/import",
            data=json.dumps({"tenant_id": tenant, "prospects": batch}).encode(),
            headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as res:
                body = json.loads(res.read())
        except urllib.error.HTTPError as e:
            sys.exit(f"Import failed: HTTP {e.code} {e.read().decode(errors='replace')}")
        print(f"Pushed {body.get('upserted')} (rejected: {body.get('rejected')})")


if __name__ == "__main__":
    main()
