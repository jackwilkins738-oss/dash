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
SENT_FIELDS = ["email", "business", "preview_url", "batch", "sent", "followup_sent", "message_id", "subject", "variant",
               "sent_from", "sent_at", "final_sent"]
FOLLOWUP_AFTER_DAYS = 5
# The last, closing-the-file email: this long after the follow-up (about two weeks after the first
# email), to anyone still silent who never opened their preview and was never rung. Never a fourth.
FINAL_AFTER_DAYS = 9
# Someone who opened their preview is a call, not an email - but if no call is logged this long after
# the first email, they get the one follow-up after all, so a warm firm is never simply forgotten.
VIEWER_FOLLOWUP_DAYS = 10


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
    # Inbound leads asked to hear from you: answered personally, never in a cold batch.
    files = [p for p in outreach.glob("mailmeteor*.csv") if not p.name.startswith("mailmeteor-batch") and p.name != "mailmeteor-inbound.csv"]
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


def block_optouts(outreach: Path, views: dict[str, dict] | None) -> int:
    """Anyone who pressed "not for us" on their preview (the dashboard marks them lost) goes on
    do-not-contact, so no batch, follow-up or call list picks them again. Returns how many were new."""
    if not views:
        return 0
    from contact_rules import add_to_blocklist

    lost = {slug for slug, v in views.items() if (v or {}).get("status") == "lost"}
    if not lost:
        return 0
    entries: list[tuple[str, str]] = []
    for path in [*sources(outreach, None), outreach / SENT]:
        for r in _rows(path)[1]:
            if _slug(r.get("preview_url", "")) in lost:
                entries += [("email", r.get("email") or ""), ("name", r.get("business") or "")]
    return add_to_blocklist(outreach, entries, "not for us (preview page)") if entries else 0


def remaining(outreach: Path, sheet: str | None = None) -> int:
    done = {**sent_emails(outreach), **do_not_email(outreach)}
    seen: set[str] = set()
    for src in sources(outreach, sheet):
        for r in _rows(src)[1]:
            e = (r.get("email") or "").lower()
            if e and e not in done:
                seen.add(e)
    return len(seen)


def list_status(outreach: Path, sheet: str) -> dict:
    """For one list, why its Mailmeteor file has the firms it has - so "I can't see it" has an answer.
    Counts only: no prospect's details leave this function."""
    stem = Path(sheet).stem
    suffix = "" if stem == "outreach-master" else f"-{stem}"
    mm, links = outreach / f"mailmeteor{suffix}.csv", outreach / f"preview-links{suffix}.csv"
    out = {"file": mm.name, "exists": mm.exists(), "in_file": 0, "waiting": 0, "done": 0, "letters": 0, "not_live": 0}
    emails = {(r.get("email") or "").lower() for r in _rows(mm)[1] if r.get("email")}
    done = {**sent_emails(outreach), **do_not_email(outreach)}
    out["in_file"] = len(emails)
    out["done"] = sum(1 for e in emails if e in done)
    out["waiting"] = out["in_file"] - out["done"]
    by_channel = [((r.get("Channel") or "").lower(), (r.get("Email") or "").lower()) for r in _rows(links)[1]]
    out["letters"] = sum(1 for c, _ in by_channel if c != "email")
    out["not_live"] = sum(1 for c, e in by_channel if c == "email" and e and e not in emails)
    return out


RECHECK_AFTER_DAYS = 30


def verified(outreach: Path, verify, today: date):
    """email -> (ok, result): the saved check if it's recent, else a fresh one (saved), so every batch
    only holds addresses that can take mail. Mailmeteor sends without the panel's own safeguards, so
    this is where bounces are stopped - each one costs the sending domain's reputation."""
    from datetime import datetime, timedelta, timezone

    from email_check import is_bad

    path = outreach / "email-checks.csv"
    fields, rows = _rows(path)
    fields = fields or ["email", "result", "checked_at"]
    saved = {(r.get("email") or "").lower(): r for r in rows}
    cache: dict[str, str] = {}
    changed = [False]

    def look(email: str) -> tuple[bool, str]:
        e = email.lower()
        row = saved.get(e)
        if row:
            try:
                fresh = today - datetime.fromisoformat(row.get("checked_at", "")).date() < timedelta(days=RECHECK_AFTER_DAYS)
            except ValueError:
                fresh = False
            if fresh or row.get("result") == "bounced":
                return not is_bad(row.get("result", "")), row.get("result", "")
        result = verify(e, cache)
        if result != "unknown":
            saved[e] = {**(row or {}), "email": e, "result": result, "checked_at": datetime.now(timezone.utc).isoformat()}
            changed[0] = True
        return not is_bad(result), result

    def save() -> None:
        if changed[0]:
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
                writer.writeheader()
                writer.writerows(saved.values())

    return look, save


