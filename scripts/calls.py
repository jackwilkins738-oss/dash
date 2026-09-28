"""The call list: who's looking at their preview, joined with the phone numbers only you have.

The dashboard knows who opened their preview page and when - and, by design,
never has their phone number. This joins the two on this machine:

    Viewing       opened their preview - hottest first (most recent, most visits)
    Letter follow-up
                  posted a letter 7+ days ago and they haven't looked yet

Each firm shows its phone, contact, visits and a link to their preview
(opened with ?src=dashboard, so your own visit isn't counted as theirs).
Outcomes are logged in outreach/calls.csv; "Not interested" also puts them on
the do-not-contact list, and they - and "Won" - drop off the list.

Needs the dashboard's GET /api/prospects/activity (see the panel for the patch).
"""

from __future__ import annotations

import csv
import json
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import overrides

OUTCOMES = ["No answer", "Call back", "Replied to them", "Interested", "Not interested", "Won"]
FINAL = {"Not interested", "Won"}
LETTER_WAIT_DAYS = 7
PHONE_COLUMNS = ["Phone", "Phone number", "Telephone", "Tel", "Mobile", "Landline"]


class DashboardMissing(Exception):
    """The dashboard doesn't have the activity endpoint yet (or refused)."""


def fetch_activity(api: str, secret: str, tenant: str) -> dict[str, dict]:
    req = urllib.request.Request(
        f"{api.rstrip('/')}/api/prospects/activity?tenant_id={tenant}", headers={"Authorization": f"Bearer {secret}"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            rows = json.loads(res.read()).get("prospects") or []
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise DashboardMissing("Your dashboard doesn't have the activity update yet.") from e
        raise DashboardMissing(f"The dashboard answered HTTP {e.code}.") from e
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise DashboardMissing(f"Couldn't reach the dashboard ({getattr(e, 'reason', e)}).") from e
    return {r["slug"]: r for r in rows if r.get("slug")}


def load_calls(outreach: Path) -> dict[str, list[dict]]:
    path = outreach / "calls.csv"
    out: dict[str, list[dict]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                out.setdefault(r.get("key") or "", []).append(r)
    return out


def log_call(outreach: Path, sheet: str, key: str, business: str, outcome: str, note: str = "") -> None:
    if outcome not in OUTCOMES:
        raise ValueError("unknown outcome")
    path = outreach / "calls.csv"
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["key", "sheet", "business", "outcome", "note", "at"])
        if new:
            writer.writeheader()
        writer.writerow({"key": key, "sheet": sheet, "business": business, "outcome": outcome, "note": note[:300],
                         "at": datetime.now(timezone.utc).isoformat(timespec="seconds")})


def _when(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


def call_list(outreach: Path, sheet: str, secret: str, site: str, activity: dict[str, dict] | None,
              now: datetime | None = None) -> dict:
    """{"viewing": [...], "letters": [...]} for one sheet."""
    import openpyxl

    from contact_rules import load_blocklist
    from push_prospects import SKIP_STATUSES, domain_of, make_slug

    now = now or datetime.now(timezone.utc)
    wb = openpyxl.load_workbook(outreach / sheet, read_only=True, data_only=True)

    def tab(name: str) -> list[dict]:
        if name not in wb.sheetnames:
            return []
        rows = list(wb[name].iter_rows(values_only=True))
        header = [str(h).strip() if h else "" for h in rows[0]] if rows else []
        return [dict(zip(header, v)) for v in rows[1:]]

    decided = overrides.load(outreach, sheet)
    rows = []
    for row in tab("Outreach"):
        fixed = overrides.apply(row, decided.get(overrides.row_key(row), {}))
        if fixed is not None:
            rows.append(fixed)
    for row in tab("Check website"):
        d = decided.get(overrides.row_key(row), {})
        if d.get("website"):
            fixed = overrides.apply(row, d)
            if fixed is not None:
                rows.append(fixed)
    wb.close()

    block = load_blocklist(outreach, domain_of)
    found = {}
    contacts_path = outreach / "contacts-found.csv"
    if contacts_path.exists():
        with contacts_path.open(encoding="utf-8") as f:
            found = {r["website"]: r for r in csv.DictReader(f) if r.get("website")}
    posted = {}
    sent_path = outreach / "letters-sent.csv"
    if sent_path.exists():
        with sent_path.open(encoding="utf-8") as f:
            posted = {r["key"]: r.get("posted") or "" for r in csv.DictReader(f) if r.get("key")}
    calls = load_calls(outreach)

    viewing, letters = [], []
    for row in rows:
        business = str(row.get("Business") or "").strip()
        domain = domain_of(str(row.get("Website") or ""))
        if not business or not domain or str(row.get("Status") or "") in SKIP_STATUSES:
            continue
        if block.why(domain, str(row.get("Email") or ""), business):
            continue
        key = overrides.row_key(row)
        history = calls.get(key, [])
        last = history[-1] if history else None
        if last and last.get("outcome") in FINAL:
            continue
        slug = make_slug(business, domain, secret)
        extra = found.get(domain) or {}
        phone = next((str(row[c]).strip() for c in PHONE_COLUMNS if str(row.get(c) or "").strip()), "") or extra.get("phone", "")
        act = (activity or {}).get(slug) or {}
        item = {
            "key": key, "business": business, "website": domain,
            "contact": str(row.get("Contact name") or "").strip() or extra.get("contact", ""),
            "phone": phone, "email": str(row.get("Email") or "").strip() or extra.get("email", ""),
            "preview": f"{site}/for/{slug}?src=dashboard",
            "views": int(act.get("view_count") or 0), "last_viewed": act.get("last_viewed_at") or "",
            "status": act.get("status") or "",
            "last_call": last.get("outcome") if last else "", "last_call_at": last.get("at") if last else "",
            "calls": len(history), "posted": posted.get(key, ""),
        }
        called = _when(item["last_call_at"])
        viewed = _when(item["last_viewed"])
        if item["views"] and (not called or not viewed or viewed > called or last.get("outcome") in ("Call back", "Interested")):
            # Hottest first: seen recently, and more than once.
            age_h = (now - viewed).total_seconds() / 3600 if viewed else 1e6
            item["heat"] = round(item["views"] * 10 / (1 + age_h / 24), 2)
            viewing.append(item)
        elif item["posted"] and activity is not None and not item["views"]:
            try:
                waited = (now.date() - date.fromisoformat(item["posted"])).days
            except ValueError:
                continue
            recently_called = called and (now - called).days < 14
            if waited >= LETTER_WAIT_DAYS and not recently_called:
                item["waited"] = waited
                letters.append(item)
    viewing.sort(key=lambda i: -i["heat"])
    letters.sort(key=lambda i: -i["waited"])

    # Replies waiting for you (from reply_scanner.py), from any list - newest first.
    by_site = {domain_of(str(r.get("Website") or "")): r for r in rows}
    replied = []
    replies_path = outreach / "replies.csv"
    if replies_path.exists():
        with replies_path.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("kind") not in ("interested", "read it") or r.get("handled"):
                    continue
                row = by_site.get(r.get("website") or "") or {}
                extra = found.get(r.get("website") or "") or {}
                replied.append({
                    "key": overrides.row_key(row) if row else overrides.row_key({"Business": r.get("business", "")}),
                    "business": r.get("business", ""), "website": r.get("website", ""), "email": r.get("from", ""),
                    "contact": str(row.get("Contact name") or "").strip() or extra.get("contact", ""),
                    "phone": next((str(row[c]).strip() for c in PHONE_COLUMNS if str(row.get(c) or "").strip()), "") or extra.get("phone", ""),
                    "kind": r.get("kind", ""), "snippet": r.get("snippet", ""), "subject": r.get("subject", ""),
                    "replied_at": r.get("date", ""), "message_id": r.get("message_id", ""),
                    "preview": "", "views": 0, "last_viewed": "", "last_call": "", "last_call_at": "", "calls": 0, "posted": "",
                })
    replied.sort(key=lambda i: i["replied_at"], reverse=True)
    return {"viewing": viewing, "letters": letters, "replied": replied}


def mark_reply_handled(outreach: Path, business: str) -> None:
    """Once you've called or answered them, their replies leave the top of the Calls tab."""
    path = outreach / "replies.csv"
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fields, rows = reader.fieldnames or [], list(reader)
    for r in rows:
        if r.get("business") == business and r.get("kind") in ("interested", "read it") and not r.get("handled"):
            r["handled"] = f"answered {date.today().isoformat()}"
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
