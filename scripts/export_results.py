"""Everything about every firm, from every list, in one Excel workbook that updates in place.

    python scripts/export_results.py          (the panel's "Export to Excel")

Writes outreach/outreach-results.xlsx - the same file every time:

  Results   one row per firm, grouped under the date it was first exported
            (newest first), each group headed "Saturday 27 September 2026 ·
            43 firms · roofing-guildford" with a blank row after it. Scores,
            emails, visits and calls refresh on every export; a firm keeps the
            date it first appeared, so groups never reshuffle. The Notes
            column is yours: whatever you type there is kept across exports.
  Summary   counts per list, and a dated log of every export.

Your list sheets are never changed - this only reads them (through
push_prospects.py, so the numbers match everything else) and the files
beside them. Close the workbook in Excel before exporting: Windows won't let
anything save over a file Excel has open.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS_NAME = "outreach-results.xlsx"

COLUMNS = [
    ("Added", 12), ("List", 26), ("Business", 30), ("Contact", 18), ("Email", 30), ("Phone", 15),
    ("Channel", 11), ("Company type", 13), ("Trade", 18), ("Area", 14), ("Website", 24), ("Mobile score", 8),
    ("Worst issue", 44), ("Preview link", 30), ("Preview live", 8), ("Visits", 7), ("Last visit", 12),
    ("Emailed", 12), ("Letter posted", 12), ("Last call", 14), ("Called on", 12), ("Status", 16), ("Notes", 40), ("Key", 10),
]


def outreach_dir() -> Path:
    for parent in [HERE.parent, *HERE.parents]:
        if (parent / "outreach").is_dir():
            return parent / "outreach"
    return HERE.parent / "outreach"


def list_sheets(outreach: Path) -> list[Path]:
    return sorted(
        p for p in outreach.glob("*.xlsx") if not p.name.startswith("~$") and p.name != RESULTS_NAME
    )


def firms_on(sheet: Path) -> list[dict]:
    """Every firm on one sheet, as push_prospects.py sees it (read-only, nothing sent)."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "firms.json"
        run = subprocess.run(
            [sys.executable, str(HERE / "push_prospects.py"), "--sheet", str(sheet), "--dry-run", "--export-json", str(out)],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )
        if not out.exists():
            last = (run.stdout + run.stderr).strip().splitlines()[-1:] or ["no output"]
            print(f"  {sheet.name}: skipped - {last[0]}")
            return []
        return json.loads(out.read_text(encoding="utf-8"))


def _csv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _date(value) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def existing_notes(path: Path) -> dict[str, str]:
    """Key -> Notes from the last export, so what you typed survives."""
    if not path.exists():
        return {}
    import openpyxl

    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    except Exception:
        return {}
    notes: dict[str, str] = {}
    if "Results" in wb.sheetnames:
        rows = wb["Results"].iter_rows(values_only=True)
        header = [str(h) if h else "" for h in next(rows, ())]
        if "Key" in header and "Notes" in header:
            k, n = header.index("Key"), header.index("Notes")
            for r in rows:
                if len(r) > max(k, n) and r[k] and r[n] not in (None, ""):
                    notes[str(r[k])] = str(r[n])
    history = []
    if "Summary" in wb.sheetnames:
        for r in wb["Summary"].iter_rows(values_only=True):
            if r and r[0] == "Export" and len(r) >= 3:
                history.append((r[1], r[2]))
    wb.close()
    notes["\x00history"] = json.dumps(history, default=str)
    return notes


