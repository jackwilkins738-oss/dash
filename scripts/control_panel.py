"""A local control panel for the prospect pipeline, instead of pasting PowerShell.

Double-click scripts/control_panel.bat (or run `python scripts/control_panel.py`)
and it opens http://127.0.0.1:8765 in your browser. Every button runs
push_prospects.py with the right options and streams its output onto the page;
"Run the whole list" chains them: email checks, company types and trades for
everyone, then speed checks 10 at a time until the list is done.

Everything stays on this machine, same as before: it only listens on
127.0.0.1, reads the sheet from outreach/, and keeps your keys in
outreach/panel.env (outreach/ is gitignored). Enter them once in the panel's
Settings and they're used for every run - no more $env: lines.

Options:
    --port N       default 8765
    --no-browser   don't open the browser on start
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import os
import secrets
import subprocess
import sys
import threading
import re
import time
import urllib.error
import urllib.request
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
PUSH = HERE / "push_prospects.py"
FIND = HERE / "find_prospects.py"
EXPORT = HERE / "export_results.py"
BATCHES = HERE / "email_batches.py"
REPLIES = HERE / "reply_scanner.py"
REPLY_WATCH = HERE / "reply_watch.py"
AUTOPILOT = HERE / "autopilot.py"
SEND = HERE / "send_email.py"
LAUNCH = HERE / "launch_report.py"
PUBLISH_SITE = HERE / "publish_site.py"
SITE_KIT = HERE / "site_kit.py"
SCORECARD = HERE / "scorecard.py"
GO_LIVE = HERE / "go_live.py"
CLIENT_SPEED = HERE / "client_speed.py"
BACKUP = HERE / "backup.py"
SENDING_HEALTH = HERE / "sending_health.py"
SITE_COPY = HERE / "site_copy.py"
SITE_QA = HERE / "site_qa.py"


def replies_first(settings: dict[str, str]) -> list:
    """Check replies before anything that picks who to contact - if the inbox is set up."""
    return [(REPLIES, [])] if settings.get("MAIL_ADDRESS") and settings.get("MAIL_APP_PASSWORD") else []
RESULTS_NAME = "outreach-results.xlsx"
SETTING_KEYS = [
    "PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    "LETTER_SIGNOFF", "LETTER_EMAIL", "LETTER_PHONE", "MAIL_ADDRESS", "MAIL_APP_PASSWORD", "MAIL_IMAP_HOST", "MAIL_FROM_NAME",
    "MAIL_EXTRA_1_ADDRESS", "MAIL_EXTRA_1_PASSWORD", "MAIL_EXTRA_2_ADDRESS", "MAIL_EXTRA_2_PASSWORD",
    "MAIL_EXTRA_3_ADDRESS", "MAIL_EXTRA_3_PASSWORD",
    "QUOTE_PRICE_BUILD", "QUOTE_PRICE_LANDING", "QUOTE_VAT_RATE", "QUOTE_DEPOSIT_PERCENT", "QUOTE_EXTRAS",
    "DASHBOARD_API_URL", "SITE_URL", "BOOKING_LINK", "CLOUDFLARE_API_TOKEN", "CLOUD_REPLY_ALERTS", "BACKUP_DIR",
    "ANTHROPIC_API_KEY", "AI_MODEL",
]
SECRET_KEYS = {"ANTHROPIC_API_KEY", "CLOUDFLARE_API_TOKEN", "PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "TELEGRAM_BOT_TOKEN", "MAIL_APP_PASSWORD",
               "MAIL_EXTRA_1_PASSWORD", "MAIL_EXTRA_2_PASSWORD", "MAIL_EXTRA_3_PASSWORD"}
# A run this long gets a phone alert when it ends (if Telegram is set up).
ALERT_AFTER_S = 180
RUN_ALL_BATCH = 10
# Shown in the header. Bump it with every change, so an old panel still running is obvious.
PANEL_VERSION = "61"
MAX_LOG_LINES = 5000


def outreach_dir() -> Path:
    # Same rule as push_prospects.py: this checkout, or the main one when run from a worktree.
    for parent in [HERE.parent, *HERE.parents]:
        if (parent / "outreach").is_dir():
            return parent / "outreach"
    return HERE.parent / "outreach"


OUTREACH = outreach_dir()
SETTINGS_FILE = OUTREACH / "panel.env"


# ---------------------------------------------------------------- mailmeteor

_MM_LOCK = threading.Lock()
_MM_LAST = [0.0]
MM_EVERY = 600  # seconds between Sent-folder checks while the panel is open


def _domain_warnings() -> list[str]:
    """The Scorecard's per-domain warnings (bouncing, or far fewer replies than the rest), for Today -
    so a domain going bad is seen the day it happens, not at the next Scorecard. Only your own sending
    domains and counts, never a prospect."""
    import scorecard

    try:
        lines = scorecard.domains(scorecard.gather(OUTREACH, None)) if OUTREACH.is_dir() else []
    except Exception:  # an odd CSV must never break the Today screen
        return []
    return [x.strip() for x in lines if any(w in x for w in ("STOP", "bounces are high", "under half"))]


def _reply_watch_last() -> dict | None:
    import reply_watch

    try:
        return reply_watch.last_check(OUTREACH)
    except OSError:
        return None


def _age_hours(stamp: str | None, now: datetime | None = None) -> float | None:
    """Hours since a 'YYYY-MM-DD HH:MM' stamp, or None if there isn't one."""
    if not stamp:
        return None
    try:
        return ((now or datetime.now()) - datetime.strptime(stamp[:16], "%Y-%m-%d %H:%M")).total_seconds() / 3600
    except ValueError:
        return None


def health(outreach: Path, settings: dict, now: datetime | None = None) -> list[dict]:
    """The things that can stop quietly, for the strip on Today: [{name, ok, text}]. ok is True, False,
    or None for 'not set up' - so a red dot means something that was working has stopped."""
    import backup

    out = []
    b = backup.last_backup(outreach)
    h = _age_hours(b, now)
    if h is None:
        out.append({"name": "Backup", "ok": False, "text": "never - set BACKUP_DIR in Settings and press Back up now"})
    else:
        out.append({"name": "Backup", "ok": h <= 48, "text": f"last {b[5:16].replace('-', '/', 1)}" + ("" if h <= 48 else " - over 2 days ago")})
    rw = _reply_watch_last()
    h = _age_hours(rw["at"] if rw else None, now)
    if h is None:
        out.append({"name": "Reply check", "ok": None, "text": "15-minute check is off"})
    else:
        out.append({"name": "Reply check", "ok": h <= 24 and not rw["line"].startswith(("The inbox refused", "Couldn't")),
                    "text": f"{rw['at'][11:16]} {rw['at'][8:10]}/{rw['at'][5:7]} - {rw['line'][:60]}"})
    try:
        import autopilot

        cfg = autopilot.load_config()
    except Exception:  # noqa: BLE001
        cfg = {}
    log = outreach / "autopilot-log.txt"
    if cfg.get("enabled"):
        ran = datetime.fromtimestamp(log.stat().st_mtime) if log.exists() else None
        hrs = ((now or datetime.now()) - ran).total_seconds() / 3600 if ran else None
        out.append({"name": "Autopilot", "ok": hrs is not None and hrs <= 30,
                    "text": (f"ran {ran:%H:%M %d/%m}" if ran else "hasn't run yet") + (", sends itself" if cfg.get("auto_send") else "")})
    else:
        out.append({"name": "Autopilot", "ok": None, "text": "off"})
    if not (settings.get("MAIL_ADDRESS") and settings.get("MAIL_APP_PASSWORD")):
        out.append({"name": "Inbox", "ok": False, "text": "no login in Settings - replies can't be checked"})
    import sending_health

    sh = sending_health.load(outreach)
    h = _age_hours(sh.get("checked_at", "").replace("T", " "), now)
    if h is None:
        out.append({"name": "Sending", "ok": None, "text": "not checked yet - press Check sending health"})
    elif sh.get("problems"):
        out.append({"name": "Sending", "ok": False, "text": sh["problems"][0][:90]})
    else:
        warn = len(sh.get("warnings") or [])
        out.append({"name": "Sending", "ok": h <= 72,
                    "text": ("clear" if not warn else f"working, {warn} to fix") + ("" if h <= 72 else " - not checked for 3 days")})
    return out


