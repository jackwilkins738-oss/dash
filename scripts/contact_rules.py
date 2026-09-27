"""Who must never be contacted again, and which list each firm belongs to.

Two files in outreach/, both on this machine only:

  do-not-contact.csv  Firms that said no, from any list. Anyone whose Status
                      in ANY sheet says they're not interested, unsubscribed
                      or asked not to be contacted is blocked from every other
                      sheet too - plus anything added by hand (the panel's
                      Review tab, or this file directly). Keyed on website,
                      email and business name, so a second list that spells
                      the firm differently still catches them.

  claims.csv          Which sheet each website was first pushed from. When the
                      same firm turns up in a newer list, that list leaves it
                      out instead of making them a second preview page and a
                      second email. If the claiming sheet is deleted, the
                      claim lapses.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path

OBJECTION = re.compile(r"not interested|unsubscri|opted? out|do not contact|don't contact|remove me|stop", re.I)
BLOCK_FIELDS = ["value", "kind", "reason", "added"]


def normalise_name(name: str) -> str:
    s = (name or "").lower().replace("&", " and ")
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(w for w in s.split() if w not in {"ltd", "limited", "llp", "plc", "the", "uk", "co", "company"})


class Blocklist:
    def __init__(self) -> None:
        self.domains: dict[str, str] = {}
        self.emails: dict[str, str] = {}
        self.names: dict[str, str] = {}

    def add(self, kind: str, value: str, reason: str) -> None:
        value = (value or "").strip().lower()
        if not value:
            return
        target = {"website": self.domains, "email": self.emails, "name": self.names}.get(kind)
        if target is not None:
            if kind == "name":
                value = normalise_name(value)
            if value:
                target.setdefault(value, reason)

    def why(self, domain: str | None, email: str | None, business: str | None) -> str | None:
        """The reason this firm is blocked, or None."""
        if domain and domain.lower() in self.domains:
            return self.domains[domain.lower()]
        if email and email.strip().lower() in self.emails:
            return self.emails[email.strip().lower()]
        name = normalise_name(business or "")
        if name and name in self.names:
            return self.names[name]
        return None


def load_blocklist(outreach: Path, domain_of, listed: dict[str, set[str]] | None = None) -> Blocklist:
    """Everyone who said no, from do-not-contact.csv and every sheet's Status column.

    Pass a dict as `listed` to also collect which websites each sheet lists (for Claims)."""
    import openpyxl

    block = Blocklist()
    path = outreach / "do-not-contact.csv"
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                block.add(r.get("kind") or "", r.get("value") or "", r.get("reason") or "added by hand")
    for sheet in outreach.glob("*.xlsx"):
        if sheet.name.startswith("~$"):
            continue
        try:
            wb = openpyxl.load_workbook(sheet, read_only=True, data_only=True)
        except Exception:
            continue
        for ws in wb.worksheets:
            rows = ws.iter_rows(values_only=True)
            header = [str(h).strip() if h else "" for h in next(rows, ())]
            for values in rows:
                row = dict(zip(header, values))
                if listed is not None:
                    d = domain_of(str(row.get("Website") or ""))
                    if d:
                        listed.setdefault(sheet.name, set()).add(d)
                status = str(row.get("Status") or "")
                if not OBJECTION.search(status):
                    continue
                reason = f"{status} (in {sheet.name})"
                block.add("website", domain_of(str(row.get("Website") or "")) or "", reason)
                block.add("email", str(row.get("Email") or ""), reason)
                block.add("name", str(row.get("Business") or ""), reason)
        wb.close()
    return block


def add_to_blocklist(outreach: Path, entries: list[tuple[str, str]], reason: str) -> int:
    """Adds (kind, value) pairs to do-not-contact.csv. Returns how many were new."""
    path = outreach / "do-not-contact.csv"
    existing: list[dict] = []
    if path.exists():
        with path.open(encoding="utf-8") as f:
            existing = list(csv.DictReader(f))
    have = {(r.get("kind"), (r.get("value") or "").lower()) for r in existing}
    added = 0
    now = datetime.now(timezone.utc).date().isoformat()
    for kind, value in entries:
        value = (value or "").strip()
        if value and (kind, value.lower()) not in have:
            existing.append({"value": value, "kind": kind, "reason": reason, "added": now})
            have.add((kind, value.lower()))
            added += 1
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=BLOCK_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(existing)
    return added


class Claims:
    """website -> the sheet that first pushed it."""

    def __init__(self, outreach: Path, listed: dict[str, set[str]] | None = None) -> None:
        self.path = outreach / "claims.csv"
        self.outreach = outreach
        self.listed = listed  # sheet -> websites it lists now; a claim lapses once the row is gone
        self.owner: dict[str, str] = {}
        if self.path.exists():
            with self.path.open(encoding="utf-8") as f:
                self.owner = {r["website"]: r["sheet"] for r in csv.DictReader(f) if r.get("website") and r.get("sheet")}

    def other_owner(self, domain: str, sheet: str) -> str | None:
        """The other, still-existing sheet that already has this firm - or None if it's this sheet's."""
        owner = self.owner.get(domain)
        if not owner or owner == sheet or not (self.outreach / owner).exists():
            return None
        if self.listed is not None and domain not in self.listed.get(owner, set()):
            return None  # deleted from that sheet since: no longer theirs
        return owner

    def claim(self, domains: list[str], sheet: str) -> None:
        changed = False
        for d in domains:
            if self.other_owner(d, sheet) is None and self.owner.get(d) != sheet:
                self.owner[d] = sheet
                changed = True
        if changed:
            with self.path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["website", "sheet"])
                writer.writeheader()
                writer.writerows({"website": w, "sheet": s} for w, s in sorted(self.owner.items()))
