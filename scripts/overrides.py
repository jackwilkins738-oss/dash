"""Your decisions from the panel's Review tab, applied on top of a sheet without editing it.

outreach/overrides.csv (this machine only): one row per decision -
    sheet, key, field, value, updated
where key identifies the firm within that sheet (company number when the
sheet has one, otherwise the business name) and field is one of:
    company_type   "Ltd", "Sole trader" ... - fills the Company type column
    email          a corrected email address ("" = none: send a letter)
    website        a confirmed website for a "Check website" row ("" = not theirs)
    skip           "yes" - leave this firm out of every run

push_prospects.py applies them as it reads the sheet, so the sheet itself
never changes and a decision can be undone by deleting its row here.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path

FIELDS = ("company_type", "email", "website", "skip")
FILE_FIELDS = ["sheet", "key", "field", "value", "updated"]


def _name(name: str) -> str:
    s = (name or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(w for w in s.split() if w not in {"ltd", "limited", "llp", "plc", "the", "uk", "co", "company"})


def row_key(row: dict) -> str:
    """How a firm is known across runs: its company number if the sheet has one, else its name."""
    number = str(row.get("Company number") or "").strip().upper()
    if number:
        return f"no:{number.zfill(8)}"
    return f"name:{_name(str(row.get('Business') or ''))}"


def load(outreach: Path, sheet: str) -> dict[str, dict[str, str]]:
    """key -> {field: value} for one sheet."""
    path = outreach / "overrides.csv"
    out: dict[str, dict[str, str]] = {}
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("sheet") == sheet and r.get("field") in FIELDS and r.get("key"):
                    out.setdefault(r["key"], {})[r["field"]] = r.get("value") or ""
    return out


def save(outreach: Path, sheet: str, key: str, field: str, value: str) -> None:
    if field not in FIELDS:
        raise ValueError(f"unknown field {field}")
    path = outreach / "overrides.csv"
    rows: list[dict] = []
    if path.exists():
        with path.open(encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f) if not (r.get("sheet") == sheet and r.get("key") == key and r.get("field") == field)]
    rows.append({"sheet": sheet, "key": key, "field": field, "value": value, "updated": datetime.now(timezone.utc).isoformat()})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FILE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def remove(outreach: Path, sheet: str, key: str, field: str | None = None) -> None:
    """Undo a decision (or every decision for that firm)."""
    path = outreach / "overrides.csv"
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        rows = [
            r for r in csv.DictReader(f)
            if not (r.get("sheet") == sheet and r.get("key") == key and (field is None or r.get("field") == field))
        ]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FILE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def apply(row: dict, decisions: dict[str, str]) -> dict | None:
    """The row with decisions applied, or None if it's to be skipped."""
    if decisions.get("skip") == "yes":
        return None
    row = dict(row)
    if "company_type" in decisions:
        row["Company type"] = decisions["company_type"]
    if "email" in decisions:
        row["Email"] = decisions["email"]
        row["Email check"] = ""  # a corrected address starts fresh
    if "website" in decisions:
        row["Website"] = decisions["website"]
    return row