def _sync_mailmeteor_soon() -> None:
    """With a Mailmeteor batch waiting, check Sent in the background - at most every 10 minutes.

    The page asks for /api/batch every couple of minutes, so a batch Mailmeteor sends is ticked
    off (and counted in "Sent today") without anyone pressing Mark batch as sent.
    """
    import mailmeteor_sync

    if not OUTREACH.is_dir() or not mailmeteor_sync.waiting(OUTREACH) or time.time() - _MM_LAST[0] < MM_EVERY:
        return
    if JOB.running():
        return  # a send (or anything else) writing the log right now - check again next time
    if not _MM_LOCK.acquire(blocking=False):
        return
    _MM_LAST[0] = time.time()

    def run() -> None:
        try:
            import mail_accounts

            env = {**os.environ, **load_settings()}
            host = env.get("MAIL_IMAP_HOST", "").strip() or "imap.gmail.com"
            mailmeteor_sync.sync(OUTREACH, mail_accounts.accounts(env), host)
        except Exception:
            pass
        finally:
            _MM_LOCK.release()

    threading.Thread(target=run, daemon=True).start()


# ---------------------------------------------------------------- settings


def load_settings() -> dict[str, str]:
    values = {k: os.environ.get(k, "") for k in SETTING_KEYS}
    if SETTINGS_FILE.exists():
        for line in SETTINGS_FILE.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() in SETTING_KEYS and value.strip():
                values[key.strip()] = value.strip()
    return values


def save_settings(new: dict[str, str]) -> None:
    values = load_settings()
    for key in SETTING_KEYS:
        value = str(new.get(key, "")).strip()
        # A blank secret field means "keep what's saved" - the page never sees the saved value.
        if value or key not in SECRET_KEYS:
            values[key] = value
    if values.get("BOOKING_LINK") and not values["BOOKING_LINK"].startswith("https://"):
        values["BOOKING_LINK"] = ""  # only a real https link goes into emails
    if values.get("COMPANIES_HOUSE_API_KEY"):
        sys.path.insert(0, str(HERE))
        from company_lookup import clean_key

        values["COMPANIES_HOUSE_API_KEY"] = clean_key(values["COMPANIES_HOUSE_API_KEY"])
    OUTREACH.mkdir(exist_ok=True)
    SETTINGS_FILE.write_text("".join(f"{k}={values[k]}\n" for k in SETTING_KEYS if values[k]), encoding="utf-8")


# ---------------------------------------------------------------- sheets and progress


def sheets() -> list[str]:
    if not OUTREACH.is_dir():
        return []
    names = sorted(p.name for p in OUTREACH.glob("*.xlsx") if not p.name.startswith("~$") and p.name != RESULTS_NAME and not p.name.endswith(".tmp.xlsx"))
    # The master list first, as it's the default.
    return sorted(names, key=lambda n: n != "outreach-master.xlsx")


def latest_sheet() -> str:
    names = sheets()
    return max(names, key=lambda n: (OUTREACH / n).stat().st_mtime) if names else ""


def sheet_path(name: str) -> Path | None:
    return OUTREACH / name if name in sheets() else None


def progress(name: str) -> dict:
    """How far the speed check has got through a sheet: checked, couldn't check, still to do."""
    path = sheet_path(name)
    if not path:
        return {}
    log: dict[str, str] = {}
    log_path = OUTREACH / "teardown-log.csv"
    if log_path.exists():
        with log_path.open(encoding="utf-8") as f:
            log = {r["website"]: r.get("result") or "ok" for r in csv.DictReader(f)}
    try:
        sys.path.insert(0, str(HERE))
        import openpyxl  # noqa: F401 - push_prospects needs it too
        from contact_rules import Claims, load_blocklist
        from push_prospects import SKIP_STATUSES, domain_of
    except (ImportError, SystemExit):
        return {"error": "Needs openpyxl: python -m pip install openpyxl"}
    # The same rules push_prospects applies, so "still to do" can reach 0.
    listed: dict[str, set[str]] = {}
    blocklist = load_blocklist(OUTREACH, domain_of, listed)
    claims = Claims(OUTREACH, listed)
    try:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        rows = list(wb["Outreach"].iter_rows(values_only=True))
        wb.close()
    except Exception as e:  # a sheet open in Excel, or no Outreach tab
        return {"error": f"Couldn't read {name}: {e}"}
    closed: set[str] = set()
    lookups_path = OUTREACH / "company-lookups.csv"
    if lookups_path.exists():
        with lookups_path.open(encoding="utf-8") as f:
            closed = {r["website"] for r in csv.DictReader(f) if r.get("result") == "closed"}
    header = [str(h).strip() if h else "" for h in rows[0]] if rows else []
    domains = set()
    for values in rows[1:]:
        row = dict(zip(header, values))
        domain = domain_of(str(row.get("Website") or ""))
        if not (str(row.get("Business") or "").strip() and domain) or str(row.get("Status") or "") in SKIP_STATUSES:
            continue
        if blocklist.why(domain, str(row.get("Email") or ""), str(row.get("Business") or "")):
            continue
        if claims.other_owner(domain, name):
            continue
        # Dissolved firms are left out of every run (only when the sheet leaves the type blank).
        if domain in closed and not str(row.get("Company type") or "").strip():
            continue
        domains.add(domain)
    ok = sum(1 for d in domains if log.get(d) == "ok")
    failed = sum(1 for d in domains if log.get(d) == "failed")
    return {"total": len(domains), "checked": ok, "failed": failed, "remaining": len(domains) - ok - failed}


def output_files() -> list[dict]:
    if not OUTREACH.is_dir():
        return []
    files = [p for p in OUTREACH.glob("*.csv")]
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return [{"name": p.name, "modified": p.stat().st_mtime} for p in files]


# ---------------------------------------------------------------- jobs

# Every button maps to fixed push_prospects.py options - the page never sends a command line.
ACTIONS = {
    "find": "Find new prospects",
    "count": "Count matching firms",
    "all": "Run the whole list",
    "retry": "Retry failed speed checks",
    "links": "Refresh preview links + Mailmeteor CSV",
    "prepare": "Prepare Mailmeteor send",
    "export": "Export to Excel",
    "batch": "Make email batch",
    "replies": "Check replies",
    "reply_watch_on": "Turn on the 15-minute reply check",
    "reply_watch_off": "Turn off the 15-minute reply check",
    "followups": "Make follow-up batch",
    "followups_sent": "Mark follow-ups as sent",
    "autopilot_now": "Autopilot (run now)",
    "batch_sent": "Mark batch as sent",
    "send_batch": "Send today's batch",
    "send_followups": "Send follow-ups",
    "send_test": "Send a test to yourself",
    "launch_report": "Launch report",
    "dns_snapshot": "Save their DNS (before the switch)",
    "launch_check": "Check the launch",
    "client_speed": "Speed check client sites",
    "backup_now": "Back up now",
    "sending_health": "Check sending health",
    "write_copy": "Write site copy (AI)",
    "build_site": "Build site",
    "site_qa": "Check site (pre-launch QA)",
    "publish_site": "Publish site",
    "publish_preview": "Publish a preview for the client",
    "scorecard": "Scorecard",
    "speed": "Speed check the next batch",
    "one": "Check one firm",
    "contacts": "Find missing emails & phones",
    "emails": "Check emails",
    "companies": "Look up company types",
    "trades": "Guess missing trades",
    "push": "Push to dashboard",
    "letters": "Make letters",
    "install_segno": "Install segno (for letters)",
}


def run_all_steps(job: "Job", sheet: str, name: str, settings: dict[str, str]):
    """Everything the list needs, in order: the quick checks for everyone, then
    speed checks in batches - each batch pushed and logged, so stopping part-way
    loses nothing."""
    if not settings.get("PAGESPEED_API_KEY"):
        job.note("WARNING: no PAGESPEED_API_KEY in Settings - the speed checks can't run, so preview pages will")
        job.note("         show only each firm's name: no score, no 'What we found'. Add the key in Settings")
        job.note("         (the Google key the site's speed test uses) and run this again.")
        job.note("")
    yield from replies_first(settings)
    first = ["--sheet", sheet, "--find-contacts", "--check-emails", "--guess-trades"]
    if settings.get("COMPANIES_HOUSE_API_KEY"):
        first.append("--lookup-companies")
    else:
        job.note("No COMPANIES_HOUSE_API_KEY in Settings - skipping the company type lookup.")
    yield first
    if not settings.get("PAGESPEED_API_KEY"):
        job.note("Skipping the speed checks - no PAGESPEED_API_KEY (see the warning at the top).")
        yield ["--sheet", sheet, "--verify-links"]
        yield (EXPORT, [])
        return
    last = None
    while True:
        now = progress(name)
        remaining = now.get("remaining")
        if not remaining:
            # Last step: make sure every link in the Mailmeteor file actually loads.
            yield ["--sheet", sheet, "--verify-links"]
            yield (EXPORT, [])
            now = progress(name)
            failed = now.get("failed") or 0
            job.note(
                f"List done: {now.get('checked', 0)} speed checked"
                + (f", {failed} couldn't be checked (site down or blocking Google - Speed check next with 'Include sites already checked' retries them)." if failed else ".")
            )
            return
        if remaining == last:
            job.note(f"{remaining} on this list still not speed checked after the last batch - finishing up. They're left out (Review, another list, "
                     "do-not-contact) unless a step above says it had a problem.")
            yield ["--sheet", sheet, "--verify-links"]
            yield (EXPORT, [])
            return
        last = remaining
        job.note(f"{remaining} sites still to speed check.")
        yield ["--sheet", sheet, "--teardown", "--limit", str(RUN_ALL_BATCH)]


