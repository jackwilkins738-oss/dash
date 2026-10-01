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


def replies_first(settings: dict[str, str]) -> list:
    """Check replies before anything that picks who to contact - if the inbox is set up."""
    return [(REPLIES, [])] if settings.get("MAIL_ADDRESS") and settings.get("MAIL_APP_PASSWORD") else []
RESULTS_NAME = "outreach-results.xlsx"
SETTING_KEYS = [
    "PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    "LETTER_SIGNOFF", "LETTER_EMAIL", "LETTER_PHONE", "MAIL_ADDRESS", "MAIL_APP_PASSWORD", "MAIL_IMAP_HOST", "MAIL_FROM_NAME",
    "MAIL_EXTRA_1_ADDRESS", "MAIL_EXTRA_1_PASSWORD", "MAIL_EXTRA_2_ADDRESS", "MAIL_EXTRA_2_PASSWORD",
    "MAIL_EXTRA_3_ADDRESS", "MAIL_EXTRA_3_PASSWORD",
    "QUOTE_PRICE_BUILD", "QUOTE_PRICE_LANDING", "QUOTE_VAT_RATE", "QUOTE_DEPOSIT_PERCENT",
    "DASHBOARD_API_URL", "SITE_URL", "BOOKING_LINK", "CLOUDFLARE_API_TOKEN", "CLOUD_REPLY_ALERTS",
]
SECRET_KEYS = {"CLOUDFLARE_API_TOKEN", "PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "TELEGRAM_BOT_TOKEN", "MAIL_APP_PASSWORD",
               "MAIL_EXTRA_1_PASSWORD", "MAIL_EXTRA_2_PASSWORD", "MAIL_EXTRA_3_PASSWORD"}
# A run this long gets a phone alert when it ends (if Telegram is set up).
ALERT_AFTER_S = 180
RUN_ALL_BATCH = 10
# Shown in the header. Bump it with every change, so an old panel still running is obvious.
PANEL_VERSION = "40"
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


def _reply_watch_last() -> dict | None:
    import reply_watch

    try:
        return reply_watch.last_check(OUTREACH)
    except OSError:
        return None


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
    "build_site": "Build site",
    "publish_site": "Publish site",
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
            job.note(f"{remaining} still to check but the last batch made no progress - finishing up.")
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
        if action == "send_test":
            follow = body.get("test_kind") == "followups"
            return (lambda job: [(SEND, ["--test", *(["--followups"] if follow else [])])]), ""
        extra = ["--followups"] if action == "send_followups" else []
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
    if action == "build_site":
        folder = str(body.get("publish_folder") or "").strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,80}$", folder):
            return None, "Type the firm's folder name under outreach/sites, e.g. kerr-roofing."
        if not (OUTREACH / "sites" / folder).is_dir():
            return None, f"There's no outreach/sites/{folder} - use Draft their site on the Calls tab first."
        cmd = "init" if not (OUTREACH / "sites" / folder / "site.json").exists() else "build"
        return (lambda job: [(SITE_KIT, [cmd, folder] + (["--draft"] if body.get("build_draft") and cmd == "build" else []))]), ""
    if action == "publish_site":
        folder = str(body.get("publish_folder") or "").strip().lower()
        account = str(body.get("publish_account") or "").strip().lower()
        project = str(body.get("publish_project") or "").strip().lower()
        if not re.match(r"^[a-z0-9][a-z0-9-]{0,80}$", folder):
            return None, "Type the firm's folder name under outreach/sites, e.g. kerr-roofing."
        if not settings.get("CLOUDFLARE_API_TOKEN"):
            return None, "Add CLOUDFLARE_API_TOKEN in Settings first."
        home = OUTREACH / "sites" / folder / "site" / "index.html"
        if home.exists() and 'class="draft-banner"' in home.read_text(encoding="utf-8", errors="ignore"):
            return None, "That's a draft build (details still to confirm) - finish site.json and press Build site without the draft box first."
        args = ["--folder", folder] + (["--account", account] if account else []) + (["--project", project] if project else [])
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
        cfg.update({"time": at, "batch_size": batch, "followups": bool(new.get("followups")), "followup_size": fsize,
                    "followup_after_days": fdays, **({"find": find} if find is not None else {})})
        if action == "on":
            err = autopilot.install(at)
            if err:
                autopilot.save_config(cfg)
                return {"error": err}, 400
            cfg["enabled"] = True
        autopilot.save_config(cfg)
        return {"ok": True, "message": f"Autopilot on: every day at {at}." if cfg.get("enabled") else "Saved."}, 200
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
    summary = [l.strip() for l in lines if ALERT_LINE.match(l)][-6:]
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
                lines = [l.split("  ", 1)[-1] for l in log.read_text(encoding="utf-8").splitlines() if l.strip()]
                tail = [l for l in lines if l.startswith(("Autopilot done", "Replies:", "READY", "Next:")) or "had problems" in l]
                last = f"Last run {time.strftime('%a %d %b %H:%M', time.localtime(log.stat().st_mtime))}: " + " · ".join(tail[-6:])
            return self._json({"config": cfg, "last": last, "running": autopilot.is_running(), "windows": sys.platform == "win32"})
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
                               "today": today})
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


PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Prospect Control Panel</title>
<style>
  :root { --bg:#0f1115; --card:#171a21; --line:#262b35; --text:#e7e9ee; --dim:#8b93a3; --accent:#4f8cff; --ok:#3ecf8e; --bad:#ff6b6b; --warn:#f5b84b; }
  * { box-sizing: border-box; }
  [hidden] { display: none !important; }
  body { margin:0; background:var(--bg); color:var(--text); font:14px/1.45 system-ui, -apple-system, Segoe UI, sans-serif; }
  header { position:sticky; top:0; z-index:5; display:flex; align-items:center; gap:18px; padding:10px 20px; background:var(--bg); border-bottom:1px solid var(--line); flex-wrap:wrap; }
  header h1 { font-size:16px; margin:0; }
  header .ver { color:var(--dim); font-weight:400; font-size:12px; }
  .jobbar { display:flex; align-items:center; gap:10px; flex:1; min-width:260px; padding:6px 12px; background:var(--card); border:1px solid var(--line); border-radius:8px; }
  .jobbar #stop { margin-left:auto; padding:4px 10px; }
  .jobbar .msg { margin:0; min-height:0; }
  nav.links { display:flex; gap:14px; }
  nav.links a { color:var(--dim); text-decoration:none; font-size:13px; } nav.links a:hover { color:var(--text); }
  nav.sections { position:sticky; top:53px; z-index:4; display:flex; align-items:center; gap:2px; padding:0 20px; background:var(--bg); border-bottom:1px solid var(--line); overflow-x:auto; }
  .listpick { margin-left:auto; display:flex; align-items:center; gap:8px; padding-left:16px; }
  .listpick label { margin:0; white-space:nowrap; }
  .listpick select { width:auto; max-width:260px; padding:5px 8px; }
  main { display:grid; grid-template-columns: minmax(0, 1fr) 460px; gap:16px; padding:16px 20px; align-items:start; }
  main.wide { grid-template-columns: minmax(0, 1fr); }
  main.wide aside.output { display:none; }
  .content { min-width:0; max-width:900px; }
  main.wide .content { max-width:none; }
  aside.output { position:sticky; top:110px; }
  aside.output h2 { font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--dim); margin:0 0 8px; }
  @media (max-width: 1000px) { main { grid-template-columns: 1fr; } aside.output { position:static; } aside.output pre { height:50vh; } }
  @media (max-width: 700px) { header, nav.sections { position:static; } .card.savebar { position:static; } nav.links { flex-wrap:wrap; } }
  .card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; margin-bottom:16px; }
  .card h2 { font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--dim); margin:0 0 10px; }
  label { display:block; color:var(--dim); font-size:12px; margin:8px 0 4px; }
  textarea { width:100%; padding:7px 9px; background:#0f1115; color:var(--text); border:1px solid var(--line); border-radius:6px; font:12.5px/1.45 ui-monospace, Consolas, monospace; resize:vertical; }
  input[type=text], input[type=password], input[type=number], select { width:100%; padding:7px 9px; background:#0f1115; color:var(--text); border:1px solid var(--line); border-radius:6px; font:inherit; }
  .row { display:flex; gap:8px; align-items:center; margin-top:8px; }
  .row input[type=number] { width:80px; }
  .check { display:flex; gap:6px; align-items:center; color:var(--dim); font-size:13px; margin-top:8px; }
  button { white-space:nowrap; background:#232834; color:var(--text); border:1px solid var(--line); border-radius:6px; padding:8px 12px; font:inherit; cursor:pointer; }
  button:hover { border-color:var(--accent); }
  button.primary { background:var(--accent); border-color:var(--accent); color:#fff; }
  button.danger { color:var(--bad); }
  button:disabled { opacity:.45; cursor:not-allowed; }
  .action { border-top:1px solid var(--line); padding-top:10px; margin-top:10px; }
  .action:first-of-type { border-top:0; margin-top:0; padding-top:0; }
  .action p { color:var(--dim); font-size:12px; margin:4px 0 0; }
  .stats { display:grid; grid-template-columns:repeat(4,1fr); gap:8px; }
  .stat { background:#0f1115; border:1px solid var(--line); border-radius:8px; padding:8px; }
  .stat b { display:block; font-size:20px; } .stat span { color:var(--dim); font-size:11px; }
  .bar { height:6px; background:#0f1115; border-radius:3px; overflow:hidden; margin-top:10px; display:flex; }
  .bar i { display:block; height:100%; }
  pre { margin:0; background:#0b0d11; border:1px solid var(--line); border-radius:8px; padding:12px; height:calc(100vh - 160px); min-height:320px; overflow:auto; white-space:pre-wrap; word-break:break-word; font:12.5px/1.5 ui-monospace, Consolas, monospace; }
  .dim { color:var(--dim); }
  .row.wrap { flex-wrap:wrap; }
  .row input[type=text] { flex:1; }
  .card h2 { font-size:13px; color:var(--text); text-transform:none; letter-spacing:0; }
  .glance { display:grid; grid-template-columns:1fr 1fr 1.6fr; gap:10px; margin-bottom:16px; }
  .tile { display:flex; flex-direction:column; align-items:flex-start; gap:4px; text-align:left; white-space:normal; background:var(--card); border:1px solid var(--line); border-radius:10px; padding:12px 14px; color:var(--dim); font-size:12px; }
  .tile b { font-size:24px; color:var(--text); }
  .tile.hero { border-color:rgba(79,140,255,.45); }
  .tile.hero b { font-size:15px; }
  @media (max-width: 700px) { .glance { grid-template-columns:1fr; } }
  .grid3 { display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px; }
  .grid4 { display:grid; grid-template-columns:repeat(4, 1fr); gap:8px; }
  label code { color:var(--dim); font-size:10.5px; opacity:.8; }
  .card.savebar { position:sticky; bottom:0; border-color:rgba(79,140,255,.45); }
  @media (max-width: 700px) { .grid2, .grid3, .grid4 { grid-template-columns:1fr; } }
  table.tools { width:100%; border-collapse:collapse; }
  table.tools td { padding:9px 8px 9px 0; border-top:1px solid var(--line); vertical-align:top; color:var(--dim); font-size:12.5px; }
  table.tools tr:first-child td { border-top:0; }
  table.tools td:first-child { width:46%; color:var(--text); }
  table.tools .check { margin-top:6px; }
  ol.steps { margin:10px 0 0; padding-left:20px; color:var(--dim); font-size:12.5px; }
  ol.steps li { margin:4px 0; }
  button.link { background:none; border:0; padding:0; color:var(--accent); text-decoration:underline; font-size:inherit; }
  .badge.good { background:var(--ok); }
  .dot { width:9px; height:9px; border-radius:50%; background:var(--dim); }
  .dot.run { background:var(--warn); animation:pulse 1s infinite; } .dot.ok { background:var(--ok); } .dot.bad { background:var(--bad); }
  @keyframes pulse { 50% { opacity:.3; } }
  .files { list-style:none; margin:0; padding:0; font-size:13px; }
  .files li { display:flex; justify-content:space-between; padding:3px 0; border-bottom:1px dashed var(--line); }
  .files span { color:var(--dim); }
  .msg { color:var(--bad); font-size:13px; margin-top:8px; min-height:1em; }
  .saved { color:var(--ok); font-size:12px; }
  details summary { cursor:pointer; color:var(--dim); font-size:12px; text-transform:uppercase; letter-spacing:.06em; }
  .card > details > summary { font-size:13px; font-weight:700; color:var(--text); text-transform:none; letter-spacing:0; }
  .chips { display:flex; flex-wrap:wrap; gap:6px; }
  .chip { display:inline-flex; align-items:center; gap:5px; margin:0; padding:5px 9px; border:1px solid var(--line); border-radius:999px; color:var(--text); font-size:13px; cursor:pointer; user-select:none; }
  .chip:has(input:checked) { border-color:var(--accent); background:rgba(79,140,255,.14); }
  .chip input { margin:0; accent-color:var(--accent); }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
  .hint { color:var(--dim); font-size:12px; margin:4px 0 0; }
  .card.find { border-color:rgba(79,140,255,.45); }
  .tabs { display:flex; gap:4px; margin-bottom:10px; border-bottom:1px solid var(--line); }
  .tab { background:none; border:0; border-bottom:2px solid transparent; border-radius:0; padding:11px 12px; color:var(--dim); }
  .tab:hover { color:var(--text); border-color:transparent; border-bottom-color:var(--line); }
  .tab.on { color:var(--text); border-bottom-color:var(--accent); }
  .badge { display:inline-block; min-width:18px; padding:0 6px; margin-left:6px; border-radius:9px; background:var(--warn); color:#111; font-size:11px; font-weight:700; }
  #review, #calls { min-height:200px; }
  .ritem { border:1px solid var(--line); border-radius:8px; padding:10px 12px; margin-bottom:8px; background:#0f1115; }
  .ritem .top { display:flex; gap:10px; align-items:baseline; flex-wrap:wrap; }
  .ritem b { font-size:14px; } .ritem a { color:var(--accent); font-size:12px; text-decoration:none; }
  .ritem .why { color:var(--dim); font-size:12px; margin:4px 0 8px; }
  .ritem .btns { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
  .ritem .btns button { padding:5px 9px; font-size:12px; }
  .ritem input { width:auto; flex:1; min-width:180px; padding:5px 8px; }
  .ritem input[type=checkbox] { flex:0 0 auto; min-width:0; padding:0; }
  .kind { font-size:11px; color:var(--warn); text-transform:uppercase; letter-spacing:.05em; }
  .toast { color:var(--ok); font-size:12px; min-height:1em; margin-bottom:6px; }
  summary.card-title { font-size:12px; font-weight:700; color:var(--dim); list-style-position:inside; }
</style>
</head>
<body>
<header>
  <h1>Control Panel <span class="ver">v__VERSION__</span></h1>
  <div class="jobbar">
    <span class="dot" id="dot"></span><b id="job-label">Nothing running</b><span id="job-time" class="dim"></span>
    <button class="danger" id="stop" disabled>Stop</button>
    <span class="msg" id="run-msg"></span>
  </div>
  <nav class="links">
    <a id="lnk-dash" href="#" target="_blank" rel="noopener">Dashboard ↗</a>
    <a id="lnk-site" href="#" target="_blank" rel="noopener">Website ↗</a>
    <a href="https://mailmeteor.com/" target="_blank" rel="noopener">Mailmeteor ↗</a>
    <a href="https://pagespeed.web.dev/" target="_blank" rel="noopener">PageSpeed ↗</a>
    <a href="https://www.tpsonline.org.uk/" target="_blank" rel="noopener">TPS ↗</a>
  </nav>
</header>

<nav class="sections" id="sections">
  <button class="tab on" data-tab="today">Today</button>
  <button class="tab" data-tab="calls">Calls<span class="badge good" id="calls-count" hidden></span></button>
  <button class="tab" data-tab="review">Review<span class="badge" id="review-count" hidden></span></button>
  <button class="tab" data-tab="find">Find firms</button>
  <button class="tab" data-tab="list">Work the list</button>
  <button class="tab" data-tab="emails">Emails &amp; letters</button>
  <button class="tab" data-tab="clients">Clients</button>
  <button class="tab" data-tab="results">Results</button>
  <button class="tab" data-tab="settings">Settings</button>
  <span class="listpick"><label for="sheet">List</label><select id="sheet"></select></span>
</nav>

<main id="layout">
<div class="content">

  <!-- ============================== TODAY -->
  <section data-section="today">
    <div class="glance">
      <button class="tile" data-goto="calls"><b id="todo-calls">–</b><span>on Calls - replies and people who opened their preview</span></button>
      <button class="tile" data-goto="review"><b id="todo-review">–</b><span>to decide on Review</span></button>
      <div class="tile hero"><b id="sent-today"></b><span id="sent-by-inbox"></span><span id="batch-info"></span></div>
    </div>

    <div class="card">
      <h2>1 · Check replies</h2>
      <div class="row"><button class="primary" data-action="replies">Check replies</button><button data-goto="calls">Open Calls →</button></div>
      <p class="hint">Reads your inboxes (read-only). No's are blocked, bounces move to letters, real replies go to Calls.</p>
      <div class="row wrap" style="border-top:1px solid var(--line); padding-top:10px">
        <span id="rw-last" class="hint" style="margin:0; flex:1"></span>
        <button data-action="reply_watch_on">Check every 15 min</button><button class="link" data-action="reply_watch_off">turn off</button>
      </div>
    </div>

    <div class="card">
      <h2>2 · First emails</h2>
      <div class="row">
        <button data-action="batch">Make batch</button>
        <input type="number" id="batch-size" value="20" min="1" max="500" title="How many">
        <select id="batch-scope" style="width:auto"><option value="all">from every list</option><option value="sheet">from this list</option></select>
      </div>
      <div class="row">
        <button data-action="send_test" data-test-kind="batch">Send test to me</button>
        <button class="primary" data-action="send_batch">Send today's batch</button>
      </div>
      <p class="hint">Sends from your own email, 40-90 s apart. Stop any time, press Send again to carry on. Using Mailmeteor? Import <b>mailmeteor-batch-&lt;date&gt;.csv</b> - sends are spotted in your Sent folder automatically (or <button class="link" data-action="batch_sent">mark batch as sent</button>).</p>
    </div>

    <div class="card">
      <h2>3 · Follow-ups</h2>
      <div class="row">
        <button data-action="followups">Make follow-ups</button>
        <input type="number" id="followup-size" value="20" min="1" max="500" title="How many">
        <span class="dim">after</span><input type="number" id="followup-days" value="5" min="1" max="60"><span class="dim">days</span>
      </div>
      <div class="row">
        <button data-action="send_test" data-test-kind="followups">Send test to me</button>
        <button class="primary" data-action="send_followups">Send follow-ups</button>
      </div>
      <p class="hint">One short second email to anyone who hasn't replied or opened their preview - never a third. Mailmeteor: import <b>mailmeteor-followup-&lt;date&gt;.csv</b>, send, then <button class="link" data-action="followups_sent">mark follow-ups as sent</button>.</p>
    </div>

    <div class="card">
      <details id="autopilot-box">
      <summary>Autopilot <span id="ap-state" class="hint"></span></summary>
      <p class="hint">Every day at your time: check replies, find new firms with the saved search, run the list, make the batches, update Excel, text you. It never sends - the PC must be on.</p>
      <div class="grid2">
        <div><label for="ap-time">Time</label><input type="text" id="ap-time" value="07:30"></div>
        <div><label for="ap-batch">Emails a day</label><input type="number" id="ap-batch" value="20" min="1" max="500"></div>
      </div>
      <label class="check"><input type="checkbox" id="ap-followups" checked> Also follow-ups after <input type="number" id="ap-fdays" value="5" min="1" max="60" style="width:52px"> days, up to <input type="number" id="ap-fsize" value="20" min="1" max="500" style="width:60px"></label>
      <p class="hint" id="ap-search">Search: none saved yet.</p>
      <div class="row wrap">
        <button id="ap-use-search">Use the search in Find firms</button>
        <button class="primary" id="ap-on">Save &amp; turn on</button>
        <button id="ap-off">Turn off</button>
        <button data-action="autopilot_now">Run now</button>
      </div>
      <p class="hint" id="ap-last"></p>
      <div class="msg" id="ap-msg"></div>
      </details>
    </div>
  </section>

  <!-- ============================== CALLS -->
  <section data-section="calls" id="pane-calls" hidden>
    <div class="card">
      <div class="row" style="margin:0 0 8px"><button class="primary" data-action="replies">Check replies</button><span class="hint">Replies, people who opened their preview, and call-backs - newest first.</span></div>
      <div class="toast" id="calls-toast"></div>
      <div id="calls"></div>
    </div>
  </section>

  <!-- ============================== REVIEW -->
  <section data-section="review" id="pane-review" hidden>
    <div class="card">
      <p class="hint" style="margin:0 0 8px">Firms the checks weren't sure about. Decide each one - your choice is kept and the sheet is never changed.</p>
      <div class="chips" id="review-filters" style="margin-bottom:8px"></div>
      <div class="toast" id="review-toast"></div>
      <div id="review"></div>
    </div>
  </section>

  <!-- ============================== FIND -->
  <section data-section="find" hidden>
    <div class="card">
      <details id="finder-box" open>
      <summary>Find new prospects</summary>
      <label>Trades</label>
      <div class="chips" id="f-trades">
        <label class="chip"><input type="checkbox" value="roofing" checked> Roofing</label>
        <label class="chip"><input type="checkbox" value="lofts"> Loft conversions</label>
        <label class="chip"><input type="checkbox" value="driveways"> Driveways &amp; patios</label>
        <label class="chip"><input type="checkbox" value="landscaping"> Landscaping</label>
        <label class="chip"><input type="checkbox" value="building"> Building &amp; extensions</label>
      </div>
      <label for="f-areas">Areas</label>
      <input type="text" id="f-areas" placeholder="Guildford, Woking, GU21">
      <p class="hint">Towns or postcode districts, comma separated - matched to where the company is registered.</p>
      <div class="grid2">
        <div>
          <label for="f-age">Company age</label>
          <select id="f-age">
            <option value="any">Any age</option>
            <option value="under6m">Under 6 months (newly registered)</option>
            <option value="under2">Under 2 years</option>
            <option value="2to10">2 to 10 years</option>
            <option value="over10">Over 10 years</option>
          </select>
        </div>
        <div>
          <label for="f-max">Max new firms</label>
          <input type="number" id="f-max" value="100" min="1" max="1000">
        </div>
      </div>
      <details style="margin-top:10px">
        <summary>More filters</summary>
        <label for="f-include">Name must include (any of)</label>
        <input type="text" id="f-include" placeholder="e.g. roof, slate">
        <label for="f-exclude">Leave out names containing</label>
        <input type="text" id="f-exclude" value="holdings, investments, estates, lettings, capital, finance">
        <label class="check"><input type="checkbox" id="f-email-only"> Only firms with an email found</label>
        <label class="check"><input type="checkbox" id="f-website-only"> Only firms with a website found</label>
        <p class="hint">With either ticked, Max counts the firms kept.</p>
        <label class="check"><input type="checkbox" id="f-no-directors"> Skip director names (a little faster)</label>
        <label class="check"><input type="checkbox" id="f-no-websites"> Skip the website search (much faster - every firm goes on the No website tab)</label>
      </details>
      <div class="row" style="margin-top:12px">
        <button data-find="count">Count matches</button>
        <button class="primary" data-find="find" style="flex:1">Find &amp; build list</button>
      </div>
      <p class="hint">Makes a new sheet in outreach/. Firms already in any sheet are skipped, so the same search again gives the next batch.</p>
      <div class="msg" id="find-msg"></div>
      </details>
    </div>
  </section>

  <!-- ============================== WORK THE LIST -->
  <section data-section="list" hidden>
    <div class="card">
      <h2>This list</h2>
      <div class="stats">
        <div class="stat"><b id="s-total">–</b><span>prospects</span></div>
        <div class="stat"><b id="s-checked">–</b><span>speed checked</span></div>
        <div class="stat"><b id="s-failed">–</b><span>couldn't check</span></div>
        <div class="stat"><b id="s-remaining">–</b><span>still to do</span></div>
      </div>
      <div class="bar"><i id="b-ok" style="background:var(--ok)"></i><i id="b-bad" style="background:var(--bad)"></i></div>
      <div class="msg" id="progress-msg"></div>
    </div>

    <div class="card">
      <h2>Do everything</h2>
      <div class="row"><button class="primary" data-action="all">Run the whole list</button><label class="check" style="margin:0"><input type="checkbox" id="dry"> Dry run (nothing sent to the dashboard)</label></div>
      <p class="hint">Company types → missing emails &amp; phones → email checks → trades → speed checks, pushing as it goes. Can take hours; Stop loses nothing.</p>
    </div>

    <div class="card">
      <h2>One step at a time</h2>
      <table class="tools">
        <tr><td><div class="row" style="margin:0"><button data-action="speed">Speed check next</button><input type="number" id="limit" value="10" min="1" max="100"><span class="dim">sites</span></div>
          <label class="check"><input type="checkbox" id="recheck"> Include sites already checked</label></td>
          <td>Google mobile score + website checks, pushed to their preview pages. 20-60 s a site.</td></tr>
        <tr><td><div class="row" style="margin:0"><input type="text" id="only" placeholder="Business or website"><button data-action="one">Check one</button></div></td>
          <td>Speed check just the firms matching this.</td></tr>
        <tr><td><button data-action="companies">Look up company types</button></td><td>Companies House: Ltd/LLP can be emailed, the rest get a letter.</td></tr>
        <tr><td><button data-action="contacts">Find missing emails &amp; phones</button></td><td>From their own site and directors.</td></tr>
        <tr><td><button data-action="emails">Check emails</button></td><td>Dead addresses move to a letter.</td></tr>
        <tr><td><button data-action="trades">Guess missing trades</button></td><td>Reads their homepage.</td></tr>
        <tr><td><button data-action="push">Push to dashboard</button></td><td>Sends names, trades, areas and scores to the dashboard.</td></tr>
        <tr><td><button data-action="links">Refresh preview links</button></td><td>Rewrites the preview-links and Mailmeteor CSVs. Sends nothing.</td></tr>
        <tr><td><button data-action="prepare">Prepare Mailmeteor send</button></td><td>Pushes, then checks every link loads. Import the file when the log says <b>READY</b>.</td></tr>
      </table>
    </div>
  </section>

  <!-- ============================== EMAILS & LETTERS -->
  <section data-section="emails" hidden>
    <div class="card">
      <h2>First email</h2>
      <p class="hint">Fields: {{business}} {{greeting_name}} {{score_line}} {{issue_line}} {{preview_url}} {{trade}} {{area}} {{your_name}}. The score and issue lines are left out when a site wasn't checked.</p>
      <label>Subject</label>
<textarea id="mm-subject" rows="1">A quick look at {{business}}'s website</textarea>
      <label>Body</label>
<textarea id="mm-body" rows="15">Hi {{greeting_name}},

I had a look at {{business}}'s website on my phone and ran it through Google's own speed test. {{score_line}} {{issue_line}}

I build fast, hand-coded websites for trade firms, and I've put together a short preview of what a new site for {{business}} could look like - next to how your current one measures up:

{{preview_url}}

There's nothing to sign up for. If it's of interest, just reply and I'll happily talk it through.

Kind regards,
[your name]
Scalar Digital · 07401 696272 · scalardigital.co.uk

If you'd rather not hear from me again, just reply and say so and I won't get in touch.</textarea>
      <details style="margin-top:8px"><summary>Version B - test a second email (optional)</summary>
        <p class="hint">Fill both and each new firm gets A or B. The Scorecard says which wins - give it 100+ sends each.</p>
        <textarea id="mm-subject-b" rows="1" placeholder="Version B subject"></textarea>
        <textarea id="mm-body-b" rows="12" placeholder="Version B body - same {{fields}}" style="margin-top:6px"></textarea>
      </details>
      <div class="row wrap"><button class="primary" id="em-save">Save</button><button id="em-reset">Back to original</button><button id="mm-copy-subject">Copy subject</button><button id="mm-copy-body">Copy body</button><span class="saved" id="mm-copied"></span></div>
    </div>

    <div class="card">
      <h2>Follow-up email</h2>
<textarea id="fu-subject" rows="1">Following up - {{business}}</textarea>
          <textarea id="fu-body" rows="12" style="margin-top:6px">Hi {{greeting_name}},

Just following up on my note last week about {{business}}'s website. {{issue_line}}

The preview I put together is still here if you'd like a look - no sign-up:

{{preview_url}}

If it's not for you, just reply and say so and I won't get in touch again.

Kind regards,
[your name]
Scalar Digital · 07401 696272</textarea>
      <div class="row"><button id="fu-copy-subject">Copy subject</button><button class="primary" id="fu-copy-body">Copy body</button><span class="saved" id="fu-copied"></span></div>
    </div>

    <div class="card">
      <h2>Saved replies</h2>
      <p class="hint">Used by the Reply box on Calls. Each starts with a line like <code>=== How much? ===</code>. Fields: {{greeting_name}} {{business}} {{your_name}} {{preview_url}} {{booking_link}} {{price_build}} {{price_landing}}.</p>
      <textarea id="sr-text" rows="16"></textarea>
      <div class="row"><button class="primary" id="sr-save">Save replies</button><button id="sr-reset">Back to the originals</button><span class="saved" id="sr-saved"></span></div>
    </div>

    <div class="card">
      <h2>Letters</h2>
      <div class="row"><button class="primary" data-action="letters">Make letters</button><label class="check" style="margin:0"><input type="checkbox" id="letters-all"> Include firms already sent one</label></div>
      <p class="hint" id="letters-links"></p>
      <p class="hint">A print-ready A4 letter for every letter-channel firm, with their score, worst problem and a QR code to their preview.</p>
      <details style="margin-top:6px"><summary>Edit letter text</summary>
        <p class="hint">Fields: {greeting} {business} {website} {score_sentence} {issue_sentence} {trade_plural} {area} {sender_email} {sender_phone} {signoff}</p>
        <label>Firms with a website</label><textarea id="tpl-site" rows="12"></textarea>
        <label>Firms with no website</label><textarea id="tpl-nosite" rows="10"></textarea>
        <div class="row"><button class="primary" id="tpl-save">Save text</button><button id="tpl-reset">Back to the original</button><span class="saved" id="tpl-saved"></span></div>
      </details>
    </div>
  </section>

  <!-- ============================== CLIENTS -->
  <section data-section="clients" hidden>
    <div class="card">
      <h2>Build &amp; publish a client's site</h2>
      <div class="grid3">
        <input type="text" id="publish-folder" placeholder="Folder (e.g. kerr-roofing)">
        <input type="text" id="publish-account" placeholder="Cloudflare account id (first time)">
        <input type="text" id="publish-project" placeholder="Project name (optional)">
      </div>
      <div class="row"><button data-action="build_site">Build site</button><button class="primary" data-action="publish_site">Publish site</button>
        <label class="check" style="margin:0"><input type="checkbox" id="build-draft"> Draft build (hidden from Google)</label></div>
      <ol class="steps">
        <li><b>Draft their site</b> on Calls writes <code>outreach/sites/&lt;folder&gt;/</code> with a brief, proposal and <code>site.json</code>.</li>
        <li>Fill in <code>site.json</code>; anything marked [Confirm] blocks a real build (the log lists it).</li>
        <li><b>Build site</b> makes every page in <code>site/</code>. <b>Publish site</b> puts only that folder live on their Cloudflare. Needs CLOUDFLARE_API_TOKEN and Node.js.</li>
      </ol>
    </div>

    <div class="card">
      <h2>Launch report</h2>
      <div class="grid2"><input type="text" id="launch-old" placeholder="Their old website"><input type="text" id="launch-new" placeholder="New site (if a different domain)"></div>
      <div class="row"><button class="primary" data-action="launch_report">Make launch report</button></div>
      <p class="hint">Old speed score and problems next to the new site measured now. Saved in their folder and added to case-studies.csv.</p>
    </div>
  </section>

  <!-- ============================== RESULTS -->
  <section data-section="results" hidden>
    <div class="card">
      <h2>How it's going</h2>
      <div class="row wrap"><button class="primary" data-action="scorecard">Scorecard</button><button data-action="export">Export to Excel</button><button id="open-results">Open results in Excel</button><button id="open-folder">Open outreach folder</button></div>
      <p class="hint">Scorecard: sent → opened → replied → quoted → won, the money, and letters. Excel: every firm from every list, with your Notes kept. Close the workbook before exporting.</p>
    </div>
    <div class="card">
      <h2>Files in outreach/</h2>
      <ul class="files" id="files"></ul>
    </div>
  </section>

  <!-- ============================== SETTINGS -->
  <section data-section="settings" hidden>
    <div id="settings-box">
    <div class="card">
      <h2>Your details</h2>
      <div class="grid2">
        <div><label>Your name - who emails are from, and the sign-off <code>MAIL_FROM_NAME</code></label><input type="text" id="MAIL_FROM_NAME" placeholder="e.g. Sam Carter"></div>
        <div><label>Booking link <code>BOOKING_LINK</code></label><input type="text" id="BOOKING_LINK" placeholder="e.g. https://cal.com/yourname/15min"></div>
      </div>
      <label>Letters and proposals: signed as / email / phone <code>LETTER_SIGNOFF / LETTER_EMAIL / LETTER_PHONE</code></label>
      <div class="grid3"><input type="text" id="LETTER_SIGNOFF" placeholder="e.g. Scalar Digital"><input type="text" id="LETTER_EMAIL" placeholder="e.g. hello@scalardigital.co.uk"><input type="text" id="LETTER_PHONE" placeholder="e.g. 07401 696272"></div>
    </div>

    <div class="card">
      <h2>Quotes</h2>
      <div class="grid4">
        <div><label>Scalar build £</label><input type="text" id="QUOTE_PRICE_BUILD" placeholder="2500 if blank"></div>
        <div><label>Landing page £</label><input type="text" id="QUOTE_PRICE_LANDING" placeholder="750 if blank"></div>
        <div><label>VAT % (0 or 20)</label><input type="text" id="QUOTE_VAT_RATE" placeholder="0 if blank"></div>
        <div><label>Deposit %</label><input type="text" id="QUOTE_DEPOSIT_PERCENT" placeholder="0 if blank - set 50"></div>
      </div>
      <p class="hint">Used by the Quote buttons on Calls, the terms the client signs, and the proposal. VAT 0 unless you're VAT-registered.</p>
    </div>

    <div class="card">
      <h2>Sending email <span id="set-mail" class="hint"></span></h2>
      <div class="grid2">
        <div><label>Gmail you send from <code>MAIL_ADDRESS</code></label><input type="text" id="MAIL_ADDRESS" placeholder="e.g. you@scalardigital.co.uk"></div>
        <div><label>App password <code>MAIL_APP_PASSWORD</code></label><input type="password" id="MAIL_APP_PASSWORD" placeholder="blank keeps the saved one" autocomplete="off"></div>
      </div>
      <label>Mail server for reading replies <code>MAIL_IMAP_HOST</code></label><input type="text" id="MAIL_IMAP_HOST" placeholder="leave blank for Gmail">
      <p class="hint">Not your normal password: Google Account → Security → 2-Step Verification → App passwords. Replies are only ever read - nothing is marked read, moved or deleted.</p>
      <details style="margin-top:8px"><summary>Extra sending inboxes (optional)</summary>
        <p class="hint">Up to three more inboxes on look-alike domains, warmed up for 3-4 weeks first. Sending is spread across them; follow-ups go from the inbox that sent the first email.</p>
        <div class="grid2"><input type="text" id="MAIL_EXTRA_1_ADDRESS" placeholder="Extra inbox 1"><input type="password" id="MAIL_EXTRA_1_PASSWORD" placeholder="app password (blank keeps the saved one)" autocomplete="off"></div>
        <div class="grid2" style="margin-top:6px"><input type="text" id="MAIL_EXTRA_2_ADDRESS" placeholder="Extra inbox 2"><input type="password" id="MAIL_EXTRA_2_PASSWORD" placeholder="app password" autocomplete="off"></div>
        <div class="grid2" style="margin-top:6px"><input type="text" id="MAIL_EXTRA_3_ADDRESS" placeholder="Extra inbox 3"><input type="password" id="MAIL_EXTRA_3_PASSWORD" placeholder="app password" autocomplete="off"></div>
      </details>
    </div>

    <div class="card">
      <h2>Keys <span class="hint">- blank keeps the saved one</span></h2>
      <div class="grid2">
        <div><label>Dashboard secret <code>PROSPECTS_API_SECRET</code> <span id="set-secret"></span></label><input type="password" id="PROSPECTS_API_SECRET" autocomplete="off"></div>
        <div><label>Google speed test <code>PAGESPEED_API_KEY</code> <span id="set-psi"></span></label><input type="password" id="PAGESPEED_API_KEY" autocomplete="off"></div>
        <div><label>Companies House <code>COMPANIES_HOUSE_API_KEY</code> <span id="set-ch"></span></label><input type="password" id="COMPANIES_HOUSE_API_KEY" autocomplete="off"></div>
        <div><label>Cloudflare, for Publish site <code>CLOUDFLARE_API_TOKEN</code></label><input type="password" id="CLOUDFLARE_API_TOKEN" autocomplete="off"></div>
        <div><label>Phone alerts bot <code>TELEGRAM_BOT_TOKEN</code> <span id="set-tg"></span></label><input type="password" id="TELEGRAM_BOT_TOKEN" autocomplete="off"></div>
        <div><label>Phone alerts chat <code>TELEGRAM_CHAT_ID</code></label><input type="text" id="TELEGRAM_CHAT_ID" placeholder="same as in Vercel"></div>
      </div>
      <p class="hint">Cloudflare token: My Profile → API Tokens → "Edit Cloudflare Workers" template, All accounts. Telegram texts you when a long run finishes.</p>
      <details style="margin-top:8px"><summary>Advanced</summary>
        <div class="grid2">
          <div><label><code>DASHBOARD_API_URL</code></label><input type="text" id="DASHBOARD_API_URL" placeholder="https://admin.scalardigital.co.uk"></div>
          <div><label><code>SITE_URL</code></label><input type="text" id="SITE_URL" placeholder="https://www.scalardigital.co.uk"></div>
          <div><label>Reply texts come from the cloud watch <code>CLOUD_REPLY_ALERTS</code></label><input type="text" id="CLOUD_REPLY_ALERTS" placeholder="yes - once the GitHub reply watch is set up"></div>
        </div>
        <p class="hint">With the cloud reply watch set up (it texts you even with this PC off), put <b>yes</b> here so this PC's reply checks don't text you a second time.</p>
      </details>
    </div>

    <div class="card savebar">
      <div class="row" style="margin:0"><button class="primary" id="save">Save settings</button><span class="saved" id="saved"></span><span class="hint" style="margin:0 0 0 auto">Kept in outreach\panel.env on this computer only.</span></div>
      <div class="msg" id="settings-msg"></div>
    </div>
    </div>
  </section>
</div>

<aside class="output" id="pane-output">
  <h2>Output</h2>
  <pre id="log">Pick a button. What it's doing appears here.</pre>
</aside>
</main>
<script>
const TOKEN = "__TOKEN__";
const $ = (id) => document.getElementById(id);
let state = null, settingsLoaded = false, lastLines = -1, wasRunning = false, polls = 0;

async function post(path, body) {
  const res = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json", "X-Panel-Token": TOKEN }, body: JSON.stringify(body || {}) });
  return res.json().catch(() => ({}));
}

async function loadProgress() {
  const name = $("sheet").value;
  if (!name) return;
  const p = await (await fetch("/api/progress/" + encodeURIComponent(name))).json();
  $("progress-msg").textContent = p.error || "";
  for (const k of ["total", "checked", "failed", "remaining"]) $("s-" + k).textContent = p[k] ?? "–";
  const t = p.total || 0;
  $("b-ok").style.width = t ? (100 * p.checked / t) + "%" : "0";
  $("b-bad").style.width = t ? (100 * p.failed / t) + "%" : "0";
}

function ago(ts) {
  const s = Math.round(Date.now() / 1000 - ts);
  if (s < 60) return "just now";
  if (s < 3600) return Math.round(s / 60) + " min ago";
  if (s < 86400) return Math.round(s / 3600) + " h ago";
  return new Date(ts * 1000).toLocaleDateString();
}

function render() {
  const s = state;
  $("lnk-dash").href = s.dashboard; $("lnk-site").href = s.site;
  const sel = $("sheet");
  const current = sel.value || localStorage.getItem("sheet") || "";
  if (sel.options.length !== s.sheets.length || [...sel.options].some((o, i) => o.value !== s.sheets[i])) {
    sel.innerHTML = s.sheets.map((n) => `<option>${n.replace(/</g, "&lt;")}</option>`).join("") || "<option value=''>No .xlsx in outreach/</option>";
    if (s.sheets.includes(current)) sel.value = current;
    loadProgress();
    loadReview();
    loadLetters();
    loadBatch();
    if (callsWanted()) loadCalls();
  }
  const rw = s.reply_watch;
  $("rw-last").textContent = rw ? `Auto-check: last ran ${rw.at.slice(11)} on ${rw.at.slice(8, 10)}/${rw.at.slice(5, 7)} - ${rw.line}`
    : "Auto-check is off. Turn it on and an interested reply texts you within 15 minutes, 8am-8pm.";
  $("files").innerHTML = s.files.map((f) => `<li>${f.name.replace(/</g, "&lt;")}<span>${ago(f.modified)}</span></li>`).join("") || "<li><span>None yet</span></li>";
  if (!settingsLoaded) {
    settingsLoaded = true;
    $("DASHBOARD_API_URL").value = s.settings.DASHBOARD_API_URL || "";
    $("SITE_URL").value = s.settings.SITE_URL || "";
    $("TELEGRAM_CHAT_ID").value = s.settings.TELEGRAM_CHAT_ID || "";
    for (const k of ["LETTER_SIGNOFF", "LETTER_EMAIL", "LETTER_PHONE", "MAIL_ADDRESS", "MAIL_IMAP_HOST", "MAIL_FROM_NAME", "MAIL_EXTRA_1_ADDRESS", "MAIL_EXTRA_2_ADDRESS", "MAIL_EXTRA_3_ADDRESS", "QUOTE_PRICE_BUILD", "QUOTE_PRICE_LANDING", "QUOTE_VAT_RATE", "QUOTE_DEPOSIT_PERCENT", "BOOKING_LINK", "CLOUD_REPLY_ALERTS"]) $(k).value = s.settings[k] || "";
    quotePrices = { build: s.settings.QUOTE_PRICE_BUILD || "2500", landing: s.settings.QUOTE_PRICE_LANDING || "750" };
    if (!s.settings.PROSPECTS_API_SECRET) showTab("settings");  // nothing works until it's set
  }
  $("set-secret").textContent = s.settings.PROSPECTS_API_SECRET ? "(saved)" : "(not set)";
  $("set-psi").textContent = s.settings.PAGESPEED_API_KEY ? "(saved)" : "(not set - needed for speed checks)";
  $("set-mail").textContent = s.settings.MAIL_APP_PASSWORD ? "(saved)" : "(lets the panel send your emails and read replies)";
  $("set-tg").textContent = s.settings.TELEGRAM_BOT_TOKEN ? "(saved)" : "(optional)";
  $("set-ch").textContent = s.settings.COMPANIES_HOUSE_API_KEY ? "(saved)" : "(not set - free at developer.company-information.service.gov.uk)";

  const j = s.job;
  $("dot").className = "dot " + (j.running ? "run" : j.exit_code === 0 ? "ok" : j.exit_code != null ? "bad" : "");
  $("job-label").textContent = j.label || "Nothing running";
  $("job-time").textContent = j.started ? (j.running ? "started " : "ran ") + ago(j.started) : "";
  $("stop").disabled = !j.running;
  document.querySelectorAll("[data-action], [data-find]").forEach((b) => (b.disabled = j.running));
  // A finished search: switch the List to the sheet it just made.
  if (wasRunning && !j.running && j.label === "Find new prospects" && j.exit_code === 0 && s.latest_sheet && s.sheets.includes(s.latest_sheet)) {
    sel.value = s.latest_sheet;
    try { localStorage.setItem("sheet", sel.value); } catch (e) {}
  }
  if (j.lines.length && j.seq !== lastLines) {
    const log = $("log");
    const atBottom = log.scrollHeight - log.scrollTop - log.clientHeight < 40;
    log.textContent = j.lines.join("\n");
    if (atBottom || lastLines === -1) log.scrollTop = log.scrollHeight;
    lastLines = j.seq;
  }
  if ((wasRunning && !j.running) || (j.running && ++polls % 15 === 0)) loadProgress();
  if (wasRunning && !j.running) { loadReview(); loadLetters(); loadBatch(); loadAutopilot(); if (callsWanted()) loadCalls(); }
  wasRunning = j.running;
}

async function poll() {
  try { state = await (await fetch("/api/state")).json(); render(); } catch (e) { $("job-label").textContent = "Panel stopped - run it again"; }
  setTimeout(poll, state && state.job.running ? 700 : 2500);
}

document.querySelectorAll("[data-action]").forEach((b) => b.addEventListener("click", async () => {
  const action = b.dataset.action;
  const dry = $("dry").checked;
  if (action === "push" && !dry && !confirm("Push this sheet to the dashboard?")) return;
  if (action === "all" && !confirm("Run the whole list? It pushes to the dashboard as it goes and can take hours on a long list.")) return;
  $("run-msg").textContent = "";
  if (action === "followups_sent" && !confirm("Mark the follow-up batch as sent? Do this once Mailmeteor has sent it.")) return;
  if (action === "batch_sent" && !confirm("Mark the last batch as sent? Do this once Mailmeteor has sent it - they won't be picked again.")) return;
  if (action === "send_batch" && !confirm("Send today's batch now, from your own email? It takes about half an hour for 20 - you can stop it any time.")) return;
  if (action === "send_followups" && !confirm("Send the follow-ups now, from your own email?")) return;
  if (action === "publish_site" && !confirm(`Publish outreach/sites/${$("publish-folder").value}/site live on their Cloudflare?`)) return;
  const r = await post("/api/run", { action, sheet: $("sheet").value, dry_run: dry, limit: $("limit").value, recheck: $("recheck").checked, only: $("only").value, letters_all: $("letters-all").checked,
    batch_size: $("batch-size").value, batch_scope: $("batch-scope").value, followup_size: $("followup-size").value, followup_days: $("followup-days").value, test_kind: b.dataset.testKind || "",
    launch_old: $("launch-old").value, launch_new: $("launch-new").value,
    publish_folder: $("publish-folder").value, publish_account: $("publish-account").value, publish_project: $("publish-project").value,
    build_draft: $("build-draft").checked });
  if (r.error) $("run-msg").textContent = r.error;
  lastLines = -1;
  setTimeout(poll, 150);
}));
const FINDER_FIELDS = ["f-areas", "f-age", "f-max", "f-include", "f-exclude"];
const FINDER_CHECKS = ["f-email-only", "f-website-only", "f-no-directors", "f-no-websites"];
function finderForm() {
  return {
    trades: [...document.querySelectorAll("#f-trades input:checked")].map((i) => i.value),
    areas: $("f-areas").value, age: $("f-age").value, max: $("f-max").value,
    include: $("f-include").value, exclude: $("f-exclude").value,
    email_only: $("f-email-only").checked, website_only: $("f-website-only").checked, no_directors: $("f-no-directors").checked, no_websites: $("f-no-websites").checked,
  };
}
function saveFinder() {
  try { localStorage.setItem("finder", JSON.stringify(finderForm())); } catch (e) {}
}
(function restoreFinder() {
  let f = null;
  try { f = JSON.parse(localStorage.getItem("finder") || "null"); } catch (e) {}
  if (!f) return;
  document.querySelectorAll("#f-trades input").forEach((i) => (i.checked = (f.trades || []).includes(i.value)));
  $("f-areas").value = f.areas || ""; $("f-age").value = f.age || "any"; $("f-max").value = f.max || 100;
  $("f-include").value = f.include || ""; if (f.exclude != null) $("f-exclude").value = f.exclude;
  $("f-email-only").checked = !!f.email_only; $("f-website-only").checked = !!f.website_only; $("f-no-directors").checked = !!f.no_directors; $("f-no-websites").checked = !!f.no_websites;
})();
document.querySelectorAll("[data-find]").forEach((b) => b.addEventListener("click", async () => {
  saveFinder();
  $("find-msg").textContent = "";
  const r = await post("/api/run", { action: b.dataset.find, ...finderForm() });
  if (r.error) $("find-msg").textContent = r.error;
  lastLines = -1;
  setTimeout(poll, 150);
}));

$("f-areas").addEventListener("keydown", (e) => { if (e.key === "Enter") document.querySelector('[data-find="count"]').click(); });
// ---- Mailmeteor template
for (const [btn, box, note] of [["mm-copy-subject", "mm-subject", "mm-copied"], ["mm-copy-body", "mm-body", "mm-copied"], ["fu-copy-subject", "fu-subject", "fu-copied"], ["fu-copy-body", "fu-body", "fu-copied"]]) {
  $(btn).addEventListener("click", async () => {
    try { await navigator.clipboard.writeText($(box).value); } catch (e) { $(box).select(); document.execCommand("copy"); }
    $(note).textContent = "Copied"; setTimeout(() => ($(note).textContent = ""), 2000);
  });
}

// ---- Calls
const LETTER_WAIT = 7;
let callData = { callbacks: [], viewing: [], letters: [], outcomes: [] };
const sheetOf = (item) => (item && item.sheet) || $("sheet").value;
// What a reply asks for -> the saved reply that answers it (matched on its name, which you can edit).
const INTENT_LABEL = { price: "asks the price", call: "wants a call", info: "wants more info", later: "not right now" };
const INTENT_REPLY = { price: /much|price|cost/i, call: /call/i, info: /how does|work|more/i, later: /not right now|later|not now/i };
function suggestedReply(intent) {
  const re = INTENT_REPLY[intent];
  return re ? savedReplies.find((n) => re.test(n)) || "" : "";
}
function agoIso(iso) { return iso ? ago(new Date(iso).getTime() / 1000) : ""; }
async function loadCalls() {
  const name = $("sheet").value;
  if (!name) return;
  callData = await (await fetch("/api/calls/" + encodeURIComponent(name))).json();
  renderCalls();
}
function callRow(i, section) {
  const phone = i.phone ? `<a href="tel:${esc(i.phone.replace(/\s/g, ""))}" style="font-size:14px">📞 ${esc(i.phone)}</a>` : '<span class="hint">no phone - check their site</span>';
  const views = i.views ? ` · opened their preview ${i.views} time${i.views === 1 ? "" : "s"}, last ${esc(agoIso(i.last_viewed))}` : "";
  const seen = section === "replied"
    ? `<b style="color:var(--ok)">${i.kind === "interested" ? "Sounds interested" : "Wrote back"}</b>${i.intent ? ` <span class="kind">${esc(INTENT_LABEL[i.intent] || i.intent)}</span>` : ""} ${esc(agoIso(i.replied_at))} · ${esc(i.email)}${views}<br><i>"${esc(i.snippet)}"</i>`
    : section === "callbacks"
    ? `<b style="color:var(--warn)">Call back ${i.overdue ? `- ${i.overdue} day${i.overdue === 1 ? "" : "s"} overdue` : "today"}</b>${i.note ? ` · "${esc(i.note)}"` : ""}${views}`
    : section === "viewing"
    ? `<b style="color:var(--ok)">${i.views} visit${i.views === 1 ? "" : "s"}</b> · last ${esc(agoIso(i.last_viewed))}`
    : `letter posted ${i.waited} days ago · not opened yet`;
  const last = i.last_call ? ` · last call: ${esc(i.last_call)} ${esc(agoIso(i.last_call_at))}` : "";
  return `<div class="ritem" data-key="${esc(i.key)}" data-sec="${section}">
    <div class="top"><b>${esc(i.business)}</b>${i.contact ? `<span class="hint">${esc(i.contact)}</span>` : ""}${phone}
      ${i.preview ? `<a href="${esc(i.preview)}" target="_blank" rel="noopener">their preview ↗</a>` : ""}
      <a href="https://${esc(i.website)}" target="_blank" rel="noopener">${esc(i.website)} ↗</a></div>
    <div class="why">${seen}${last}</div>
    <div class="btns">${(callData.outcomes || []).map((o) => `<button data-outcome="${esc(o)}" ${o === "Not interested" ? 'class="danger"' : o === "Interested" || o === "Won" ? 'class="primary"' : ""}>${esc(o)}</button>`).join("")}
      <input type="text" placeholder="note (optional)" data-note></div>
    <div class="btns" style="margin-top:6px"><button class="primary" data-quote="build">Quote: Scalar build £${esc(Number(quotePrices.build).toLocaleString())}</button><button data-quote="landing">Quote: landing page £${esc(Number(quotePrices.landing).toLocaleString())}</button><label class="hint" title="One of the first three Scalar builds: 24 months' free dashboard, the speed guarantee, first in the queue - for a case study, video and review"><input type="checkbox" data-founding> founding client</label><button data-draft>Draft their site</button></div>
    <div class="why" data-quote-result></div>
    ${section === "replied" && i.email ? `<div class="btns" style="margin-top:6px">
      ${suggestedReply(i.intent) ? `<button class="primary" data-reply-suggest="${esc(suggestedReply(i.intent))}">Suggested reply: ${esc(suggestedReply(i.intent))}</button>` : ""}
      ${i.intent === "later" ? `<button data-callback-in="3m">Call back in 3 months</button>` : ""}
      <select data-reply-pick><option value="">Reply with a saved answer...</option>${savedReplies.map((n) => `<option>${esc(n)}</option>`).join("")}</select></div>
      <div data-reply-box hidden style="margin-top:6px"><textarea data-reply-text rows="9" style="width:100%"></textarea>
      <div class="btns"><button class="primary" data-reply-send>Send reply to ${esc(i.email)}</button><span class="hint" data-reply-msg></span></div></div>` : ""}
  </div>`;
}
function renderCalls() {
  const n = (callData.viewing || []).length + (callData.replied || []).length + (callData.callbacks || []).length;
  $("calls-count").hidden = !n; $("calls-count").textContent = n; $("todo-calls").textContent = n;
  const msg = callData.message
    ? `<div class="ritem"><b>${esc(callData.message)}</b><div class="why">The call list needs one small, read-only addition to your dashboard: a list of who opened their preview. Until it's live the call list stays empty - nothing else is affected.</div></div>` : "";
  const tps = '<p class="hint">Check each number against <a href="https://www.tpsonline.org.uk/" target="_blank" rel="noopener" style="color:var(--accent)">TPS / CTPS</a> before you call.</p>';
  const rp = (callData.replied || []).map((i) => callRow(i, "replied")).join("");
  const cb = (callData.callbacks || []).map((i) => callRow(i, "callbacks")).join("");
  const v = (callData.viewing || []).map((i) => callRow(i, "viewing")).join("") || '<p class="hint">Nobody new has opened their preview since your last calls.</p>';
  const l = (callData.letters || []).map((i) => callRow(i, "letters")).join("") || '<p class="hint">No letters waiting on a follow-up.</p>';
  $("calls").innerHTML = msg + tps
    + (cb ? `<h2 style="font-size:12px;color:var(--warn);text-transform:uppercase;letter-spacing:.06em">Call-backs due</h2>` + cb : "")
    + (rp ? `<h2 style="font-size:12px;color:var(--ok);text-transform:uppercase;letter-spacing:.06em">Replied to your email - answer these first</h2>` + rp : "") + `<h2 style="font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:.06em">Looking at their preview - hottest first</h2>` + v
    + `<h2 style="font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:.06em;margin-top:18px">Letter follow-ups (${LETTER_WAIT} days+, not opened)</h2>` + l;
  document.querySelectorAll("#calls [data-outcome]").forEach((b) => b.addEventListener("click", () => callOutcome(b)));
  document.querySelectorAll("#calls [data-quote]").forEach((b) => b.addEventListener("click", () => makeQuote(b)));
  document.querySelectorAll("#calls [data-draft]").forEach((b) => b.addEventListener("click", () => draftSite(b)));
  document.querySelectorAll("#calls [data-reply-pick]").forEach((sel) => sel.addEventListener("change", () => pickReply(sel)));
  document.querySelectorAll("#calls [data-reply-send]").forEach((b) => b.addEventListener("click", () => sendReply(b)));
  document.querySelectorAll("#calls [data-reply-suggest]").forEach((b) => b.addEventListener("click", () => {
    const sel = b.closest(".ritem").querySelector("[data-reply-pick]");
    sel.value = b.dataset.replySuggest; pickReply(sel);
  }));
  document.querySelectorAll("#calls [data-callback-in]").forEach((b) => b.addEventListener("click", () => callOutcome(b, b.dataset.callbackIn)));
}
let savedReplies = [];
async function loadSavedReplies() {
  const r = await (await fetch("/api/reply-templates")).json();
  savedReplies = r.names || [];
  if ($("sr-text")) $("sr-text").value = r.text || "";
  if (typeof callData !== "undefined" && callData && (callData.replied || []).length) renderCalls();
}
function replyItem(el) {
  const card = el.closest(".ritem");
  return [card, (callData[card.dataset.sec] || []).find((x) => x.key === card.dataset.key)];
}
async function pickReply(sel) {
  const [card, item] = replyItem(sel);
  if (!sel.value) return;
  const r = await post("/api/reply-draft", { name: sel.value, business: item.business, contact: item.contact, preview: item.preview });
  const box = card.querySelector("[data-reply-box]");
  box.hidden = false;
  if (r.error) { card.querySelector("[data-reply-msg]").textContent = r.error; return; }
  card.querySelector("[data-reply-text]").value = r.text;
}
async function sendReply(b) {
  const [card, item] = replyItem(b);
  const text = card.querySelector("[data-reply-text]").value;
  if (!text.trim() || !confirm(`Send this reply to ${item.email}?`)) return;
  b.disabled = true; b.textContent = "Sending...";
  const r = await post("/api/reply-send", { sheet: sheetOf(item), key: item.key, business: item.business, to: item.email,
    message_id: item.message_id, subject: item.subject, text, name: card.querySelector("[data-reply-pick]").value });
  b.disabled = false; b.textContent = "Send reply";
  const msg = card.querySelector("[data-reply-msg]");
  msg.style.color = r.error ? "var(--bad)" : "var(--ok)";
  msg.textContent = r.error || r.message;
  if (!r.error) setTimeout(loadCalls, 2500);
}
loadSavedReplies();
async function draftSite(b) {
  const card = b.closest(".ritem");
  const item = (callData[card.dataset.sec] || []).find((x) => x.key === card.dataset.key);
  b.disabled = true; b.textContent = "Reading their site...";
  const r = await post("/api/draft-site", { sheet: sheetOf(item), key: item.key, business: item.business, website: item.website,
    email: item.email, phone: item.phone, contact: item.contact });
  b.disabled = false; b.textContent = "Draft their site";
  const box = card.querySelector("[data-quote-result]");
  box.style.color = r.error ? "var(--bad)" : "var(--ok)";
  box.textContent = r.error || r.message;
}
let quotePrices = { build: "2500", landing: "750" };
async function makeQuote(b) {
  const card = b.closest(".ritem");
  const item = (callData[card.dataset.sec] || []).find((x) => x.key === card.dataset.key);
  const founding = b.dataset.quote === "build" && !!card.querySelector("[data-founding]")?.checked;
  const label = b.dataset.quote === "build" ? (founding ? "founding-client Scalar build" : "Scalar build") : "landing page";
  if (!confirm(`Make a ${label} quote for ${item.business}? It's added to your dashboard as a sent quote - you send the link.`)) return;
  b.disabled = true;
  const r = await post("/api/quote", { sheet: sheetOf(item), key: item.key, business: item.business, email: item.email,
    phone: item.phone, website: item.website, contact: item.contact, package: b.dataset.quote,
    founding });
  b.disabled = false;
  const box = card.querySelector("[data-quote-result]");
  if (r.error) { box.style.color = "var(--bad)"; box.textContent = r.error; return; }
  box.style.color = "var(--ok)";
  box.innerHTML = `Quote ${esc(r.quote_number)} (£${Number(r.total).toLocaleString()}) is ready: <a href="${esc(r.url)}" target="_blank" rel="noopener">open it ↗</a>
    <button data-copy="${esc(r.url)}">Copy link</button> <button class="primary" data-send-quote>Email it to them${item.email ? " (" + esc(item.email) + ")" : ""}</button>
    <a href="${esc(r.mailto)}" class="hint">or open in your mail app</a>${r.proposal ? ' <button data-open-proposal>Open proposal</button>' : ""} <span data-sent></span>`;
  const openBtn = box.querySelector("[data-open-proposal]");
  if (openBtn) openBtn.addEventListener("click", async () => {
    const o = await post("/api/proposal-open", { key: item.key, quote_number: r.quote_number });
    const note = box.querySelector("[data-sent]");
    note.style.color = o.ok ? "var(--ok)" : "var(--bad)";
    note.textContent = o.error || o.message;
  });
  box.querySelector("[data-send-quote]").addEventListener("click", async (e) => {
    const btn = e.target;
    let to = item.email;
    if (!to) to = (prompt(`Email address to send ${item.business}'s quote to:`) || "").trim();
    if (!to) return;
    btn.disabled = true; btn.textContent = "Sending...";
    const s = await post("/api/quote-email", { sheet: sheetOf(item), key: item.key, to, contact: item.contact, quote_number: r.quote_number });
    btn.disabled = false; btn.textContent = s.ok ? "Sent" : "Email it to them";
    const note = box.querySelector("[data-sent]");
    note.style.color = s.ok ? "var(--ok)" : "var(--bad)";
    note.textContent = s.error || s.message;
  });
  box.querySelector("[data-copy]").addEventListener("click", async (e) => {
    try { await navigator.clipboard.writeText(e.target.dataset.copy); e.target.textContent = "Copied"; } catch (err) {}
  });
}
async function callOutcome(b, dueIn) {
  const card = b.closest(".ritem");
  const list = callData[card.dataset.sec] || [];
  const item = list.find((x) => x.key === card.dataset.key);
  const outcome = dueIn ? "Call back" : b.dataset.outcome;
  if (outcome === "Not interested" && !confirm(`${item.business}: not interested? They won't be contacted again, from any list.`)) return;
  let due = dueIn || "";
  if (outcome === "Call back" && !due) {
    due = prompt(`Call ${item.business} back when?\n3d = 3 days, 2w = 2 weeks, 3m = 3 months, tomorrow, or a date (2026-11-03)`, "3d");
    if (!due) return;
  }
  const r = await post("/api/calls", { sheet: sheetOf(item), key: item.key, business: item.business, outcome, due,
    note: card.querySelector("[data-note]").value, website: item.website, email: item.email });
  $("calls-toast").style.color = r.error ? "var(--bad)" : "var(--ok)";
  $("calls-toast").textContent = r.error || r.message;
  if (!r.error) loadCalls();
}
setInterval(() => { if (callsWanted()) loadCalls(); }, 60000);

// ---- Autopilot
let apSearch = null;
function describeSearch(f) {
  if (!f || !f.trades || !f.trades.length) return "Search: none saved yet - fill in Find new prospects, then press Use the search.";
  return `Search: ${f.trades.join(", ")} in ${f.areas} - up to ${f.max} new firms a day${f.email_only ? ", only with an email" : ""}.`;
}
async function loadAutopilot() {
  const r = await (await fetch("/api/autopilot")).json();
  const c = r.config || {};
  $("ap-time").value = c.time || "07:30"; $("ap-batch").value = c.batch_size || 20;
  $("ap-followups").checked = c.followups !== false; $("ap-fdays").value = c.followup_after_days || 5; $("ap-fsize").value = c.followup_size || 20;
  apSearch = c.find || null;
  $("ap-search").textContent = describeSearch(apSearch);
  $("ap-state").textContent = r.running ? "· running now" : c.enabled ? `· on, daily at ${c.time}` : "· off";
  $("ap-last").textContent = r.last || "";
  if (!r.windows) $("ap-on").title = "Scheduling needs Windows";
}
async function saveAutopilot(action) {
  const config = { time: $("ap-time").value.trim(), batch_size: $("ap-batch").value, followups: $("ap-followups").checked,
    followup_after_days: $("ap-fdays").value, followup_size: $("ap-fsize").value, ...(apSearch ? { find: apSearch } : {}) };
  const r = await post("/api/autopilot", { action, config });
  $("ap-msg").style.color = r.error ? "var(--bad)" : "var(--ok)";
  $("ap-msg").textContent = r.error || r.message;
  loadAutopilot();
}
$("ap-use-search").addEventListener("click", () => {
  apSearch = finderForm();
  $("ap-search").textContent = describeSearch(apSearch) + " (press Save & turn on to keep it)";
});
$("ap-on").addEventListener("click", () => saveAutopilot("on"));
$("ap-off").addEventListener("click", () => saveAutopilot("off"));
loadAutopilot();

// ---- Email batches
async function loadBatch() {
  const q = `?sheet=${encodeURIComponent($("sheet").value || "")}&scope=${$("batch-scope").value}`;
  const r = await (await fetch("/api/batch" + q)).json();
  $("batch-info").textContent = `${r.remaining} waiting to be emailed.` + (r.pending ? ` Last batch not marked as sent yet: ${r.pending}.` : "");
  const t = r.today;
  if (t) {
    $("sent-today").textContent = `Sent today: ${t.sent} of ${t.cap} · ${t.left} left today`;
    $("sent-by-inbox").textContent = t.by_inbox.map(b => `${b.inbox}: ${b.sent} sent, ${b.left} left`).join("  ·  ");
  }
}
$("batch-scope").addEventListener("change", loadBatch);
// Keeps "Sent today" current while the panel is open - and lets the server tick off a Mailmeteor
// batch from the Sent folder as it goes out.
setInterval(() => { if (!document.hidden) loadBatch(); }, 120000);

// ---- Letters
async function loadLetters() {
  const name = $("sheet").value;
  if (!name) return;
  const r = await (await fetch("/api/letters/" + encodeURIComponent(name))).json();
  const bits = [];
  if (r.segno === false) bits.push('<button data-action-install>Install segno first</button>');
  if (r.page) bits.push(`<a href="/letters/${encodeURIComponent(r.page)}" target="_blank" rel="noopener" style="color:var(--accent)">Open letters ↗</a>`);
  if (r.batch) bits.push(`<button data-posted>Mark ${r.batch} as posted</button>`);
  $("letters-links").innerHTML = bits.join(" ");
  const inst = document.querySelector("[data-action-install]");
  if (inst) inst.addEventListener("click", async () => { await post("/api/run", { action: "install_segno" }); lastLines = -1; showTab("output"); setTimeout(poll, 150); });
  const posted = document.querySelector("[data-posted]");
  if (posted) posted.addEventListener("click", async () => {
    if (!confirm(`Mark these ${r.batch} letters as posted today? They'll be left out of future batches.`)) return;
    const res = await post("/api/letters/posted", { sheet: name });
    $("run-msg").style.color = res.error ? "var(--bad)" : "var(--ok)";
    $("run-msg").textContent = res.error || res.message;
    loadLetters();
  });
}
async function loadEmailTemplates() {
  const t = await (await fetch("/api/email-template")).json();
  $("mm-subject").value = t.first_subject; $("mm-body").value = t.first_body;
  $("fu-subject").value = t.followup_subject; $("fu-body").value = t.followup_body;
  $("mm-subject-b").value = t.first_subject_b || ""; $("mm-body-b").value = t.first_body_b || "";
}
loadEmailTemplates();
$("em-save").addEventListener("click", async () => {
  const r = await post("/api/email-template", { first_subject: $("mm-subject").value, first_body: $("mm-body").value,
    followup_subject: $("fu-subject").value, followup_body: $("fu-body").value,
    first_subject_b: $("mm-subject-b").value, first_body_b: $("mm-body-b").value });
  $("mm-copied").textContent = r.error || "Saved"; setTimeout(() => ($("mm-copied").textContent = ""), r.error ? 8000 : 2500);
});
$("sr-save").addEventListener("click", async () => {
  const r = await post("/api/reply-templates", { text: $("sr-text").value });
  $("sr-saved").textContent = r.error || "Saved"; setTimeout(() => ($("sr-saved").textContent = ""), r.error ? 8000 : 2500);
  if (!r.error) loadSavedReplies();
});
$("sr-reset").addEventListener("click", async () => {
  if (!confirm("Put the saved replies back to the originals?")) return;
  await post("/api/reply-templates", { reset: true });
  loadSavedReplies();
});
$("em-reset").addEventListener("click", async () => {
  if (!confirm("Put both emails back to the original text?")) return;
  await post("/api/email-template", { reset: true });
  loadEmailTemplates();
});
(async function loadTemplates() {
  const t = await (await fetch("/api/letter-template")).json();
  $("tpl-site").value = t.with_site || ""; $("tpl-nosite").value = t.no_site || "";
})();
$("tpl-save").addEventListener("click", async () => {
  const r = await post("/api/letter-template", { with_site: $("tpl-site").value, no_site: $("tpl-nosite").value });
  $("tpl-saved").textContent = r.error || "Saved"; setTimeout(() => ($("tpl-saved").textContent = ""), 2500);
});
$("tpl-reset").addEventListener("click", async () => {
  if (!confirm("Put both letters back to the original text?")) return;
  await post("/api/letter-template", { reset: true });
  const t = await (await fetch("/api/letter-template")).json();
  $("tpl-site").value = t.with_site; $("tpl-nosite").value = t.no_site;
});

// ---- Review tab
let reviewItems = [], reviewKinds = {}, reviewFilter = "all";
function esc(t) { return String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
// One section on screen at a time; the output log sits beside the tool sections and the
// job bar in the header shows what's running from anywhere.
const SECTIONS = [...document.querySelectorAll("[data-section]")].map((el) => el.dataset.section);
const WIDE = new Set(["calls", "review"]);
function showTab(name) {
  if (name === "output") name = WIDE.has(currentTab) ? "today" : currentTab;  // "show me the log"
  if (!SECTIONS.includes(name)) name = "today";
  currentTab = name;
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("on", t.dataset.tab === name));
  document.querySelectorAll("[data-section]").forEach((el) => { el.hidden = el.dataset.section !== name; });
  $("layout").classList.toggle("wide", WIDE.has(name));
  try { localStorage.setItem("tab", name); } catch (e) {}
  if (history.replaceState) history.replaceState(null, "", "#tab-" + name);
  if (name === "review") loadReview();
  if (name === "calls") loadCalls();
}
let currentTab = "today";
function callsWanted() { return currentTab === "calls" || currentTab === "today"; }  // Today shows the count
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));
document.querySelectorAll("[data-goto]").forEach((b) => b.addEventListener("click", () => showTab(b.dataset.goto)));
async function loadReview() {
  const name = $("sheet").value;
  if (!name) return;
  const r = await (await fetch("/api/review/" + encodeURIComponent(name))).json();
  reviewItems = r.items || []; reviewKinds = r.kinds || reviewKinds;
  if (r.error) $("review-toast").textContent = r.error;
  renderReview();
}
function renderReview() {
  const n = reviewItems.length;
  $("review-count").hidden = !n; $("review-count").textContent = n; $("todo-review").textContent = n;
  const counts = {};
  reviewItems.forEach((i) => (counts[i.kind] = (counts[i.kind] || 0) + 1));
  if (reviewFilter !== "all" && !counts[reviewFilter]) reviewFilter = "all";
  $("review-filters").innerHTML = [["all", "All", n], ...Object.keys(reviewKinds).filter((k) => counts[k]).map((k) => [k, reviewKinds[k], counts[k]])]
    .map(([k, label, c]) => `<label class="chip"><input type="radio" name="rf" value="${k}" ${k === reviewFilter ? "checked" : ""}> ${esc(label)} (${c})</label>`).join("");
  document.querySelectorAll('#review-filters input').forEach((i) => i.addEventListener("change", () => { reviewFilter = i.value; renderReview(); }));
  const shown = reviewItems.filter((i) => reviewFilter === "all" || i.kind === reviewFilter);
  if (!shown.length) { $("review").innerHTML = '<p class="hint">Nothing needs a decision on this list.</p>'; return; }
  const failed = counts.failed ? `<div class="ritem"><div class="btns"><button data-rall="retry">Retry all ${counts.failed} failed speed checks</button><span class="hint">Sites are often just down for a while.</span></div></div>` : "";
  $("review").innerHTML = (reviewFilter === "all" || reviewFilter === "failed" ? failed : "") + shown.map((i, idx) => {
    const site = i.website ? `<a href="https://${esc(i.website)}" target="_blank" rel="noopener">${esc(i.website)} ↗</a>` : "";
    const ch = `<a href="${esc(i.ch_search)}" target="_blank" rel="noopener">Companies House ↗</a>`;
    let btns = "";
    if (i.kind === "website") btns = `<a href="https://${esc(i.possible)}" target="_blank" rel="noopener">${esc(i.possible)} ↗</a> <button class="primary" data-act="website_yes" data-value="${esc(i.possible)}">Yes, it's theirs</button><button data-act="website_no">Not theirs</button>`;
    if (i.kind === "company") btns = ["Ltd", "LLP", "Sole trader", "Partnership"].map((t) => `<button data-act="set_type" data-value="${t}">${t}</button>`).join("");
    if (i.kind === "email") btns = `<input type="text" value="${esc(i.email)}" data-email><button data-act="set_email">Save email</button><button data-act="set_email" data-value="">No email - send a letter</button>`;
    if (i.kind === "closed") btns = `<button data-act="keep_closed">Still trading - keep them</button>`;
    return `<div class="ritem" data-idx="${reviewItems.indexOf(i)}">
      <div class="top"><span class="kind">${esc(reviewKinds[i.kind] || i.kind)}</span><b>${esc(i.business)}</b>${site}${ch}</div>
      <div class="why">${esc(i.detail)}${i.email && i.kind !== "email" ? " · " + esc(i.email) : ""}${i.phone ? " · " + esc(i.phone) : ""}</div>
      <div class="btns">${btns}<button data-act="skip">Leave out</button><button class="danger" data-act="block">Do not contact</button></div>
    </div>`;
  }).join("");
  document.querySelectorAll("#review [data-act]").forEach((b) => b.addEventListener("click", () => reviewDecide(b)));
  document.querySelectorAll("#review [data-rall]").forEach((b) => b.addEventListener("click", async () => {
    const r = await post("/api/run", { action: "retry", sheet: $("sheet").value });
    if (r.error) $("review-toast").textContent = r.error; else { showTab("output"); lastLines = -1; setTimeout(poll, 150); }
  }));
}
async function reviewDecide(b) {
  const card = b.closest(".ritem"), item = reviewItems[+card.dataset.idx];
  const act = b.dataset.act;
  if (act === "block" && !confirm(`Never contact ${item.business} again, from any list?`)) return;
  let value = b.dataset.value;
  if (act === "set_email" && value === undefined) value = card.querySelector("[data-email]").value.trim();
  const body = act === "block"
    ? { sheet: $("sheet").value, action: "block", business: item.business, website: item.website, email: item.email }
    : { sheet: $("sheet").value, action: act, key: item.key, value: value ?? "" };
  const r = await post("/api/review", body);
  $("review-toast").textContent = r.error ? r.error : `${item.business}: ${r.message}`;
  $("review-toast").style.color = r.error ? "var(--bad)" : "var(--ok)";
  if (!r.error) {
    // One decision settles the firm: drop every item for it (block also covers other lists).
    reviewItems = reviewItems.filter((x) => x.key !== item.key);
    renderReview();
    loadProgress();
  }
}
$("stop").addEventListener("click", () => post("/api/stop"));
$("open-folder").addEventListener("click", () => post("/api/open-folder"));
$("open-results").addEventListener("click", async () => { const r = await post("/api/open-results"); if (r.error) { $("run-msg").style.color = "var(--bad)"; $("run-msg").textContent = r.error; } });
$("sheet").addEventListener("change", () => { try { localStorage.setItem("sheet", $("sheet").value); } catch (e) {} loadProgress(); loadReview(); loadLetters(); if (callsWanted()) loadCalls(); });
$("save").addEventListener("click", async () => {
  const body = {};
  for (const k of ["PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "LETTER_SIGNOFF", "LETTER_EMAIL", "LETTER_PHONE", "MAIL_ADDRESS", "MAIL_APP_PASSWORD", "MAIL_IMAP_HOST", "MAIL_FROM_NAME", "MAIL_EXTRA_1_ADDRESS", "MAIL_EXTRA_1_PASSWORD", "MAIL_EXTRA_2_ADDRESS", "MAIL_EXTRA_2_PASSWORD", "MAIL_EXTRA_3_ADDRESS", "MAIL_EXTRA_3_PASSWORD", "QUOTE_PRICE_BUILD", "QUOTE_PRICE_LANDING", "QUOTE_VAT_RATE", "QUOTE_DEPOSIT_PERCENT", "DASHBOARD_API_URL", "SITE_URL", "BOOKING_LINK", "CLOUDFLARE_API_TOKEN", "CLOUD_REPLY_ALERTS"]) body[k] = $(k).value;
  const r = await post("/api/settings", body);
  for (const k of ["PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "TELEGRAM_BOT_TOKEN", "MAIL_APP_PASSWORD", "MAIL_EXTRA_1_PASSWORD", "MAIL_EXTRA_2_PASSWORD", "MAIL_EXTRA_3_PASSWORD"]) $(k).value = "";
  $("saved").textContent = "Saved"; setTimeout(() => ($("saved").textContent = ""), 2000);
  $("settings-msg").textContent = r.warning ? "Saved, but " + r.warning + "." : "";
});
{
  let saved = "";
  try { saved = localStorage.getItem("tab") || ""; } catch (e) {}
  showTab(location.hash.startsWith("#tab-") ? location.hash.slice(5) : saved || "today");
}
poll();
</script>
</body>
</html>
"""


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
