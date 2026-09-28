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
FOLLOWUP_PENDING = "mailmeteor-followup-pending.csv"
SENT = "emails-sent.csv"
SENT_FIELDS = ["email", "business", "preview_url", "batch", "sent", "followup_sent", "message_id", "subject", "variant"]
FOLLOWUP_AFTER_DAYS = 5


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


def do_not_email(outreach: Path) -> dict[str, str]:
    """email -> why not: said no (do-not-contact) or bounced - even if an older Mailmeteor file still lists them."""
    out: dict[str, str] = {}
    for r in _rows(outreach / "email-checks.csv")[1]:
        if (r.get("result") or "") == "bounced" and r.get("email"):
            out[r["email"].lower()] = "bounced"
    for r in _rows(outreach / "do-not-contact.csv")[1]:
        if r.get("kind") == "email" and r.get("value"):
            out[r["value"].strip().lower()] = r.get("reason") or "do not contact"
    return out


def remaining(outreach: Path, sheet: str | None = None) -> int:
    done = {**sent_emails(outreach), **do_not_email(outreach)}
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
    stop = do_not_email(outreach)
    picked, fields, notes, seen = [], [], [], set()
    for src in sources(outreach, sheet):
        src_fields, rows = _rows(src)
        for r in rows:
            email = (r.get("email") or "").strip().lower()
            if not email or email in done or email in seen:
                continue
            seen.add(email)
            if email in stop:
                notes.append(f"skipped {r.get('business')}: {stop[email]}")
                continue
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
        writer = csv.DictWriter(f, fieldnames=SENT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(existing + new)
    (outreach / PENDING).unlink()
    return len(new)


def _write_sent(outreach: Path, rows: list[dict]) -> None:
    tmp = outreach / (SENT + ".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SENT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(outreach / SENT)  # never a half-written file, even if the run is stopped mid-write


def record_sent(outreach: Path, row: dict, batch: str, today: date, message_id: str = "", subject: str = "",
                variant: str = "") -> None:
    """One email just sent from the panel (send_email.py) - recorded straight away."""
    rows = _rows(outreach / SENT)[1]
    email = row["email"].strip().lower()
    if any((r.get("email") or "").lower() == email for r in rows):
        return
    rows.append({"email": email, "business": row.get("business", ""), "preview_url": row.get("preview_url", ""),
                 "batch": batch, "sent": today.isoformat(), "message_id": message_id, "subject": subject,
                 "variant": variant})
    _write_sent(outreach, rows)


def record_followup_sent(outreach: Path, email: str, today: date) -> None:
    rows = _rows(outreach / SENT)[1]
    for r in rows:
        if (r.get("email") or "").lower() == email.lower() and not r.get("followup_sent"):
            r["followup_sent"] = today.isoformat()
    _write_sent(outreach, rows)


def record_bounce(outreach: Path, email: str) -> None:
    """An address the mail server refused outright: bounced, so it gets a letter instead."""
    from datetime import datetime, timezone

    path = outreach / "email-checks.csv"
    fields, rows = _rows(path)
    fields = fields or ["email", "result", "checked_at"]
    by_email = {(r.get("email") or "").lower(): r for r in rows}
    by_email[email.lower()] = {**by_email.get(email.lower(), {}), "email": email.lower(), "result": "bounced",
                               "checked_at": datetime.now(timezone.utc).isoformat()}
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(by_email.values())


# ---------------------------------------------------------------- follow-ups


def _slug(url: str) -> str:
    import re

    m = re.search(r"/for/([a-z0-9-]+)", url or "")
    return m.group(1) if m else ""


def followup_candidates(outreach: Path, after_days: int = FOLLOWUP_AFTER_DAYS, today: date | None = None,
                        views: dict[str, dict] | None = None) -> tuple[list[dict], dict[str, int]]:
    """Emailed once, long enough ago, and no sign of life - (rows to follow up, why others were left out).

    Only ever one follow-up. Left out: anyone who replied (in any way), bounced, said no, or opened their
    preview (they're on the Calls list - a call beats a second email)."""
    from datetime import timedelta

    today = today or date.today()
    stop = do_not_email(outreach)
    replied_emails, replied_names = set(), set()
    for r in _rows(outreach / "replies.csv")[1]:
        if r.get("kind") != "out of office":
            replied_emails.add((r.get("from") or "").lower())
            replied_names.add((r.get("business") or "").lower())
    latest: dict[str, dict] = {}
    for src in sources(outreach, None):
        for r in _rows(src)[1]:
            if r.get("email"):
                latest[r["email"].strip().lower()] = r
    out, skipped = [], {"replied": 0, "viewed": 0, "blocked": 0, "too soon": 0}
    for r in _rows(outreach / SENT)[1]:
        email = (r.get("email") or "").lower()
        if not email or r.get("followup_sent"):
            continue
        try:
            sent = date.fromisoformat(r.get("sent") or "")
        except ValueError:
            continue
        if sent > today - timedelta(days=after_days):
            skipped["too soon"] += 1
        elif email in stop:
            skipped["blocked"] += 1
        elif email in replied_emails or (r.get("business") or "").lower() in replied_names:
            skipped["replied"] += 1
        elif views is not None and ((views.get(_slug(r.get("preview_url", ""))) or {}).get("view_count") or 0) > 0:
            skipped["viewed"] += 1
        else:
            out.append({**r, **latest.get(email, {}), "email": email})
    out.sort(key=lambda r: r.get("sent") or "")
    return out, skipped


def make_followups(outreach: Path, size: int, after_days: int = FOLLOWUP_AFTER_DAYS, check=None,
                   views: dict[str, dict] | None = None, today: date | None = None) -> tuple[Path | None, list[str], dict]:
    if check is None:
        from push_prospects import link_loads as check
    today = today or date.today()
    candidates, skipped = followup_candidates(outreach, after_days, today, views)
    picked, notes = [], []
    for r in candidates:
        why = check(r.get("preview_url") or "")
        if why:
            notes.append(f"skipped {r.get('business')}: link {why}")
            continue
        picked.append(r)
        if len(picked) >= size:
            break
    if not picked:
        return None, notes, skipped
    path = outreach / f"mailmeteor-followup-{today.isoformat()}.csv"
    n = 2
    while path.exists():
        path = outreach / f"mailmeteor-followup-{today.isoformat()}-{n}.csv"
        n += 1
    fields = [f for f in dict.fromkeys(k for r in picked for k in r) if f not in ("batch", "sent", "followup_sent")]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(picked)
    with (outreach / FOLLOWUP_PENDING).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "batch"])
        writer.writeheader()
        writer.writerows({"email": r["email"], "batch": path.name} for r in picked)
    return path, notes, skipped