SAFE_TEXT = re.compile(r"^[A-Za-z0-9 ,;'&.\-]*$")


def build_find_args(body: dict, settings: dict[str, str]) -> tuple[list[str] | None, str]:
    """find_prospects.py options from the finder form - every value checked, nothing passed through raw."""
    from find_prospects import AGE_BANDS, DEFAULT_EXCLUDE, TRADES

    if not settings.get("COMPANIES_HOUSE_API_KEY"):
        return None, "Add COMPANIES_HOUSE_API_KEY in Settings first (free from developer.company-information.service.gov.uk)."
    trades = [t for t in body.get("trades") or [] if t in TRADES]
    if not trades:
        return None, "Tick at least one trade."
    areas = str(body.get("areas") or "").strip()
    if not areas or not re.search(r"[A-Za-z0-9]", areas):
        return None, "Type at least one area - a town like Guildford, or a postcode district like GU1."
    include = str(body.get("include") or "").strip()
    # Missing means "the usual"; an emptied box means "leave nothing out".
    exclude = str(body["exclude"] if "exclude" in body else DEFAULT_EXCLUDE).strip()
    for label, text in (("Areas", areas), ("Name must include", include), ("Leave out names with", exclude)):
        if len(text) > 300 or not SAFE_TEXT.match(text):
            return None, f"{label}: letters, numbers and commas only."
    age = str(body.get("age") or "any")
    if age not in AGE_BANDS:
        return None, "Unknown company age."
    try:
        most = int(body.get("max") or 100)
    except ValueError:
        return None, "Max firms must be a number."
    if not 1 <= most <= 1000:
        return None, "Max firms must be 1-1000."
    args = ["--trades", ",".join(trades), "--areas", areas, "--age", age, "--max", str(most), "--exclude", exclude]
    if include:
        args += ["--include", include]
    if (body.get("website_only") or body.get("email_only")) and body.get("no_websites"):
        return None, "Only firms with an email / a website needs the website search - untick Skip the website search."
    if body.get("website_only"):
        args.append("--website-only")
    if body.get("email_only"):
        args.append("--email-only")
    if body.get("no_directors"):
        args.append("--no-directors")
    if body.get("no_websites"):
        args.append("--no-websites")
    if body.get("action") == "count":
        args.append("--count-only")
    return args, ""


def build_steps(body: dict, settings: dict[str, str]):
    """(steps, error): steps yields argument lists for push_prospects.py, or (script, args) pairs."""
    action = body.get("action")
    if action not in ACTIONS:
        return None, "Unknown action."
    if action == "export":
        return (lambda job: [(EXPORT, [])]), ""
    if action == "autopilot_now":
        return (lambda job: [(AUTOPILOT, [])]), ""
    if action == "followups_sent":
        return (lambda job: [(BATCHES, ["--mark-followups-sent"]), (EXPORT, [])]), ""
    if action == "followups":
        try:
            size, days = int(body.get("followup_size") or 20), int(body.get("followup_days") or 5)
        except ValueError:
            return None, "Size and days must be numbers."
        if not 1 <= size <= 500 or not 1 <= days <= 60:
            return None, "Size 1-500, days 1-60."
        return (lambda job: [*replies_first(settings), (BATCHES, ["--followups", "--size", str(size), "--after-days", str(days)])]), ""
    if action == "replies":
        if not (settings.get("MAIL_ADDRESS") and settings.get("MAIL_APP_PASSWORD")):
            return None, "Add MAIL_ADDRESS and MAIL_APP_PASSWORD in Settings first."
        return (lambda job: [(REPLIES, [])]), ""
    if action in ("reply_watch_on", "reply_watch_off"):
        if action == "reply_watch_on" and not (settings.get("MAIL_ADDRESS") and settings.get("MAIL_APP_PASSWORD")):
            return None, "Add MAIL_ADDRESS and MAIL_APP_PASSWORD in Settings first."
        return (lambda job: [(REPLY_WATCH, ["--install" if action == "reply_watch_on" else "--remove"])]), ""
    if action in ("send_batch", "send_followups", "send_test"):
        if not (settings.get("MAIL_ADDRESS") and settings.get("MAIL_APP_PASSWORD")):
            return None, "Add MAIL_ADDRESS and MAIL_APP_PASSWORD in Settings first (the Gmail app password)."
        if not settings.get("MAIL_FROM_NAME"):
            return None, "Add MAIL_FROM_NAME in Settings first - the name people see, and your sign-off."
        send_from = str(body.get("send_from") or "").strip().lower()
        if send_from and not EMAIL.match(send_from):
            return None, "Pick an inbox to send from, or All inboxes."
        frm = ["--from", send_from] if send_from else []
        if action == "send_test":
            follow = body.get("test_kind") == "followups"
            return (lambda job: [(SEND, ["--test", *(["--followups"] if follow else []), *frm])]), ""
        extra = (["--followups"] if action == "send_followups" else []) + frm
        try:
            gap = float(body.get("send_gap") or 0)
        except (TypeError, ValueError):
            return None, "Minutes apart must be a number (or blank for about a minute)."
        if not 0 <= gap <= 60:
            return None, "Minutes apart must be between 0 and 60."
        if gap:
            extra += ["--gap-minutes", f"{gap:g}"]
        # Replies first, so anyone who said no since the batch was made is left out.
        return (lambda job: [*replies_first(settings), (SEND, extra), (EXPORT, [])]), ""
    if action == "scorecard":
        return (lambda job: [(SCORECARD, [])]), ""
    if action == "launch_report":
        from push_prospects import domain_of

        old, new = str(body.get("launch_old") or "").strip().lower(), str(body.get("launch_new") or "").strip().lower()
        old, new = domain_of(old), domain_of(new or old)
        if not (old and DOMAIN.match(old) and new and DOMAIN.match(new)):
            return None, "Type their old website (and the new one if it's a different domain), e.g. kerrroofing.co.uk"
        if not settings.get("PAGESPEED_API_KEY"):
            return None, "Add PAGESPEED_API_KEY in Settings first."
        return (lambda job: [(LAUNCH, ["--old", old, "--new", new])]), ""
    if action == "backup_now":
        return (lambda job: [(BACKUP, [])]), ""
    if action == "sending_health":
        if not settings.get("MAIL_ADDRESS"):
            return None, "Add MAIL_ADDRESS in Settings first - it's your sending domain that gets checked."
        return (lambda job: [(SENDING_HEALTH, [])]), ""
    if action == "client_speed":
        if not settings.get("PAGESPEED_API_KEY"):
            return None, "Add PAGESPEED_API_KEY in Settings first."
        return (lambda job: [(CLIENT_SPEED, [])]), ""
    if action in ("dns_snapshot", "launch_check"):
        from push_prospects import domain_of

        domain = domain_of(str(body.get("golive_domain") or "").strip().lower())
        if not (domain and DOMAIN.match(domain)):
            return None, "Type their domain, e.g. kerrroofing.co.uk"
        folder = str(body.get("publish_folder") or "").strip().lower()
        extra = ["--folder", folder] if re.match(r"^[a-z0-9][a-z0-9-]{0,80}$", folder) else []
        return (lambda job: [(GO_LIVE, ["dns" if action == "dns_snapshot" else "check", domain, *extra])]), ""
    if action == "write_copy":
        folder = str(body.get("publish_folder") or "").strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,80}$", folder):
            return None, "Type the firm's folder name under outreach/sites, e.g. kerr-roofing."
        if not (OUTREACH / "sites" / folder / "site.json").exists():
            return None, f"There's no outreach/sites/{folder}/site.json yet - use Draft their site on the Calls tab first."
        if not settings.get("ANTHROPIC_API_KEY"):
            return None, "Add ANTHROPIC_API_KEY in Settings first."
        return (lambda job: [(SITE_COPY, [folder])]), ""
    if action == "site_qa":
        folder = str(body.get("publish_folder") or "").strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,80}$", folder):
            return None, "Type the firm's folder name under outreach/sites, e.g. kerr-roofing."
        if not (OUTREACH / "sites" / folder / "site").is_dir():
            return None, f"There's no built site for {folder} yet - press Build site first."
        return (lambda job: [(SITE_QA, [folder])]), ""
    if action == "build_site":
        folder = str(body.get("publish_folder") or "").strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,80}$", folder):
            return None, "Type the firm's folder name under outreach/sites, e.g. kerr-roofing."
        if not (OUTREACH / "sites" / folder).is_dir():
            return None, f"There's no outreach/sites/{folder} - use Draft their site on the Calls tab first."
        cmd = "init" if not (OUTREACH / "sites" / folder / "site.json").exists() else "build"
        return (lambda job: [(SITE_KIT, [cmd, folder] + (["--draft"] if body.get("build_draft") and cmd == "build" else []))]), ""
    if action in ("publish_site", "publish_preview"):
        preview = action == "publish_preview"
        folder = str(body.get("publish_folder") or "").strip().lower()
        account = str(body.get("publish_account") or "").strip().lower()
        project = str(body.get("publish_project") or "").strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,80}$", folder):
            return None, "Type the firm's folder name under outreach/sites, e.g. kerr-roofing."
        if not settings.get("CLOUDFLARE_API_TOKEN"):
            return None, "Add CLOUDFLARE_API_TOKEN in Settings first."
        home = OUTREACH / "sites" / folder / "site" / "index.html"
        if not preview and home.exists() and 'class="draft-banner"' in home.read_text(encoding="utf-8", errors="ignore"):
            return None, ("That's a draft build (details still to confirm) - finish site.json and press Build site without the draft box "
                          "first, or use Publish preview to show the client the draft.")
        args = (["--folder", folder] + (["--account", account] if account else []) + (["--project", project] if project else [])
                + (["--preview"] if preview else []))
        return (lambda job: [(PUBLISH_SITE, args)]), ""
    if action == "batch_sent":
        return (lambda job: [(BATCHES, ["--mark-sent"]), (EXPORT, [])]), ""
    if action == "batch":
        try:
            size = int(body.get("batch_size") or 20)
        except ValueError:
            return None, "Batch size must be a number."
        if not 1 <= size <= 500:
            return None, "Batch size must be 1-500."
        args = ["--size", str(size)]
        if body.get("batch_scope") == "sheet":
            name = str(body.get("sheet") or "")
            if not sheet_path(name):
                return None, "Pick a sheet first."
            args += ["--sheet", name]
        return (lambda job: [*replies_first(settings), (BATCHES, args)]), ""
    if action == "install_segno":
        return (lambda job: [("pip", ["install", "segno"])]), ""
    if action in ("find", "count"):
        args, error = build_find_args(body, settings)
        if args is None:
            return None, error
        return (lambda job: [(FIND, args)]), ""
    name = str(body.get("sheet") or "")
    path = sheet_path(name)
    if not path:
        return None, "Pick a sheet in outreach/ first."
    dry = bool(body.get("dry_run"))
    if action == "all":
        if dry:
            return None, "Run the whole list can't be a dry run - a dry run never logs, so it would repeat the first batch. Untick Dry run."
        return (lambda job: run_all_steps(job, str(path), name, settings)), ""
    args = ["--sheet", str(path)]
    if action == "links":
        args.append("--dry-run")
    elif action == "prepare":
        if dry:
            return None, "Prepare Mailmeteor send pushes for real, so every link exists - untick Dry run."
        args.append("--verify-links")
        return (lambda job: [*replies_first(settings), args, (EXPORT, [])]), ""
    elif action == "speed":
        try:
            n = int(body.get("limit") or 10)
        except ValueError:
            return None, "Batch size must be a number."
        if not 1 <= n <= 100:
            return None, "Batch size must be 1-100."
        args += ["--teardown", "--limit", str(n)]
        if n > 10:
            args.append("--yes-all")
        if body.get("recheck"):
            args.append("--recheck")
    elif action == "retry":
        args += ["--teardown", "--retry-failed", "--yes-all"]
    elif action == "one":
        only = str(body.get("only") or "").strip()
        if not only:
            return None, "Type part of the business name or website."
        args += ["--teardown", "--only", only]
    elif action == "contacts":
        args.append("--find-contacts")
    elif action == "emails":
        args.append("--check-emails")
    elif action == "companies":
        if not settings.get("COMPANIES_HOUSE_API_KEY"):
            return None, "Add COMPANIES_HOUSE_API_KEY in Settings first (free from developer.company-information.service.gov.uk)."
        args.append("--lookup-companies")
    elif action == "trades":
        args.append("--guess-trades")
    elif action == "letters":
        args.append("--letters")
        if body.get("letters_all"):
            args.append("--letters-all")
    if dry and action != "links":
        args.append("--dry-run")
    return (lambda job: [args]), ""