def build(outreach: Path, today: date | None = None) -> tuple[list[dict], dict]:
    """(rows, per-list counts) across every list - and records first-seen dates."""
    today = today or date.today()
    index_path = outreach / "results-index.csv"
    first_seen = {r["key"]: r["added"] for r in _csv(index_path) if r.get("key")}
    posted = {r["key"]: r.get("posted") or "" for r in _csv(outreach / "letters-sent.csv") if r.get("key")}
    emailed = {r["email"].lower(): r.get("sent") or "" for r in _csv(outreach / "emails-sent.csv") if r.get("email")}
    calls: dict[str, dict] = {}
    for r in _csv(outreach / "calls.csv"):
        calls[r.get("key") or ""] = r  # the last one wins

    rows, counts = [], {}
    for sheet in list_sheets(outreach):
        firms = firms_on(sheet)
        c = counts.setdefault(sheet.name, {"firms": 0, "email": 0, "letter": 0, "live": 0, "visited": 0, "posted": 0, "called": 0})
        for f in firms:
            key = f"{sheet.name}|{f['key']}"
            first_seen.setdefault(key, today.isoformat())
            call = calls.get(f["key"]) or {}
            rows.append({**f, "_key": key, "_sheet": sheet.name, "_added": first_seen[key],
                         "_posted": posted.get(f["key"], ""), "_emailed": emailed.get((f.get("email") or "").lower(), ""), "_call": call.get("outcome", ""), "_call_at": call.get("at", "")})
            c["firms"] += 1
            c["email" if f["channel"] == "email" else "letter"] += 1
            c["live"] += 1 if f.get("live") else 0
            c["visited"] += 1 if (f.get("views") or 0) > 0 else 0
            c["posted"] += 1 if posted.get(f["key"]) else 0
            c["called"] += 1 if call else 0
    with index_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["key", "added"])
        writer.writeheader()
        writer.writerows({"key": k, "added": v} for k, v in sorted(first_seen.items()))
    return rows, counts


