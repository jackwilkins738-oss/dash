"""The call list: who's looking at their preview, joined with the phone numbers only you have.

The dashboard knows who opened their preview page and when - and, by design,
never has their phone number. This joins the two on this machine:

    Viewing       opened their preview - hottest first (most recent, most visits)
    Letter follow-up
                  posted a letter 7+ days ago and they haven't looked yet
    Call-backs    "Call back" with a date (or "not now" replies parked for a few
                  months) - they come back here, top of the list, on the day

Each firm shows its phone, contact, visits and a link to their preview
(opened with ?src=dashboard, so your own visit isn't counted as theirs).
Outcomes are logged in outreach/calls.csv; "Not interested" also puts them on
the do-not-contact list, and they - and "Won" - drop off the list.

Needs the dashboard's GET /api/prospects/activity (see the panel for the patch).
"""

from __future__ import annotations

import csv
import json
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import overrides

OUTCOMES = ["No answer", "Call back", "Replied to them", "Interested", "Quoted", "Not interested", "Won"]
FINAL = {"Not interested", "Won"}
# Why a firm said no - one tap on "Not interested", kept in the call's note ("Reason: Price") so the
# scorecard can count them. A month of these says what the real objection is.
LOST_REASONS = ["Price", "Timing", "Has someone", "No need", "Other"]
LETTER_WAIT_DAYS = 7
PHONE_COLUMNS = ["Phone", "Phone number", "Telephone", "Tel", "Mobile", "Landline"]


class DashboardMissing(Exception):
    """The dashboard doesn't have the activity endpoint yet (or refused)."""


# One-tap answers from the preview page (dashboard migration 059) -> how they land in replies.csv.
CHOICE_REPLIES = {
    "call": ("interested", "call", 'Tapped "Yes, give me a ring" on their preview'),
    "whatsapp": ("interested", "call", 'Tapped "WhatsApp me" on their preview - check WhatsApp'),
    "not_now": ("read it", "later", 'Tapped "Maybe later" on their preview'),
}


def interest(item: dict) -> float:
    """How keen a viewer looks: visits, real time on the page, how far they got - the price and the
    rebuilt homepage count most. Before migration 059 it's visits alone, as it always was."""
    score = item.get("views", 0) * 10
    score += min(item.get("seconds", 0), 600) / 20  # up to 30 for ten minutes of looking
    score += item.get("scroll", 0) / 10  # up to 10 for reaching the bottom
    reached = set(item.get("reached") or [])
    score += 15 * ("pricing" in reached) + 8 * ("rebuilt" in reached) + 5 * ("reply" in reached)
    return score


def sync_choices(outreach: Path, choices: list[tuple[dict, str, str, str]]) -> int:
    """Adds each new one-tap answer to replies.csv once -> how many were added."""
    from reply_scanner import FIELDS, REPLIES

    path = outreach / REPLIES
    existing = []
    if path.exists():
        with path.open(encoding="utf-8") as f:
            existing = list(csv.DictReader(f))
    seen = {r.get("message_id") for r in existing}
    new = []
    for act, business, domain, email in choices:
        kind, intent, said = CHOICE_REPLIES[act["choice"]]
        mid = f"preview-choice:{act.get('slug')}:{act['choice']}"
        if mid in seen:
            continue
        seen.add(mid)
        new.append({"message_id": mid, "date": (act.get("choice_at") or "")[:16], "from": email.lower(), "business": business,
                    "website": domain, "kind": kind, "subject": "", "snippet": said, "handled": "", "intent": intent,
                    "message": said, "objection": "not now" if act["choice"] == "not_now" else ""})
    if new:
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
            w.writeheader()
            w.writerows(existing + new)
    return len(new)


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


# ---------------------------------------------------------------- call-backs

CALLBACKS = "callbacks.csv"
CALLBACK_FIELDS = ["key", "sheet", "business", "due", "note", "created", "done"]
MAX_AHEAD_DAYS = 400