class Job:
    """One run at a time: a single push_prospects.py call, or a chain of them."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.proc: subprocess.Popen | None = None
        self.thread: threading.Thread | None = None
        self.stopping = False
        self.lines: list[str] = []
        self.seq = 0  # lines ever added, so the page notices new output after the log is trimmed
        self.label = ""
        self.started = 0.0
        self.exit_code: int | None = None

    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def note(self, line: str) -> None:
        with self.lock:
            self.seq += 1
            self.lines.append(line)
            if len(self.lines) > MAX_LOG_LINES:
                del self.lines[: len(self.lines) - MAX_LOG_LINES]

    def start(self, label: str, steps, settings: dict[str, str], needs_secret: bool = True, keep_going: bool = False) -> str:
        with self.lock:
            if self.running():
                return "Something is already running - wait for it or press Stop."
            import autopilot

            if autopilot.is_running():
                return "Autopilot is running right now - wait for its text, or see outreach/autopilot-log.txt."
            if needs_secret and len(settings["PROSPECTS_API_SECRET"]) < 32:
                return "Add PROSPECTS_API_SECRET in Settings first (32+ characters, same value as in Vercel)."
            env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
            env.update({k: v for k, v in settings.items() if v})
            self.lines = [f"> {label}"]
            self.seq += 1
            self.label, self.started, self.exit_code, self.stopping = label, time.time(), None, False
            self.keep_going, self.failed_steps = keep_going, []
            self.thread = threading.Thread(target=self._run, args=(steps, env), daemon=True)
            self.thread.start()
            return ""

    def _run(self, steps, env: dict[str, str]) -> None:
        code = 0
        keep_awake(True)
        try:
            for step in steps(self):
                if self.stopping:
                    break
                script, args = step if isinstance(step, tuple) else (PUSH, step)
                if script == "pip":
                    argv, shown = [sys.executable, "-m", "pip", *args], "pip " + " ".join(args)
                else:
                    argv, shown = [sys.executable, "-u", str(script), *args], script.name + " " + " ".join(a if " " not in a else repr(a) for a in args)
                self.note(f"> python {shown}")
                self.note("")
                with self.lock:
                    self.proc = subprocess.Popen(
                        argv,
                        cwd=str(HERE),
                        env=env,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        stdin=subprocess.DEVNULL,
                    )
                    proc = self.proc
                assert proc.stdout
                for raw in proc.stdout:
                    self.note(raw.decode("utf-8", errors="replace").rstrip())
                code = proc.wait()
                self.note("")
                if self.stopping:
                    break
                if code != 0:
                    # A chain like "Run the whole list" carries on: each later step
                    # (the pushes, the link check) still does its job.
                    self.failed_steps.append(shown.split(" --")[0] + " " + " ".join(a for a in args if a.startswith("--") and a != "--sheet"))
                    if not self.keep_going:
                        break
                    self.note("That step had a problem (above) - carrying on with the rest.")
                    self.note("")
        except Exception as e:  # never leave the panel stuck on "running"
            self.note(f"Panel error: {e}")
            code = 1
        keep_awake(False)
        if getattr(self, "failed_steps", None) and self.keep_going and not self.stopping:
            self.note(f"Finished, but {len(self.failed_steps)} step(s) had problems - look for WARNING or errors above:")
            for f in self.failed_steps:
                self.note(f"    {f}")
            code = 1
        with self.lock:
            self.exit_code = code if not self.stopping else -1
            lines = list(self.lines)
        if time.time() - self.started >= ALERT_AFTER_S:
            phone_alert(self.label, code, self.stopping, time.time() - self.started, lines, env)
        with self.lock:
            self.seq += 1
            self.lines.append("Stopped." if self.stopping else "Done." if code == 0 else f"Stopped (exit code {code}).")

    def stop(self) -> None:
        with self.lock:
            self.stopping = True
            if self.proc is not None and self.proc.poll() is None:
                if sys.platform == "win32":
                    # The whole tree: the autopilot runs its steps as child processes, which a plain
                    # terminate() would leave running on their own.
                    subprocess.run(["taskkill", "/PID", str(self.proc.pid), "/T", "/F"], capture_output=True, timeout=30)
                else:
                    self.proc.terminate()

    def state(self) -> dict:
        with self.lock:
            return {
                "running": self.running(),
                "label": self.label,
                "started": self.started,
                "exit_code": self.exit_code,
                "lines": list(self.lines),
                "seq": self.seq,
            }


def calls_for(sheet: str) -> dict:
    import calls

    settings = load_settings()
    secret = settings["PROSPECTS_API_SECRET"]
    if len(secret) < 32:
        return {"viewing": [], "letters": [], "message": "Add PROSPECTS_API_SECRET in Settings first."}
    api = (settings["DASHBOARD_API_URL"] or "https://admin.scalardigital.co.uk").rstrip("/")
    site = (settings["SITE_URL"] or "https://www.scalardigital.co.uk").rstrip("/")
    tenant = os.environ.get("SCALAR_TENANT_ID", "abdc6408-1fd5-4fb6-9c4c-53600b571a6d")
    message = ""
    try:
        activity = calls.fetch_activity(api, secret, tenant)
    except calls.DashboardMissing as e:
        activity, message = None, str(e)
    if activity:
        import email_batches

        email_batches.block_optouts(OUTREACH, activity)
    try:
        out = calls.call_list(OUTREACH, sheet, secret, site, activity)
    except Exception as e:  # a sheet open in Excel, an odd file
        return {"viewing": [], "letters": [], "message": f"Couldn't read {sheet}: {e}"}
    out["message"] = message
    out["outcomes"] = calls.OUTCOMES
    return out


def quote_action(body: dict) -> tuple[dict, int]:
    """Calls tab "Quote" button: a numbered quote in the dashboard, and its link for you to send."""
    import calls
    import quotes
    from push_prospects import make_slug

    settings = load_settings()
    sheet, key = str(body.get("sheet") or ""), str(body.get("key") or "")
    business = str(body.get("business") or "").strip()[:120]
    package = str(body.get("package") or "")
    website = str(body.get("website") or "").lower()
    email = str(body.get("email") or "").strip()
    phone = str(body.get("phone") or "").strip()[:40]
    if not sheet_path(sheet) or not REVIEW_KEY.match(key) or not business or package not in quotes.PACKAGES:
        return {"error": "That doesn't look right."}, 400
    if email and not EMAIL.match(email):
        email = ""
    if len(settings["PROSPECTS_API_SECRET"]) < 32:
        return {"error": "Add PROSPECTS_API_SECRET in Settings first."}, 400
    slug = make_slug(business, website, settings["PROSPECTS_API_SECRET"]) if DOMAIN.match(website) else None
    founding = bool(body.get("founding")) and package == "build"
    try:
        result = quotes.create_quote(settings, business, email, phone, package, slug, founding=founding)
    except quotes.QuoteFailed as e:
        return {"error": f"No quote made: {e}."}, 502
    quotes.record(OUTREACH, sheet, key, business, package, result)
    try:
        import proposal

        proposal.make(OUTREACH, sheet, key, business, package, result, settings, founding,
                      {"website": website, "contact": str(body.get("contact") or "")})
        made_proposal = True
    except (OSError, ValueError, KeyError):
        made_proposal = False  # the quote exists either way; the proposal is the extra
    calls.log_call(OUTREACH, sheet, key, business, "Quoted", result.get("quote_number", ""))
    calls.mark_reply_handled(OUTREACH, business)
    signoff = settings.get("MAIL_FROM_NAME") or settings.get("LETTER_SIGNOFF") or "Scalar Digital"
    return {"ok": True, "quote_number": result.get("quote_number"), "total": (result.get("total_pence") or 0) / 100,
            "url": result["quote_url"], "mailto": quotes.email_link(email, str(body.get("contact") or ""), business, result, signoff),
            "proposal": made_proposal}, 200


def proposal_open_action(body: dict) -> tuple[dict, int]:
    """Calls tab "Open proposal": the printable proposal made with a quote, opened in your browser."""
    import proposal
    import quotes

    key = str(body.get("key") or "")
    sent = quotes.find_sent(OUTREACH, key, str(body.get("quote_number") or "")) if REVIEW_KEY.match(key) else None
    if not sent:
        return {"error": "Couldn't find that quote."}, 404
    path = proposal.path_for(OUTREACH, sent.get("business", ""), sent["quote_number"])
    if not path.exists():
        return {"error": "No proposal was saved for that quote - make the quote again."}, 404
    try:
        open_folder(path)
    except OSError as e:
        return {"error": f"Couldn't open it ({e}) - it's at {path}"}, 500
    return {"ok": True, "message": f"Opened - print it to PDF to attach it. Saved at outreach/sites/{path.parent.name}/{path.name}"}, 200


def draft_site_action(body: dict) -> tuple[dict, int]:
    """Calls tab "Draft their site": a client brief and a one-page draft, opened in your browser."""
    import site_draft

    sheet, key = str(body.get("sheet") or ""), str(body.get("key") or "")
    if not sheet_path(sheet) or not REVIEW_KEY.match(key):
        return {"error": "That doesn't look right."}, 400
    fallback = {k: str(body.get(k) or "").strip()[:150] for k in ("business", "website", "email", "phone", "contact")}
    if not DOMAIN.match(fallback["website"].lower()):
        fallback["website"] = ""
    try:
        folder = site_draft.make(OUTREACH, sheet, key, fallback, settings=load_settings())
    except (ValueError, OSError) as e:
        return {"error": f"No draft made: {e}."}, 400
    try:
        open_folder(folder / "index.html")
    except OSError:
        pass
    return {"ok": True, "message": f"Draft and brief saved in outreach/sites/{folder.name} - opened in your browser."}, 200


def quote_email_action(body: dict) -> tuple[dict, int]:
    """Calls tab "Email it to them": sends the quote link from your own email (as the batches are sent)."""
    import quotes
    import send_email

    settings = load_settings()
    sheet, key = str(body.get("sheet") or ""), str(body.get("key") or "")
    to = str(body.get("to") or "").strip()
    if not sheet_path(sheet) or not REVIEW_KEY.match(key) or not EMAIL.match(to):
        return {"error": "No email address for them - copy the link and send it yourself."}, 400
    if not (settings.get("MAIL_ADDRESS") and settings.get("MAIL_APP_PASSWORD")):
        return {"error": "Add MAIL_ADDRESS and MAIL_APP_PASSWORD in Settings to send from here - or use the mail-app link."}, 400
    sent = quotes.find_sent(OUTREACH, key, str(body.get("quote_number") or ""))
    if not sent or not sent.get("quote_url"):
        return {"error": "Couldn't find that quote - make it again."}, 404
    result = {"quote_url": sent["quote_url"], "quote_number": sent["quote_number"],
              "total_pence": round(float(sent.get("total") or 0) * 100)}
    signoff = settings.get("MAIL_FROM_NAME") or settings.get("LETTER_SIGNOFF") or "Scalar Digital"
    subject, text = quotes.email_text(str(body.get("contact") or ""), sent.get("business", ""), result, signoff)
    try:
        smtp = send_email.connect(settings)
        try:
            smtp.send_message(send_email.build_message(to, subject, text, env=settings))
        finally:
            smtp.quit()
    except send_email.SendStopped as e:
        return {"error": str(e)}, 502
    except (OSError, Exception) as e:  # refused recipient, dropped connection
        return {"error": f"Not sent: {e}"}, 502
    return {"ok": True, "message": f"Sent to {to} - it's in your Sent folder."}, 200


def reply_values(settings: dict, body: dict) -> dict[str, str]:
    import saved_replies

    def price(key: str, default: str) -> str:
        try:
            return f"{float(settings.get(key) or default):,.0f}"
        except ValueError:
            return default

    preview = str(body.get("preview") or "")
    return {
        "greeting_name": saved_replies.first_name(str(body.get("contact") or "")),
        "business": str(body.get("business") or "")[:120],
        "your_name": settings.get("MAIL_FROM_NAME") or settings.get("LETTER_SIGNOFF") or "Scalar Digital",
        "preview_url": preview.replace("src=dashboard", "src=email") if preview.startswith("https://") else "",
        "booking_link": settings.get("BOOKING_LINK", ""),
        "price_build": price("QUOTE_PRICE_BUILD", "2500"),
        "price_landing": price("QUOTE_PRICE_LANDING", "750"),
    }


def reply_draft_action(body: dict) -> tuple[dict, int]:
    """Calls tab "Reply": a saved reply filled in for this firm, to read and edit before sending."""
    import saved_replies

    replies = saved_replies.parse(saved_replies.load(OUTREACH))
    name = str(body.get("name") or "")
    if name not in replies:
        return {"error": "That saved reply doesn't exist any more - reload the tab."}, 400
    return {"ok": True, "text": saved_replies.render(replies[name], reply_values(load_settings(), body))}, 200


def reply_ai_action(body: dict) -> tuple[dict, int]:
    """Calls tab "Draft with AI": Claude's first go at answering their reply - shown in the box, never sent."""
    import ai_reply
    import saved_replies

    settings = load_settings()
    firm = {k: str(body.get(k) or "")[:200] for k in ("business", "trade", "area", "website", "mobile_score", "subject")}
    firm["message"] = str(body.get("message") or "")[: ai_reply.MAX_REPLY_CHARS]
    if not firm["business"]:
        return {"error": "That doesn't look right."}, 400
    try:
        text = ai_reply.draft(firm, reply_values(settings, body), saved_replies.load(OUTREACH),
                              settings.get("ANTHROPIC_API_KEY", ""), settings.get("AI_MODEL", ""))
    except ai_reply.AIError as e:
        return {"error": str(e)}, 502
    return {"ok": True, "text": text}, 200