def mark_followups_sent(outreach: Path, today: date | None = None) -> int:
    today = today or date.today()
    pending = {r["email"].lower() for r in _rows(outreach / FOLLOWUP_PENDING)[1] if r.get("email")}
    if not pending:
        return 0
    rows = _rows(outreach / SENT)[1]
    n = 0
    for r in rows:
        if (r.get("email") or "").lower() in pending and not r.get("followup_sent"):
            r["followup_sent"] = today.isoformat()
            n += 1
    with (outreach / SENT).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SENT_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    (outreach / FOLLOWUP_PENDING).unlink()
    return n


def preview_views() -> dict[str, dict] | None:
    """Who's opened their preview, from the dashboard - or None if it can't be asked (nothing is filtered then)."""
    import os

    try:
        from calls import DashboardMissing, fetch_activity

        return fetch_activity(os.environ.get("DASHBOARD_API_URL", "") or "https://admin.scalardigital.co.uk",
                              os.environ.get("PROSPECTS_API_SECRET", ""),
                              os.environ.get("SCALAR_TENANT_ID", "abdc6408-1fd5-4fb6-9c4c-53600b571a6d"))
    except DashboardMissing as e:
        print(f"  (couldn't ask the dashboard who opened their preview - {e} - so viewers aren't left out this time)")
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--size", type=int, default=20)
    ap.add_argument("--sheet", default=None, help="only this list (default: every list, oldest first)")
    ap.add_argument("--mark-sent", action="store_true")
    ap.add_argument("--followups", action="store_true", help="make a follow-up batch instead")
    ap.add_argument("--after-days", type=int, default=FOLLOWUP_AFTER_DAYS)
    ap.add_argument("--mark-followups-sent", action="store_true")
    args = ap.parse_args()
    outreach = outreach_dir()
    if args.mark_followups_sent:
        n = mark_followups_sent(outreach)
        print(f"Marked {n} follow-ups sent today - nobody gets a third email." if n else "No follow-up batch waiting to be marked.")
        return
    if args.followups:
        if not 1 <= args.size <= 500 or not 1 <= args.after_days <= 60:
            sys.exit("Size must be 1-500 and days 1-60.")
        print(f"Picking up to {args.size} firms emailed {args.after_days}+ days ago with no reply and no preview visit ...", flush=True)
        path, notes, skipped = make_followups(outreach, args.size, args.after_days, views=preview_views())
        for n in notes[:10]:
            print(f"  {n}")
        left_out = ", ".join(f"{v} {k}" for k, v in skipped.items() if v)
        if left_out:
            print(f"  Left out: {left_out}.")
        if not path:
            print("No follow-ups due today.")
            return
        count = len(_rows(path)[1])
        print(f"READY: {path.name} - {count} follow-ups, every link checked. Press Send follow-ups on the panel "
              "(or import it into Mailmeteor, send, then Mark follow-ups as sent).")
        return
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
    print(f"READY: {path.name} - {count} firms, every link checked. Press Send today's batch on the panel "
          "(or import it into Mailmeteor, send, then Mark batch as sent).")
    print(f"  {max(left, 0)} more waiting after this batch.")


if __name__ == "__main__":
    main()