def parse_due(text: str, today: date) -> date | None:
    """'3d', '2w', '3m', 'tomorrow', or a date (2026-11-03 / 3/11/2026) -> the day to call back."""
    t = str(text or "").strip().lower()
    if t in ("tomorrow", "1d"):
        return today + timedelta(days=1)
    m = re.fullmatch(r"(\d{1,3})\s*(d|day|days|w|wk|week|weeks|m|mo|month|months)", t)
    if m:
        n, unit = int(m.group(1)), m.group(2)[0]
        days = n * {"d": 1, "w": 7, "m": 30}[unit]
        due = today + timedelta(days=days)
    else:
        due = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y", "%d-%m-%Y"):
            try:
                due = datetime.strptime(t, fmt).date()
                break
            except ValueError:
                continue
    if due is None or due <= today - timedelta(days=1) or (due - today).days > MAX_AHEAD_DAYS:
        return None
    return due


def _callback_rows(outreach: Path) -> list[dict]:
    path = outreach / CALLBACKS
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_callbacks(outreach: Path, rows: list[dict]) -> None:
    with (outreach / CALLBACKS).open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CALLBACK_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def add_callback(outreach: Path, sheet: str, key: str, business: str, due: date, note: str = "") -> None:
    """One open call-back per firm: a new date replaces the old one."""
    rows = [r for r in _callback_rows(outreach) if not (r.get("key") == key and not r.get("done"))]
    rows.append({"key": key, "sheet": sheet, "business": business, "due": due.isoformat(), "note": note[:300],
                 "created": datetime.now(timezone.utc).isoformat(timespec="seconds"), "done": ""})
    _write_callbacks(outreach, rows)


def complete_callbacks(outreach: Path, key: str) -> None:
    """Any outcome logged for them closes their open call-back."""
    rows = _callback_rows(outreach)
    changed = False
    for r in rows:
        if r.get("key") == key and not r.get("done"):
            r["done"] = date.today().isoformat()
            changed = True
    if changed:
        _write_callbacks(outreach, rows)