def reply_send_action(body: dict) -> tuple[dict, int]:
    """Calls tab "Send reply": answers their email in the same thread, from the inbox that wrote to them."""
    import calls
    import mail_accounts
    import send_email

    settings = load_settings()
    sheet, key = str(body.get("sheet") or ""), str(body.get("key") or "")
    business = str(body.get("business") or "")[:150]
    to = str(body.get("to") or "").strip()
    text = str(body.get("text") or "").strip()
    message_id = str(body.get("message_id") or "").strip()
    subject = str(body.get("subject") or "").strip()[:200]
    if not sheet_path(sheet) or not REVIEW_KEY.match(key) or not business or not EMAIL.match(to):
        return {"error": "That doesn't look right."}, 400
    if not text or len(text) > 8000:
        return {"error": "Write the reply first (8,000 characters at most)."}, 400
    if not re.match(r"^<[^<>\s]{3,300}>$", message_id):
        message_id = ""
    inboxes = mail_accounts.accounts(settings)
    if not inboxes:
        return {"error": "Add MAIL_ADDRESS and MAIL_APP_PASSWORD in Settings to reply from here."}, 400
    sent_from = ""
    sent_path = OUTREACH / "emails-sent.csv"
    if sent_path.exists():
        with sent_path.open(encoding="utf-8") as f:
            sent_from = next((r.get("sent_from") or "" for r in csv.DictReader(f) if (r.get("email") or "").lower() == to.lower()), "")
    inbox = next((a for a in inboxes if a.address == sent_from.lower()), inboxes[0])
    subject = subject if subject.lower().startswith("re:") else f"Re: {subject or business}"
    env = {**settings, **inbox.env()}
    try:
        smtp = send_email.connect(env)
        try:
            smtp.send_message(send_email.build_message(to, subject, text + "\n", message_id, env=env))
        finally:
            smtp.quit()
    except send_email.SendStopped as e:
        return {"error": str(e)}, 502
    except Exception as e:  # refused recipient, dropped connection
        return {"error": f"Not sent: {e}"}, 502
    calls.log_call(OUTREACH, sheet, key, business, "Replied to them", str(body.get("name") or "")[:60])
    calls.mark_reply_handled(OUTREACH, business)
    calls.complete_callbacks(OUTREACH, key)
    return {"ok": True, "message": f"Replied to {to} from {inbox.address} - it's in that inbox's Sent folder."}, 200