def write(path: Path, rows: list[dict], counts: dict, notes: dict[str, str], now: datetime | None = None) -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    now = now or datetime.now()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Results"
    names = [c for c, _ in COLUMNS]
    ws.append(names)
    head_fill = PatternFill("solid", fgColor="1F2937")
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = head_fill
        cell.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 20
    ws.freeze_panes = "D2"
    for i, (_, width) in enumerate(COLUMNS, 1):
        ws.column_dimensions[get_column_letter(i)].width = width
    ws.column_dimensions[get_column_letter(names.index("Key") + 1)].hidden = True

    group_fill = PatternFill("solid", fgColor="DBEAFE")
    group_font = Font(bold=True, size=12, color="1E3A8A")
    band = Border(top=Side(style="thin", color="93C5FD"))
    score_fills = {"poor": PatternFill("solid", fgColor="FECACA"), "mid": PatternFill("solid", fgColor="FDE68A"),
                   "good": PatternFill("solid", fgColor="BBF7D0")}
    link_font = Font(color="1D4ED8", underline="single")

    by_date: dict[str, list[dict]] = {}
    for r in rows:
        by_date.setdefault(r["_added"], []).append(r)
    for added in sorted(by_date, reverse=True):
        group = sorted(by_date[added], key=lambda r: (r["_sheet"], r["business"].lower()))
        d = date.fromisoformat(added)
        lists = sorted({r["_sheet"].removesuffix(".xlsx") for r in group})
        heading = f"{d.strftime('%A')} {d.day} {d.strftime('%B %Y')}  ·  {len(group)} firm{'s' if len(group) != 1 else ''}  ·  {', '.join(lists)}"
        ws.append([heading])
        row_no = ws.max_row
        ws.merge_cells(start_row=row_no, start_column=1, end_row=row_no, end_column=len(COLUMNS) - 1)
        cell = ws.cell(row_no, 1)
        cell.font, cell.fill, cell.alignment = group_font, group_fill, Alignment(vertical="center", indent=1)
        for col in range(1, len(COLUMNS)):
            ws.cell(row_no, col).fill = group_fill
            ws.cell(row_no, col).border = band
        ws.row_dimensions[row_no].height = 24
        for r in group:
            score = r.get("mobile_score")
            live = {True: "Yes", False: "Not yet", None: ""}[r.get("live")]
            ws.append([
                d, r["_sheet"].removesuffix(".xlsx"), r["business"], r.get("contact") or "", r.get("email") or "",
                r.get("phone") or "", r["channel"].capitalize(), r.get("company_type") or "", r.get("trade") or "",
                r.get("area") or "", r.get("website") or "", int(score) if score is not None else None,
                r.get("top_issue") or "", r.get("preview_url") or "", live, r.get("views") if r.get("views") is not None else None,
                _date(r.get("last_viewed")), _date(r.get("_emailed")), _date(r.get("_posted")), r.get("_call") or "", _date(r.get("_call_at")),
                r.get("status") or "", notes.get(r["_key"], ""), r["_key"],
            ])
            n = ws.max_row
            for col in ("Added", "Last visit", "Emailed", "Letter posted", "Called on"):
                ws.cell(n, names.index(col) + 1).number_format = "d mmm yyyy"
            if score is not None:
                band_name = "good" if score >= 90 else "mid" if score >= 50 else "poor"
                ws.cell(n, names.index("Mobile score") + 1).fill = score_fills[band_name]
            for col in ("Preview link", "Website"):
                c = ws.cell(n, names.index(col) + 1)
                if c.value:
                    c.hyperlink = c.value if str(c.value).startswith("http") else f"https://{c.value}"
                    c.font = link_font
            ws.cell(n, names.index("Worst issue") + 1).alignment = Alignment(wrap_text=False)
        ws.append([])  # the spacing between date groups

    # ---- Summary: per list, plus a dated log of every export
    sm = wb.create_sheet("Summary")
    sm.append(["List", "Firms", "Email", "Letter", "Previews live", "Visited", "Letters posted", "Called"])
    for cell in sm[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = head_fill
    total = {"firms": 0, "email": 0, "letter": 0, "live": 0, "visited": 0, "posted": 0, "called": 0}
    for name, c in sorted(counts.items()):
        sm.append([name.removesuffix(".xlsx"), c["firms"], c["email"], c["letter"], c["live"], c["visited"], c["posted"], c["called"]])
        for k in total:
            total[k] += c[k]
    sm.append(["All lists", total["firms"], total["email"], total["letter"], total["live"], total["visited"], total["posted"], total["called"]])
    for cell in sm[sm.max_row]:
        cell.font = Font(bold=True)
    sm.append([])
    sm.append(["Export history"])
    sm.cell(sm.max_row, 1).font = Font(bold=True, size=12)
    history = json.loads(notes.get("\x00history", "[]"))
    history.append([now.strftime("%Y-%m-%d %H:%M"), f"{total['firms']} firms, {total['visited']} visited, {total['called']} called"])
    for when, what in history[-200:]:
        sm.append(["Export", when, what])
    sm.column_dimensions["A"].width = 30
    for col in "BCDEFGH":
        sm.column_dimensions[col].width = 16

    # Save beside, then swap in: a failed save never leaves a half-written file.
    tmp = path.with_suffix(".tmp.xlsx")
    wb.save(tmp)
    os.replace(tmp, path)


def main() -> None:
    outreach = outreach_dir()
    path = outreach / RESULTS_NAME
    sheets = list_sheets(outreach)
    if not sheets:
        sys.exit("No lists in outreach/ yet.")
    print(f"Exporting {len(sheets)} list{'s' if len(sheets) != 1 else ''} to {RESULTS_NAME} ...", flush=True)
    notes = existing_notes(path)
    rows, counts = build(outreach)
    try:
        write(path, rows, counts, notes)
    except PermissionError:
        path.with_suffix(".tmp.xlsx").unlink(missing_ok=True)
        # Not a failure of the run - the lists, links and Mailmeteor files are all written already.
        print(f"Skipped: {RESULTS_NAME} is open in Excel, so it wasn't updated. Close it and press Export results "
              "(nothing was lost).")
        return
    added_today = sum(1 for r in rows if r["_added"] == date.today().isoformat())
    kept = sum(1 for r in rows if notes.get(r["_key"]))
    print(f"Wrote {RESULTS_NAME}: {len(rows)} firms across {len(counts)} lists, {added_today} added today"
          + (f", {kept} notes kept" if kept else "") + ".")


if __name__ == "__main__":
    main()
