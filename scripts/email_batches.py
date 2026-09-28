"""Send in small daily batches: the next N firms not yet emailed, ready for Mailmeteor.

    python scripts/email_batches.py --size 20 [--sheet NAME]     make a batch
    python scripts/email_batches.py --mark-sent                  after sending it

A batch is taken from the Mailmeteor files the other buttons write (so every
firm in it is email-eligible, not blocked, and its preview page exists), oldest
list first, skipping anyone in outreach/emails-sent.csv. Each link is checked
again before it goes in; one that doesn't load is skipped and the next firm
takes its place. Writes outreach/mailmeteor-batch-<date>.csv - import that.

Small batches keep a sending account out of spam folders: a new account that
suddenly emails hundreds of strangers looks like a spammer. 20-30 a day, rising
slowly, is the usual advice.
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PENDING = "mailmeteor-batch-pending.csv"
SENT = "emails-sent.csv"


def outreach_dir() -> Path:
    for parent in [HERE.parent, *HERE.parents]:
        if (parent / "outreach").is_dir():
            return parent / "outreach"
    return HERE.parent / "outreach"


def _rows(path: Path) -> tuple[list[str], list[dict]]:
    if not path.exists():
        return [], []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames or []), list(reader)


def sent_emails(outreach: Path) -> dict[str, str]:
    return {r["email"].lower(): r.get("sent", "") for r in _rows(outreach / SENT)[1] if r.get("email")}


def sources(outreach: Path, sheet: str | None) -> list[Path]:
    """The Mailmeteor files to draw from, oldest list first."""
    if sheet:
        stem = Path(sheet).stem
        path = outreach / ("mailmeteor.csv" if stem == "outreach-master" else f"mailmeteor-{stem}.csv")
        return [path] if path.exists() else []
    files = [p for p in outreach.glob("mailmeteor*.csv") if not p.name.startswith("mailmeteor-batch")]
    return sorted(files, key=lambda p: p.stat().st_mtime)


def remaining(outreach: Path, sheet: str | None = None) -> int:
    done = sent_emails(outreach)
    seen: set[str] = set()
    for src in sources(outreach, sheet):
        for r in _rows(src)[1]:
            e = (r.get("email") or "").lower()
            if e and e not in done:
                seen.add(e)
    return len(seen)


def make_batch(outreach: Path, size: int, sheet: str | None = None, check=None, today: date | None = None) -> tuple[Path | None, list[str]]:
    """(batch file, notes). check(url) -> None if the link loads, else why not."""
    if check is None:
        from push_prospects import link_loads as check
    today = today or date.today()
    done = sent_emails(outreach)
    picked, fields, notes, seen = [], [], [], set()
    for src in sources(outreach, sheet):
        src_fields, rows = _rows(src)
        for r in rows:
            email = (r.get("email") or "").strip().lower()
            if not email or email in done or email in seen:
                continue
            seen.add(email)
            why = check(r.get("preview_url") or "")
            if why:
                notes.append(f"skipped {r.get('business')}: link {why}")
                continue
            fields = fields or src_fields
            picked.append({**r, "_source": src.name})
            if len(picked) >= size:
                break
        if len(picked) >= size:
            break
    if not picked:
        return None, notes
    path = outreach / f"mailmeteor-batch-{today.isoformat()}.csv"
    n = 2
    while path.exists():
        path = outreach / f"mailmeteor-batch-{today.isoformat()}-{n}.csv"
        n += 1
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(picked)
    with (outreach / PENDING).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "business", "preview_url", "batch"])
        writer.writeheader()
        writer.writerows({"email": r["email"].strip().lower(), "business": r.get("business", ""),
                          "preview_url": r.get("preview_url", ""), "batch": path.name} for r in picked)
    return path, notes


def mark_sent(outreach: Path, today: date | None = None) -> int:
    today = today or date.today()
    pending = _rows(outreach / PENDING)[1]
    if not pending:
        return 0
    sent_path = outreach / SENT
    existing = _rows(sent_path)[1]
    have = {r["email"].lower() for r in existing if r.get("email")}
    new = [{"email": r["email"], "business": r.get("business", ""), "preview_url": r.get("preview_url", ""),
            "batch": r.get("batch", ""), "sent": today.isoformat()} for r in pending if r["email"].lower() not in have]
    with sent_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "business", "preview_url", "batch", "sent"], extrasaction="ignore")
        writer.writeheader()
        writer.writerows(existing + new)
    (outreach / PENDING).unlink()
    return len(new)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=20)
    ap.add_argument("--sheet", default=None, help="only this list (default: every list, oldest first)")
    ap.add_argument("--mark-sent", action="store_true")
    args = ap.parse_args()
    outreach = outreach_dir()
    if args.mark_sent:
        n = mark_sent(outreach)
        print(f"Marked {n} emailed today - they won't be in a batch again." if n else "No batch waiting to be marked.")
        return
    if not 1 <= args.size <= 500:
        sys.exit("Batch size must be 1-500.")
    pending = _rows(outreach / PENDING)[1]
    if pending:
        print(f"Note: the last batch ({pending[0].get('batch')}) was never marked as sent - it's being replaced.")
    print(f"Picking the next {args.size} firms not yet emailed{' from ' + args.sheet if args.sheet else ' from every list'}, "
          "and checking each link ...", flush=True)
    path, notes = make_batch(outreach, args.size, args.sheet)
    for n in notes[:10]:
        print(f"  {n}")
    if not path:
        sys.exit("Nobody left to email - every firm in the Mailmeteor files has been sent to. Prepare a new list.")
    count = len(_rows(path)[1])
    left = remaining(outreach, args.sheet) - count
    print(f"READY: {path.name} - {count} firms, every link checked. Import it into Mailmeteor, send, then press Mark batch as sent.")
    print(f"  {max(left, 0)} more waiting after this batch.")


if __name__ == "__main__":
    main()