def call_action(body: dict) -> tuple[dict, int]:
    from datetime import date

    import calls
    from contact_rules import add_to_blocklist

    sheet = str(body.get("sheet") or "")
    key = str(body.get("key") or "")
    outcome = str(body.get("outcome") or "")
    business = str(body.get("business") or "")[:150]
    if not sheet_path(sheet) or not REVIEW_KEY.match(key) or outcome not in calls.OUTCOMES or not business:
        return {"error": "That doesn't look right."}, 400
    note = str(body.get("note") or "")[:300]
    due = None
    if outcome == "Call back":
        due = calls.parse_due(str(body.get("due") or "3d"), date.today())
        if due is None:
            return {"error": "Call back when? Try 3d, 2w, 3m, tomorrow or a date like 2026-11-03 (within a year)."}, 400
    calls.log_call(OUTREACH, sheet, key, business, outcome, note)
    calls.mark_reply_handled(OUTREACH, business)
    if due:
        calls.add_callback(OUTREACH, sheet, key, business, due, note)
        return {"ok": True, "message": f"{business}: call back on {due.strftime('%a %d %b')} - they'll be top of Calls that day"}, 200
    calls.complete_callbacks(OUTREACH, key)
    if outcome == "Not interested":
        website, email = str(body.get("website") or "").lower(), str(body.get("email") or "").strip()
        entries = [("name", business)]
        if DOMAIN.match(website):
            entries.append(("website", website))
        if EMAIL.match(email):
            entries.append(("email", email))
        add_to_blocklist(OUTREACH, entries, "not interested (call)")
        return {"ok": True, "message": f"{business}: logged, and they won't be contacted again"}, 200
    return {"ok": True, "message": f"{business}: {outcome} logged"}, 200


def autopilot_action(body: dict) -> tuple[dict, int]:
    """Save the autopilot's settings, and turn the daily schedule on or off."""
    import autopilot

    action = str(body.get("action") or "")
    if action == "stop":
        return {"ok": True, "message": autopilot.stop()}, 200
    cfg = autopilot.load_config()
    if action in ("save", "on"):
        new = body.get("config") or {}
        at = str(new.get("time") or cfg["time"])
        if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", at):
            return {"error": "The time must look like 07:30."}, 400
        try:
            batch, fsize, fdays = int(new.get("batch_size") or 20), int(new.get("followup_size") or 20), int(new.get("followup_after_days") or 5)
        except ValueError:
            return {"error": "Sizes and days must be numbers."}, 400
        if not (1 <= batch <= 500 and 1 <= fsize <= 500 and 1 <= fdays <= 60):
            return {"error": "Batch sizes 1-500, days 1-60."}, 400
        find = new.get("find")
        if find is not None:
            settings = load_settings()
            args, error = build_find_args({**find, "action": "find"}, {**settings, "COMPANIES_HOUSE_API_KEY": settings.get("COMPANIES_HOUSE_API_KEY") or "x"})
            if args is None:
                return {"error": f"Search: {error}"}, 400
            find = {k: find.get(k) for k in ("trades", "areas", "age", "max", "include", "exclude", "email_only", "website_only", "no_directors", "no_websites")}
        try:
            gap = float(new.get("send_gap") or 0)
        except (TypeError, ValueError):
            return {"error": "Minutes apart must be a number."}, 400
        send_from = str(new.get("send_from") or "").strip().lower()
        if not 0 <= gap <= 60 or (send_from and not EMAIL.match(send_from)):
            return {"error": "Minutes apart 0-60, and pick an inbox (or All inboxes)."}, 400
        cfg.update({"time": at, "batch_size": batch, "followups": bool(new.get("followups")), "followup_size": fsize,
                    "followup_after_days": fdays, "auto_send": bool(new.get("auto_send")), "send_gap": gap,
                    "send_from": send_from, **({"find": find} if find is not None else {})})
        if action == "on":
            err = autopilot.install(at)
            if err:
                autopilot.save_config(cfg)
                return {"error": err}, 400
            cfg["enabled"] = True
        autopilot.save_config(cfg)
        sends = (f" It sends the batch itself, {gap:g} min apart{' from ' + send_from if send_from else ''}." if cfg["auto_send"]
                 else " It makes the batches; you press Send.")
        return {"ok": True, "message": (f"Autopilot on: every day at {at}." + sends) if cfg.get("enabled") else "Saved."}, 200
    if action == "off":
        err = autopilot.remove()
        cfg["enabled"] = False
        autopilot.save_config(cfg)
        return ({"error": err}, 400) if err else ({"ok": True, "message": "Autopilot off."}, 200)
    return {"error": "Unknown action."}, 400


