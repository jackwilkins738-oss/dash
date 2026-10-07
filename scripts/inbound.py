"""Inbound leads: tradespeople who asked for their website report on the free speed test.

The website sends you a Telegram alert with "Add to pipeline" (app/api/website-check). Tapping it, the
panel's bot reads the alert's lines (Business:, Email:, Website: ...) and adds the firm here:

    outreach/inbound.xlsx    one row per firm (Source: Website check), built by Run the whole list like
                             any list - so their preview page is made and speed-checked.

They asked to hear from you, so they're answered personally (the bot offers an AI draft with their
preview link), never in a cold batch: mailmeteor-inbound.csv is left out of Make batch.
"""

from __future__ import annotations

import re
from pathlib import Path

SHEET = "inbound.xlsx"
SOURCE = "Website check"
LABELS = {"Business": "business", "Name": "name", "Email": "email", "Phone": "phone", "Website": "website",
          "Trade": "trade", "Town": "town", "Score": "score"}


def parse(text: str) -> dict | None:
    """The lead from the website's alert, or None if it isn't one."""
    lead: dict[str, str] = {}
    for line in (text or "").splitlines():
        label, sep, value = line.partition(": ")
        key = LABELS.get(label.strip())
        if sep and key and key not in lead:  # first one wins - the website never repeats a label
            lead[key] = value.strip()
    if not (lead.get("business") and lead.get("website") and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", lead.get("email", ""))):
        return None
    m = re.match(r"(\d{1,3})/100", lead.get("score", ""))
    lead["score"] = m.group(1) if m else ""
    return lead


def safe(value: str) -> str:
    """No spreadsheet formulas from a web form."""
    value = (value or "").strip()
    return "'" + value if value[:1] in ("=", "+", "-", "@") else value


def add(outreach: Path, lead: dict, sheet: str = SHEET, source: str = SOURCE, found: str = "they gave it") -> tuple[str, str]:
    """("added" | "already" | "known:<list>", message) - adds them to inbound.xlsx (or `sheet`) unless they're
    already in a list."""
    import openpyxl

    from find_prospects import HEADERS
    from push_prospects import domain_of

    domain = domain_of(lead["website"]) or ""
    if not domain:
        return "bad", "Their website address doesn't look right - add them by hand."
    path = outreach / sheet
    for other in sorted(outreach.glob("*.xlsx")):
        if other.name in (sheet, "outreach-results.xlsx") or other.name.startswith("~$") or other.name.endswith(".tmp.xlsx"):
            continue
        try:
            wb = openpyxl.load_workbook(other, read_only=True, data_only=True)
        except Exception:  # noqa: BLE001 - an odd file never blocks a lead
            continue
        try:
            for ws in wb.worksheets:
                rows = ws.iter_rows(values_only=True)
                header = [str(h).strip() if h else "" for h in next(rows, ())]
                if "Website" not in header:
                    continue
                i = header.index("Website")
                if any(domain_of(str(r[i] or "")) == domain for r in rows if i < len(r)):
                    return f"known:{other.name}", f"{lead['business']} is already in {other.name} - their preview is built from there (see Calls)."
        finally:
            wb.close()
    headers = HEADERS + ["Source", "Their score"]
    if path.exists():
        wb = openpyxl.load_workbook(path)
        ws = wb["Outreach"]
        headers = [str(c.value or "") for c in ws[1]]
        site_col = headers.index("Website")
        if any(domain_of(str(r[site_col] or "")) == domain for r in ws.iter_rows(min_row=2, values_only=True)):
            return "already", f"{lead['business']} is already in {sheet}."
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Outreach"
        ws.append(headers)
    row = {"Business": lead["business"], "Website": lead["website"], "Status": "New", "Trade": lead.get("trade", ""),
           "Area": lead.get("town", ""), "Email": lead.get("email", ""), "Phone": lead.get("phone", ""),
           "Contact name": lead.get("name", ""), "Website found": found, "Source": source,
           "Their score": lead.get("score", "")}
    ws.append([safe(str(row.get(h, ""))) for h in headers])
    tmp = path.with_suffix(".tmp.xlsx")
    wb.save(tmp)
    tmp.replace(path)
    return "added", f"{lead['business']} added to {sheet}."
