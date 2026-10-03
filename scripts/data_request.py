"""Data requests (UK GDPR): what you hold on a prospect - shown, exported, or erased everywhere.

    python scripts/data_request.py find   info@kerrroofing.co.uk
    python scripts/data_request.py export kerrroofing.co.uk
    python scripts/data_request.py erase  kerrroofing.co.uk

Anyone you email can ask what you hold on them (a subject access request: answer within a month) or
ask you to delete it (erasure). Give their email address or website; this finds them in:

    every list (.xlsx) in outreach/, the results workbook included
    every CSV in outreach/ - sends, replies, calls, email checks, first lines, links and the rest
    their preview record on your dashboard

export   writes outreach/data-requests/<date>-<website>.txt - everything above in plain words, ready
         to paste into a reply or attach.
erase    deletes them from all of it, then puts their website and email on do-not-contact.csv. That
         one line is allowed (and needed): it's what stops a future list emailing them again.

Not covered, so do these by hand: emails in your inbox and Sent folder, letters you've already
printed, and the nightly backups (they age out after 14 days). A firm that became a client is never
erased from the dashboard - their record is kept with their contract.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

KEEP = {"do-not-contact.csv"}  # the suppression list itself
FOLDER = "data-requests"
SLUG = re.compile(r"/for/([a-z0-9-]+)")


class RequestError(Exception):
    pass


def domain_of(text: str) -> str:
    raw = (text or "").strip().lower()
    if not raw or "@" in raw or " " in raw:
        return ""
    host = (urlparse(raw if re.match(r"^https?://", raw) else f"https://{raw}").hostname or "").lower()
    return host.removeprefix("www.") if "." in host else ""


class Who:
    """The person asking, as every place might record them."""

    def __init__(self, given: str) -> None:
        given = (given or "").strip()
        self.emails: set[str] = set()
        self.domains: set[str] = set()
        self.slugs: set[str] = set()
        self.names: set[str] = set()
        if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", given):
            self.emails.add(given.lower())
            self.domains.add(given.lower().split("@", 1)[1])
        elif domain_of(given):
            self.domains.add(domain_of(given))
        else:
            raise RequestError("Give their email address or their website, e.g. info@kerrroofing.co.uk or kerrroofing.co.uk.")

    def matches(self, row: dict) -> bool:
        for v in row.values():
            s = str(v or "").strip().lower()
            if not s:
                continue
            if s in self.emails or (domain_of(s) and domain_of(s) in self.domains):
                return True
            if "@" in s and s.rsplit("@", 1)[-1] in self.domains:
                return True
            m = SLUG.search(s)
            if m and m.group(1) in self.slugs:
                return True
        return False

    def learn(self, row: dict) -> None:
        """A matching row may hold their other details (a website row gives the email, and the slug)."""
        for k, v in row.items():
            s = str(v or "").strip()
            low = s.lower()
            if re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", low):
                self.emails.add(low)
            m = SLUG.search(low)
            if m:
                self.slugs.add(m.group(1))
            if (k or "").strip().lower() in ("business", "business_name") and s:
                self.names.add(s)


def _csv(path: Path) -> tuple[list[str], list[dict]]:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            with path.open(encoding=enc, newline="") as f:
                r = csv.DictReader(f)
                return list(r.fieldnames or []), list(r)
        except UnicodeDecodeError:
            continue
    return [], []


def _sheets(outreach: Path) -> list[Path]:
    return sorted(p for p in outreach.glob("*.xlsx") if not p.name.startswith("~$") and not p.name.endswith(".tmp.xlsx"))


def _sheet_rows(path: Path) -> list[tuple[str, list[str], list[dict]]]:
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    out = []
    try:
        for ws in wb.worksheets:
            rows = list(ws.iter_rows(values_only=True))
            if not rows:
                continue
            header = [str(h).strip() if h is not None else "" for h in rows[0]]
            out.append((ws.title, header, [dict(zip(header, r)) for r in rows[1:]]))
    finally:
        wb.close()
    return out


def find(outreach: Path, who: Who, secret: str = "") -> dict:
    """{source: [rows]} for everywhere on this PC that holds them. Looks twice, so details learnt from
    one place (their email, from a list found by website) find them in the rest."""
    found: dict[str, list[dict]] = {}
    for _ in range(2):
        found = {}
        for sheet in _sheets(outreach):
            for tab, _header, rows in _sheet_rows(sheet):
                hits = [r for r in rows if who.matches(r)]
                if hits:
                    found[f"{sheet.name} ({tab})"] = hits
        for path in sorted(outreach.glob("*.csv")):
            if path.name in KEEP:
                continue
            hits = [r for r in _csv(path)[1] if who.matches(r)]
            if hits:
                found[path.name] = hits
        for rows in found.values():
            for r in rows:
                who.learn(r)
        if secret:
            from push_prospects import make_slug

            for d in list(who.domains):
                for n in list(who.names):
                    who.slugs.add(make_slug(n, d, secret))
    return found


def dashboard(api: str, secret: str, slug: str, method: str = "GET") -> dict | None:
    req = urllib.request.Request(f"{api.rstrip('/')}/api/prospects/{slug}", method=method,
                                 headers={"Authorization": f"Bearer {secret}"})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.loads(res.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        try:
            msg = json.loads(e.read()).get("error") or f"HTTP {e.code}"
        except ValueError:
            msg = f"HTTP {e.code}"
        raise RequestError(f"The dashboard said: {msg}") from e
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise RequestError(f"Couldn't reach the dashboard ({getattr(e, 'reason', e)}) - nothing there was changed.") from e


SKIP_FIELDS = {"teardown", "frames", "screenshot"}


def report(who: Who, found: dict, online: dict[str, dict]) -> str:
    """Everything held, in plain words - what you send them."""
    name = sorted(who.names)[0] if who.names else sorted(who.domains)[0]
    lines = [f"Personal data held by Scalar Digital about {name}", f"Prepared {date.today():%d %B %Y}", "",
             "Why we hold it: legitimate interest - we contacted your business about its website. We hold only",
             "business contact details that are publicly listed (website, Companies House) and our own notes.",
             "Ask us to delete it at any time and we will, keeping only your website and email address on a",
             "do-not-contact list so you are never contacted again.", ""]
    for source, rows in found.items():
        lines.append(f"== {source}")
        for r in rows:
            for k, v in r.items():
                if k and v not in (None, "") and k not in SKIP_FIELDS:
                    lines.append(f"   {k}: {v}")
            lines.append("")
    for slug, rec in online.items():
        lines.append(f"== Preview page record ({slug}) on our dashboard")
        for k, v in (rec or {}).items():
            if v not in (None, "") and k not in SKIP_FIELDS:
                lines.append(f"   {k}: {v}")
        lines.append("")
    if not found and not online:
        lines.append("We hold no data about you.")
    return "\n".join(lines).rstrip() + "\n"


def export(outreach: Path, given: str, api: str = "", secret: str = "") -> Path:
    who = Who(given)
    found = find(outreach, who, secret)
    online = {}
    if api and secret:
        for slug in sorted(who.slugs):
            rec = dashboard(api, secret, slug)
            if rec and rec.get("prospect"):
                online[slug] = rec["prospect"]
    folder = outreach / FOLDER
    folder.mkdir(exist_ok=True)
    path = folder / f"{date.today().isoformat()}-{sorted(who.domains)[0]}.txt"
    path.write_text(report(who, found, online), encoding="utf-8")
    return path


def _erase_sheet(path: Path, who: Who) -> int:
    import openpyxl

    wb = openpyxl.load_workbook(path)
    gone = 0
    for ws in wb.worksheets:
        header = [str(c.value).strip() if c.value is not None else "" for c in ws[1]] if ws.max_row else []
        for i in range(ws.max_row, 1, -1):
            row = dict(zip(header, (c.value for c in ws[i])))
            if who.matches(row):
                ws.delete_rows(i)
                gone += 1
    if gone:
        tmp = path.with_suffix(".tmp.xlsx")
        wb.save(tmp)
        tmp.replace(path)
    return gone


def erase(outreach: Path, given: str, api: str = "", secret: str = "") -> list[str]:
    """Deletes them everywhere -> lines for the log. Stops before touching anything on this PC if the
    dashboard refuses (a client) or can't be reached, so it's never half done."""
    from contact_rules import add_to_blocklist

    who = Who(given)
    found = find(outreach, who, secret)
    notes = []
    if api and secret:
        for slug in sorted(who.slugs):
            res = dashboard(api, secret, slug, method="DELETE") or {}
            if res.get("deleted"):
                notes.append(f"Dashboard: preview record {slug} deleted - their preview link now shows 'not found'.")
            if res.get("quotes"):
                notes.append(f"Dashboard: {res['quotes']} quote(s) sent to them were kept - delete those in the dashboard if they ask.")
    else:
        notes.append("Dashboard not checked - add PROSPECTS_API_SECRET in Settings, then erase again to remove their preview page.")
    locked = []
    for sheet in _sheets(outreach):
        try:
            n = _erase_sheet(sheet, who)
        except PermissionError:
            locked.append(sheet.name)
            continue
        if n:
            notes.append(f"{sheet.name}: {n} row(s) deleted.")
    for path in sorted(outreach.glob("*.csv")):
        if path.name in KEEP:
            continue
        fields, rows = _csv(path)
        keep = [r for r in rows if not who.matches(r)]
        if len(keep) == len(rows):
            continue
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(keep)
        notes.append(f"{path.name}: {len(rows) - len(keep)} row(s) deleted.")
    entries = [("website", d) for d in sorted(who.domains)] + [("email", e) for e in sorted(who.emails)]
    add_to_blocklist(outreach, entries, f"erasure request {date.today().isoformat()}")
    notes.append("do-not-contact.csv: kept their website and email only, so no future list emails them.")
    if locked:
        notes.append(f"NOT DONE - open in Excel: {', '.join(locked)}. Close it and erase again.")
    if not found:
        notes.append("Nothing about them was on this PC.")
    notes.append("By hand: delete their emails from your inbox and Sent folder.")
    return notes


def main() -> None:
    import reply_scanner

    if len(sys.argv) != 3 or sys.argv[1] not in ("find", "export", "erase"):
        sys.exit("Usage: python scripts/data_request.py find|export|erase <their email or website>")
    outreach = reply_scanner.outreach_dir()
    api = os.environ.get("DASHBOARD_API_URL", "https://admin.scalardigital.co.uk")
    secret = os.environ.get("PROSPECTS_API_SECRET", "")
    try:
        if sys.argv[1] == "find":
            who = Who(sys.argv[2])
            found = find(outreach, who, secret)
            for source, rows in found.items():
                print(f"{source}: {len(rows)} row(s)")
            print(f"Preview pages: {', '.join(sorted(who.slugs)) or 'none found'}")
            if not found:
                print("Nothing about them on this PC.")
        elif sys.argv[1] == "export":
            path = export(outreach, sys.argv[2], api, secret)
            print(f"Written: {path} - check it, then send it to them.")
        else:
            for n in erase(outreach, sys.argv[2], api, secret):
                print(n)
    except RequestError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    main()