def mark_posted(sheet: str) -> tuple[dict, int]:
    """Moves the last letters batch for this sheet into letters-sent.csv, dated today."""
    from datetime import date

    batch = OUTREACH / f"letters-batch-{Path(sheet).stem}.csv"
    if not batch.exists():
        return {"error": "No letters batch to mark - make letters first."}, 400
    with batch.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    sent_path = OUTREACH / "letters-sent.csv"
    sent: dict[str, dict] = {}
    if sent_path.exists():
        with sent_path.open(encoding="utf-8") as f:
            sent = {r["key"]: r for r in csv.DictReader(f) if r.get("key")}
    today = date.today().isoformat()
    for r in rows:
        sent[r["key"]] = {"key": r["key"], "business": r.get("business", ""), "sheet": r.get("sheet", sheet), "posted": today}
    with sent_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["key", "business", "sheet", "posted"])
        writer.writeheader()
        writer.writerows(sent.values())
    batch.unlink()
    return {"ok": True, "message": f"{len(rows)} letter{'s' if len(rows) != 1 else ''} marked as posted today."}, 200


REVIEW_KEY = re.compile(r"^(no:[A-Z0-9]{8}|name:[a-z0-9 ]{0,150})$")
REVIEW_TYPES = {"Ltd", "LLP", "PLC", "Sole trader", "Partnership"}
DOMAIN = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")
EMAIL = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def review_action(body: dict) -> tuple[dict, int]:
    """One Review button: every value checked before it's written."""
    import review

    sheet = str(body.get("sheet") or "")
    if not sheet_path(sheet):
        return {"error": "Pick a sheet first."}, 400
    action = str(body.get("action") or "")
    if action == "block":
        business = str(body.get("business") or "")[:150]
        website = str(body.get("website") or "").lower()
        email = str(body.get("email") or "").strip()
        if (website and not DOMAIN.match(website)) or (email and not EMAIL.match(email)) or not business:
            return {"error": "That doesn't look right."}, 400
        return {"ok": True, "message": review.block(OUTREACH, business, website, email)}, 200
    key = str(body.get("key") or "")
    if not REVIEW_KEY.match(key):
        return {"error": "Unknown firm."}, 400
    value = str(body.get("value") or "").strip()
    if action == "set_type" and value not in REVIEW_TYPES:
        return {"error": "Unknown company type."}, 400
    if action == "website_yes":
        value = value.lower().removeprefix("https://").removeprefix("http://").removeprefix("www.").strip("/")
        if not DOMAIN.match(value):
            return {"error": "That isn't a website address."}, 400
    if action == "set_email" and value and not EMAIL.match(value):
        return {"error": "That isn't an email address."}, 400
    if action not in ("set_type", "keep_closed", "website_yes", "website_no", "set_email", "skip", "undo"):
        return {"error": "Unknown action."}, 400
    return {"ok": True, "message": review.decide(OUTREACH, sheet, key, action, value)}, 200


def keep_awake(on: bool) -> None:
    """Stops Windows sleeping mid-run (the screen may still turn off). Called on the run's own thread."""
    if sys.platform != "win32":
        return
    import ctypes

    ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
    ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | (ES_SYSTEM_REQUIRED if on else 0))


# Only these lines go in a phone alert: counts and outcomes, never names or emails.
ALERT_LINE = re.compile(r"^(READY|List done|Logged|Pushed|Wrote|\d+ prospects|\d+ companies|Only \d+|Stopped|  (Outreach|Check website|No website) )")


def phone_alert(label: str, code: int, stopped: bool, seconds: float, lines: list[str], env: dict[str, str]) -> None:
    token, chat = env.get("TELEGRAM_BOT_TOKEN", ""), env.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat:
        return
    mins = int(seconds // 60)
    took = f"{mins // 60}h {mins % 60}m" if mins >= 60 else f"{mins}m"
    head = ("Stopped: " if stopped else "Done: " if code == 0 else "Failed: ") + f"{label} ({took})"
    summary = [ln.strip() for ln in lines if ALERT_LINE.match(ln)][-6:]
    text = "\n".join([head, *summary])
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode(),
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=15).close()
    except (urllib.error.URLError, TimeoutError, OSError):
        pass  # an alert that can't be sent never breaks a run


JOB = Job()


def open_folder(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(path)])


# ---------------------------------------------------------------- server