def due_callbacks(outreach: Path, today: date) -> list[dict]:
    """Open call-backs due today or overdue, oldest first."""
    out = []
    for r in _callback_rows(outreach):
        try:
            due = date.fromisoformat(r.get("due") or "")
        except ValueError:
            continue
        if not r.get("done") and due <= today:
            out.append({**r, "overdue": (today - due).days})
    return sorted(out, key=lambda r: r["due"])


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

    viewing, letters, choices = [], [], []
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
        if act.get("status") == "lost":  # "not for us" on their preview - never call them about it
            from contact_rules import add_to_blocklist

            add_to_blocklist(outreach, [("name", business), ("website", domain)], "not for us (preview page)")
            continue
        if act.get("choice") in CHOICE_REPLIES:
            # A one-tap answer on their preview is a reply: into replies.csv (so it's in "Replied" and
            # their follow-up email stops), not the "looking" list.
            choices.append((act, business, domain, str(row.get("Email") or "").strip() or extra.get("email", "")))
            continue
        item = {
            "key": key, "business": business, "website": domain,
            "contact": str(row.get("Contact name") or "").strip() or extra.get("contact", ""),
            "phone": phone, "email": str(row.get("Email") or "").strip() or extra.get("email", ""),
            "area": str(row.get("Area") or row.get("Town") or "").strip(),
            "preview": f"{site}/for/{slug}?src=dashboard",
            "views": int(act.get("view_count") or 0), "last_viewed": act.get("last_viewed_at") or "",
            "first_viewed": act.get("first_viewed_at") or "",
            "status": act.get("status") or "",
            "last_call": last.get("outcome") if last else "", "last_call_at": last.get("at") if last else "",
            "calls": len(history), "posted": posted.get(key, ""),
            "seconds": int(act.get("engaged_seconds") or 0), "scroll": int(act.get("max_scroll") or 0),
            "reached": [r for r in (act.get("reached") or []) if isinstance(r, str)],
        }
        called = _when(item["last_call_at"])
        viewed = _when(item["last_viewed"])
        if item["views"] and (not called or not viewed or viewed > called or last.get("outcome") in ("Call back", "Interested")):
            # Hottest first: seen recently, and more than once.
            age_h = (now - viewed).total_seconds() / 3600 if viewed else 1e6
            item["heat"] = round(interest(item) / (1 + age_h / 24), 2)
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
    if choices:
        sync_choices(outreach, choices)
    letters.sort(key=lambda i: -i["waited"])

    # Replies waiting for you (from reply_scanner.py), from any list - newest first.
    from reply_scanner import intent as reply_intent

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
                slug = make_slug(str(row.get("Business") or r.get("business") or ""), r.get("website") or "", secret) if r.get("website") else ""
                act = (activity or {}).get(slug) or {}
                replied.append({
                    "key": overrides.row_key(row) if row else overrides.row_key({"Business": r.get("business", "")}),
                    "business": r.get("business", ""), "website": r.get("website", ""), "email": r.get("from", ""),
                    "contact": str(row.get("Contact name") or "").strip() or extra.get("contact", ""),
                    "phone": next((str(row[c]).strip() for c in PHONE_COLUMNS if str(row.get(c) or "").strip()), "") or extra.get("phone", ""),
                    "kind": r.get("kind", ""), "snippet": r.get("snippet", ""), "subject": r.get("subject", ""),
                    "message": r.get("message") or r.get("snippet", ""),
                    "trade": str(row.get("Trade") or "").strip(), "area": str(row.get("Area") or row.get("Town") or "").strip(),
                    "mobile_score": str(row.get("Mobile score") or "").strip(),
                    "intent": r.get("intent") or reply_intent(r.get("snippet", "")),
                    "replied_at": r.get("date", ""), "message_id": r.get("message_id", ""),
                    "preview": f"{site}/for/{slug}?src=dashboard" if act else "",
                    "views": int(act.get("view_count") or 0), "last_viewed": act.get("last_viewed_at") or "",
                    "last_call": "", "last_call_at": "", "calls": 0, "posted": "",
                })
    replied.sort(key=lambda i: i["replied_at"], reverse=True)

    # Call-backs due today or overdue - from every list, so none is missed by looking at the wrong sheet.
    by_key = {overrides.row_key(r): r for r in rows}
    callbacks = []
    for cb in due_callbacks(outreach, now.date()):
        row = by_key.get(cb["key"]) or {}
        domain = domain_of(str(row.get("Website") or "")) or ""
        extra = found.get(domain) or {}
        slug = make_slug(cb["business"], domain, secret) if domain else ""
        act = (activity or {}).get(slug) or {}
        callbacks.append({
            "key": cb["key"], "sheet": cb.get("sheet") or sheet, "business": cb["business"], "website": domain,
            "contact": str(row.get("Contact name") or "").strip() or extra.get("contact", ""),
            "phone": next((str(row[c]).strip() for c in PHONE_COLUMNS if str(row.get(c) or "").strip()), "") or extra.get("phone", ""),
            "email": str(row.get("Email") or "").strip() or extra.get("email", ""),
            "area": str(row.get("Area") or row.get("Town") or "").strip(),
            "preview": f"{site}/for/{slug}?src=dashboard" if slug else "",
            "views": int(act.get("view_count") or 0), "last_viewed": act.get("last_viewed_at") or "",
            "due": cb["due"], "overdue": cb["overdue"], "note": cb.get("note", ""),
            "last_call": "", "last_call_at": "", "calls": 0, "posted": "",
        })
    # Someone due a call-back isn't also listed again below.
    queued = {c["key"] for c in callbacks}
    viewing = [v for v in viewing if v["key"] not in queued]
    return {"callbacks": callbacks, "viewing": viewing, "letters": letters, "replied": replied}


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