def _ratings(outreach: Path) -> dict:
    import json

    try:
        return json.loads((outreach / "google-ratings.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def need(row: dict, ratings: dict) -> float:
    """How much this firm needs the email first: a slow site (unknown counts as middling), plus a busy
    firm on Google (4.5+ stars and plenty of reviews - it gets work and can pay for a site)."""
    try:
        score = float(row.get("mobile_score") or "")
    except ValueError:
        score = 50.0
    google = ((ratings.get(row.get("website") or "") or {}).get("google")) or {}
    reviews, rating = int(google.get("reviews") or 0), float(google.get("rating") or 0)
    busy = 30 if rating >= 4.5 and reviews >= 20 else 15 if reviews >= 10 else 0
    return (100 - score) + busy


def make_batch(outreach: Path, size: int, sheet: str | None = None, check=None, today: date | None = None,
               verify=None) -> tuple[Path | None, list[str]]:
    """(batch file, notes). check(url) -> None if the link loads, else why not. verify(email, cache) ->
    an email_check result (None skips address checks - the tests' default)."""
    if check is None:
        from push_prospects import link_loads as check
    today = today or date.today()
    done = sent_emails(outreach)
    stop = do_not_email(outreach)
    look, save = verified(outreach, verify, today) if verify else (None, lambda: None)
    picked, fields, notes, seen, waiting = [], [], [], set(), []
    for src in sources(outreach, sheet):
        src_fields, rows = _rows(src)
        fields = list(dict.fromkeys([*fields, *src_fields]))
        for r in rows:
            email = (r.get("email") or "").strip().lower()
            if not email or email in done or email in seen:
                continue
            seen.add(email)
            if email in stop:
                notes.append(f"skipped {r.get('business')}: {stop[email]}")
                continue
            waiting.append({**r, "_source": src.name})
    # Neediest first: the slowest sites, and among them the firms Google shows are busiest.
    ratings = _ratings(outreach)
    waiting.sort(key=lambda r: -need(r, ratings))
    for r in waiting:
        if len(picked) >= size:
            break
        email = (r.get("email") or "").strip().lower()
        if look:
            ok, result = look(email)
            if not ok:
                notes.append(f"skipped {r.get('business')}: {email} can't take mail ({result}) - they'll get a letter instead")
                continue
        why = check(r.get("preview_url") or "")
        if why:
            notes.append(f"skipped {r.get('business')}: link {why}")
            continue
        picked.append(r)
    save()
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
                variant: str = "", sent_from: str = "", sent_at: str | None = None) -> None:
    """One email just sent from the panel (send_email.py) - recorded straight away, with the time (HH:MM)
    so the scorecard can tell whether early sends get more replies."""
    from datetime import datetime

    sent_at = datetime.now().strftime("%H:%M") if sent_at is None else sent_at
    rows = _rows(outreach / SENT)[1]
    email = row["email"].strip().lower()
    if any((r.get("email") or "").lower() == email for r in rows):
        return
    rows.append({"email": email, "business": row.get("business", ""), "preview_url": row.get("preview_url", ""),
                 "batch": batch, "sent": today.isoformat(), "message_id": message_id, "subject": subject,
                 "variant": variant, "sent_from": sent_from, "sent_at": sent_at})
    _write_sent(outreach, rows)


def record_followup_sent(outreach: Path, email: str, today: date, final: bool = False) -> None:
    col = "final_sent" if final else "followup_sent"
    rows = _rows(outreach / SENT)[1]
    for r in rows:
        if (r.get("email") or "").lower() == email.lower() and not r.get(col):
            r[col] = today.isoformat()
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
    """Emailed, long enough ago, and no sign of life - (rows to follow up, why others were left out).

    One follow-up ("stage": "followup"), then one closing email ("stage": "final") FINAL_AFTER_DAYS
    after it - never more. Left out: anyone who replied (in any way), bounced or said no. Anyone who
    opened their preview is on the Calls list - a call beats a second email - so they wait
    VIEWER_FOLLOWUP_DAYS, and are left out for good once a call is logged; they never get the closing
    email at all."""
    from datetime import timedelta

    today = today or date.today()
    stop = do_not_email(outreach)
    from reply_scanner import back_on

    replied_emails, replied_names, away = set(), set(), {}
    for r in _rows(outreach / "replies.csv")[1]:
        if r.get("kind") != "out of office":
            replied_emails.add((r.get("from") or "").lower())
            replied_names.add((r.get("business") or "").lower())
            continue
        try:  # an out-of-office: no follow-up until they're back (and a day to catch up)
            received = date.fromisoformat((r.get("date") or "")[:10])
        except ValueError:
            continue
        until = back_on(r.get("message") or r.get("snippet") or "", received)
        who = (r.get("from") or "").lower()
        away[who] = max(away.get(who, until), until)
    latest: dict[str, dict] = {}
    for src in sources(outreach, None):
        for r in _rows(src)[1]:
            if r.get("email"):
                latest[r["email"].strip().lower()] = r
    called = set()
    calls_path = outreach / "calls.csv"
    if calls_path.exists():
        with calls_path.open(encoding="utf-8") as f:
            called = {(r.get("business") or "").strip().lower() for r in csv.DictReader(f)}
    out, skipped = [], {"replied": 0, "viewed": 0, "blocked": 0, "too soon": 0}
    for r in _rows(outreach / SENT)[1]:
        email = (r.get("email") or "").lower()
        if not email or r.get("final_sent"):
            continue
        if email in away and today <= away[email]:
            skipped["too soon"] += 1  # away - their follow-up waits until they're back
            continue
        if r.get("followup_sent"):
            try:
                followed = date.fromisoformat(r["followup_sent"][:10])
            except ValueError:
                continue
            viewed = views is not None and ((views.get(_slug(r.get("preview_url", ""))) or {}).get("view_count") or 0) > 0
            if followed > today - timedelta(days=FINAL_AFTER_DAYS):
                skipped["too soon"] += 1
            elif email in stop:
                skipped["blocked"] += 1
            elif email in replied_emails or (r.get("business") or "").lower() in replied_names:
                skipped["replied"] += 1
            elif viewed or (r.get("business") or "").strip().lower() in called:
                skipped["viewed"] += 1
            elif views is not None:  # without the dashboard's views, a viewer can't be told apart: no closing email
                out.append({**r, **latest.get(email, {}), "email": email, "stage": "final"})
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
        elif views is not None and ((views.get(_slug(r.get("preview_url", ""))) or {}).get("view_count") or 0) > 0 and (
            (r.get("business") or "").strip().lower() in called or sent > today - timedelta(days=VIEWER_FOLLOWUP_DAYS)
        ):
            skipped["viewed"] += 1
        else:
            out.append({**r, **latest.get(email, {}), "email": email, "stage": "followup"})
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
    fields = [f for f in dict.fromkeys(k for r in picked for k in r) if f not in ("batch", "sent", "followup_sent", "final_sent")]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(picked)
    with (outreach / FOLLOWUP_PENDING).open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "batch", "stage"])
        writer.writeheader()
        writer.writerows({"email": r["email"], "batch": path.name, "stage": r.get("stage", "followup")} for r in picked)
    return path, notes, skipped


def mark_followups_sent(outreach: Path, today: date | None = None) -> int:
    today = today or date.today()
    pending = {r["email"].lower(): r.get("stage") or "followup" for r in _rows(outreach / FOLLOWUP_PENDING)[1] if r.get("email")}
    if not pending:
        return 0
    rows = _rows(outreach / SENT)[1]
    n = 0
    for r in rows:
        stage = pending.get((r.get("email") or "").lower())
        col = "final_sent" if stage == "final" else "followup_sent"
        if stage and not r.get(col):
            r[col] = today.isoformat()
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
        views = preview_views()
        if block_optouts(outreach, views):
            print("  Some firms said 'not for us' on their preview - they're on do-not-contact now.")
        path, notes, skipped = make_followups(outreach, args.size, args.after_days, views=views)
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
          "and checking each address and link ...", flush=True)
    if block_optouts(outreach, preview_views()):
        print("  Some firms said 'not for us' on their preview - they're on do-not-contact now.")
    from email_check import check as verify_email

    path, notes = make_batch(outreach, args.size, args.sheet, verify=verify_email)
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