class Handler(BaseHTTPRequestHandler):
    token = ""
    port = 8765

    def log_message(self, *args) -> None:
        pass

    def _host_ok(self) -> bool:
        # Blocks DNS rebinding: only answer to our own address.
        return self.headers.get("Host", "") in (f"127.0.0.1:{self.port}", f"localhost:{self.port}")

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data: dict, status: int = 200) -> None:
        self._send(status, json.dumps(data).encode(), "application/json")

    def do_GET(self) -> None:
        if not self._host_ok():
            return self._send(403, b"Forbidden", "text/plain")
        route = urlparse(self.path).path
        if route == "/":
            page = (
                PAGE.replace("__TOKEN__", self.token)
                .replace("__OUTREACH__", html.escape(str(OUTREACH)))
                .replace("__VERSION__", PANEL_VERSION)
                .replace("__HERE__", html.escape(str(HERE)))
            )
            return self._send(200, page.encode(), "text/html; charset=utf-8")
        if route == "/api/state":
            settings = load_settings()
            return self._json(
                {
                    "job": JOB.state(),
                    "sheets": sheets(),
                    "latest_sheet": latest_sheet(),
                    "files": output_files(),
                    "reply_watch": _reply_watch_last(),
                    "health": health(OUTREACH, settings),
                    "settings": {
                        k: (bool(settings[k]) if k in SECRET_KEYS else settings[k]) for k in SETTING_KEYS
                    },
                    "dashboard": (settings["DASHBOARD_API_URL"] or "https://admin.scalardigital.co.uk").rstrip("/"),
                    "site": (settings["SITE_URL"] or "https://www.scalardigital.co.uk").rstrip("/"),
                }
            )
        if route.startswith("/letters/"):
            from urllib.parse import unquote

            name = unquote(route[len("/letters/") :])
            path = OUTREACH / name
            if not re.fullmatch(r"letters-[A-Za-z0-9._ -]+\.html", name) or not path.is_file():
                return self._send(404, b"Not found", "text/plain")
            return self._send(200, path.read_bytes(), "text/html; charset=utf-8")
        if route.startswith("/api/letters/"):
            from urllib.parse import unquote

            name = unquote(route[len("/api/letters/") :])
            if not sheet_path(name):
                return self._json({})
            stem = Path(name).stem
            batch = OUTREACH / f"letters-batch-{stem}.csv"
            n = 0
            if batch.exists():
                with batch.open(encoding="utf-8") as f:
                    n = sum(1 for _ in csv.DictReader(f))
            page = OUTREACH / f"letters-{stem}.html"
            try:
                import importlib.util

                has_segno = importlib.util.find_spec("segno") is not None
            except (ImportError, ValueError):
                has_segno = False
            return self._json({"page": page.name if page.exists() else "", "batch": n, "segno": has_segno})
        if route.startswith("/api/calls/"):
            from urllib.parse import unquote

            name = unquote(route[len("/api/calls/") :])
            if not sheet_path(name):
                return self._json({"viewing": [], "letters": []})
            return self._json(calls_for(name))
        if route == "/api/autopilot":
            import autopilot

            cfg = autopilot.load_config()
            log = OUTREACH / "autopilot-log.txt"
            last = ""
            if log.exists():
                lines = [ln.split("  ", 1)[-1] for ln in log.read_text(encoding="utf-8").splitlines() if ln.strip()]
                tail = [ln for ln in lines if ln.startswith(("Autopilot done", "Replies:", "READY", "Next:")) or "had problems" in ln]
                last = f"Last run {time.strftime('%a %d %b %H:%M', time.localtime(log.stat().st_mtime))}: " + " · ".join(tail[-6:])
            running = autopilot.is_running()
            return self._json({"config": cfg, "last": last, "running": running, "now": autopilot.now_doing() if running else {},
                               "windows": sys.platform == "win32"})
        if route.startswith("/api/batch"):
            import email_batches

            from urllib.parse import parse_qs

            q = parse_qs(urlparse(self.path).query)
            name = (q.get("sheet") or [""])[0]
            scope = name if name and sheet_path(name) and (q.get("scope") or [""])[0] == "sheet" else None
            pending = OUTREACH / email_batches.PENDING
            batch = ""
            if pending.exists():
                with pending.open(encoding="utf-8") as f:
                    rows = list(csv.DictReader(f))
                batch = f"{rows[0]['batch']} ({len(rows)})" if rows else ""
            import mail_accounts
            import send_email
            from datetime import date

            _sync_mailmeteor_soon()
            # Today's sending, per inbox. Only your own sending addresses and counts leave
            # this function - never a prospect's address.
            inboxes = [a.address for a in mail_accounts.accounts({**os.environ, **load_settings()})]
            today = send_email.today_summary(OUTREACH, date.today(), inboxes) if OUTREACH.is_dir() else None
            return self._json({"remaining": email_batches.remaining(OUTREACH, scope) if OUTREACH.is_dir() else 0, "pending": batch,
                               "today": today, "domain_warnings": _domain_warnings()})
        if route == "/api/email-template":
            import send_email

            return self._json(send_email.load_templates(OUTREACH))
        if route == "/api/reply-templates":
            import saved_replies

            text = saved_replies.load(OUTREACH)
            return self._json({"text": text, "names": list(saved_replies.parse(text))})
        if route == "/api/letter-template":
            import letters

            with_site, no_site = letters.load_templates(OUTREACH)
            return self._json({"with_site": with_site, "no_site": no_site})
        if route.startswith("/api/review/"):
            from urllib.parse import unquote

            name = unquote(route[len("/api/review/") :])
            if not sheet_path(name):
                return self._json({"items": []})
            try:
                import review

                return self._json({"items": review.items(OUTREACH, name), "kinds": review.KINDS})
            except Exception as e:  # a sheet open in Excel, an odd file
                return self._json({"items": [], "error": f"Couldn't read {name}: {e}"})
        if route.startswith("/api/progress/"):
            from urllib.parse import unquote

            return self._json(progress(unquote(route[len("/api/progress/") :])))
        self._send(404, b"Not found", "text/plain")

    def do_POST(self) -> None:
        # Blocks other websites posting to this panel from your browser.
        if not self._host_ok() or self.headers.get("X-Panel-Token") != self.token:
            return self._send(403, b"Forbidden", "text/plain")
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
        except ValueError:
            return self._json({"error": "Bad request."}, 400)
        route = urlparse(self.path).path
        if route == "/api/run":
            settings = load_settings()
            steps, error = build_steps(body, settings)
            if steps is None:
                return self._json({"error": error}, 400)
            import autopilot

            if autopilot.is_running():
                # Said loudly, with what it's doing, so the page can offer to stop it - a list run
                # refused quietly here is why a Mailmeteor file never appeared.
                return self._json({"error": "The autopilot is running, so nothing else can run until it finishes or is stopped.",
                                   "autopilot": autopilot.now_doing()}, 409)
            finder = body["action"] in ("find", "count")
            label = ACTIONS[body["action"]] + (" (dry run)" if body.get("dry_run") and not finder else "")
            error = JOB.start(label, steps, settings, needs_secret=not finder and body["action"] != "install_segno",
                              keep_going=body["action"] in ("all", "prepare", "batch"))
            return self._json({"error": error} if error else {"ok": True}, 409 if error else 200)
        if route == "/api/autopilot":
            return self._json(*autopilot_action(body))
        if route == "/api/letters/posted":
            name = str(body.get("sheet") or "")
            if not sheet_path(name):
                return self._json({"error": "Pick a sheet first."}, 400)
            return self._json(*mark_posted(name))
        if route == "/api/letter-template":
            import letters

            if body.get("reset"):
                letters.save_templates(OUTREACH, letters.DEFAULT_TEMPLATE, letters.DEFAULT_TEMPLATE_NO_WEBSITE)
            else:
                with_site, no_site = str(body.get("with_site") or ""), str(body.get("no_site") or "")
                if not with_site.strip() or not no_site.strip() or len(with_site) > 5000 or len(no_site) > 5000:
                    return self._json({"error": "Both letters need some text (5,000 characters at most)."}, 400)
                letters.save_templates(OUTREACH, with_site, no_site)
            return self._json({"ok": True})
        if route == "/api/email-template":
            import send_email

            if body.get("reset"):
                (OUTREACH / send_email.TEMPLATES).unlink(missing_ok=True)
                return self._json({"ok": True})
            problem = send_email.save_templates(
                OUTREACH, {k: str(body.get(k) or "") for k in [*send_email.DEFAULT_TEMPLATES, *send_email.VARIANT_B]})
            return self._json({"error": problem}, 400) if problem else self._json({"ok": True})
        if route == "/api/quote":
            return self._json(*quote_action(body))
        if route == "/api/calls":
            return self._json(*call_action(body))
        if route == "/api/quote-email":
            return self._json(*quote_email_action(body))
        if route == "/api/proposal-open":
            return self._json(*proposal_open_action(body))
        if route == "/api/reply-templates":
            import saved_replies

            if body.get("reset"):
                (OUTREACH / saved_replies.FILE).unlink(missing_ok=True)
                return self._json({"ok": True})
            OUTREACH.mkdir(exist_ok=True)
            why = saved_replies.save(OUTREACH, str(body.get("text") or ""))
            return self._json({"error": why}, 400) if why else self._json({"ok": True})
        if route == "/api/reply-draft":
            return self._json(*reply_draft_action(body))
        if route == "/api/email-preview":
            import send_email

            return self._json(send_email.preview_batch(OUTREACH, body.get("kind") == "followups", load_settings(),
                                                       str(body.get("from") or "")))
        if route == "/api/reply-ai":
            return self._json(*reply_ai_action(body))
        if route == "/api/reply-send":
            return self._json(*reply_send_action(body))
        if route == "/api/draft-site":
            return self._json(*draft_site_action(body))
        if route == "/api/review":
            return self._json(*review_action(body))
        if route == "/api/stop":
            JOB.stop()
            return self._json({"ok": True})
        if route == "/api/settings":
            save_settings(body)
            from company_lookup import key_problem

            ch = load_settings()["COMPANIES_HOUSE_API_KEY"]
            return self._json({"ok": True, "warning": key_problem(ch) if ch else None})
        if route == "/api/open-results":
            path = OUTREACH / RESULTS_NAME
            if not path.exists():
                return self._json({"error": "Export first - there's no results workbook yet."}, 400)
            open_folder(path)
            return self._json({"ok": True})
        if route == "/api/open-folder":
            OUTREACH.mkdir(exist_ok=True)
            open_folder(OUTREACH)
            return self._json({"ok": True})
        self._send(404, b"Not found", "text/plain")


# The page itself (HTML, CSS and JS) lives next to this file, so an editor can check it as a web page.
# __TOKEN__ and __VERSION__ are filled in per request (Handler.do_GET).
PAGE = (HERE / "panel.html").read_text(encoding="utf-8")


def running_panel_version(port: int) -> str | None:
    """The version of a panel already on this port: "" for one too old to say, None if it isn't a panel."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=3) as res:
            page = res.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError):
        return None
    if "Prospect Control Panel" not in page:
        return None
    found = re.search(r">v([0-9.]+) ", page)
    return found.group(1) if found else ""


def stop_old_panel(port: int) -> None:
    """Closes the panel process listening on this port (Windows), so the new version can start."""
    if sys.platform == "win32":
        command = (
            f"Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | "
            f"Where-Object {{ $_.OwningProcess -ne {os.getpid()} }} | "
            "ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }"
        )
        subprocess.run(["powershell", "-NoProfile", "-Command", command], capture_output=True, timeout=30)
    else:
        subprocess.run(["fuser", "-k", f"{port}/tcp"], capture_output=True, timeout=30)
    time.sleep(1)


class PanelServer(ThreadingHTTPServer):
    # On Windows, "reuse address" lets a second server share a port that's in use, and the
    # browser keeps talking to the old one - so an update never showed. Claim the port alone.
    allow_reuse_address = sys.platform != "win32"

    def server_bind(self) -> None:
        if sys.platform == "win32":
            import socket

            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def start_server(port: int) -> ThreadingHTTPServer | str | None:
    """Our server - replacing an older panel still running on the port. "same" if this
    version is already running (left alone: it may be mid-run), None if something else has the port."""
    # Ask first, rather than rely on the port being refused.
    version = running_panel_version(port)
    if version == PANEL_VERSION:
        return "same"
    if version is not None:
        print(f"Closing the panel that was already running ({'v' + version if version else 'an old version'}) and starting v{PANEL_VERSION} ...")
        stop_old_panel(port)
    for attempt in range(3):
        try:
            return PanelServer(("127.0.0.1", port), Handler)
        except OSError:
            if running_panel_version(port) is None:
                return None  # not a panel - never close someone else's program
            stop_old_panel(port)
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    args = ap.parse_args()

    Handler.token = secrets.token_urlsafe(24)
    Handler.port = args.port
    server = start_server(args.port)
    url = f"http://127.0.0.1:{args.port}/"
    if server == "same":
        print(f"The panel is already open at {url}")
        if not args.no_browser:
            webbrowser.open(url)
        return
    if server is None:
        print(f"Port {args.port} is busy with something that isn't this panel - try --port 8766")
        return
    print(f"Control panel running at {url}  (close this window to stop it)")
    print(f"Reading sheets from {OUTREACH}")
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        JOB.stop()


if __name__ == "__main__":
    main()
