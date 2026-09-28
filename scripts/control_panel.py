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
AUTOPILOT = HERE / "autopilot.py"
SEND = HERE / "send_email.py"
LAUNCH = HERE / "launch_report.py"


def replies_first(settings: dict[str, str]) -> list:
    """Check replies before anything that picks who to contact - if the inbox is set up."""
    return [(REPLIES, [])] if settings.get("MAIL_ADDRESS") and settings.get("MAIL_APP_PASSWORD") else []
RESULTS_NAME = "outreach-results.xlsx"
SETTING_KEYS = [
    "PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    "LETTER_SIGNOFF", "LETTER_EMAIL", "LETTER_PHONE", "MAIL_ADDRESS", "MAIL_APP_PASSWORD", "MAIL_IMAP_HOST", "MAIL_FROM_NAME",
    "QUOTE_PRICE_BUILD", "QUOTE_PRICE_LANDING", "QUOTE_VAT_RATE", "QUOTE_DEPOSIT_PERCENT",
    "DASHBOARD_API_URL", "SITE_URL",
]
SECRET_KEYS = {"PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "TELEGRAM_BOT_TOKEN", "MAIL_APP_PASSWORD"}
# A run this long gets a phone alert when it ends (if Telegram is set up).
ALERT_AFTER_S = 180
RUN_ALL_BATCH = 10
# Shown in the header. Bump it with every change, so an old panel still running is obvious.
PANEL_VERSION = "29"
MAX_LOG_LINES = 5000


def outreach_dir() -> Path:
    # Same rule as push_prospects.py: this checkout, or the main one when run from a worktree.
    for parent in [HERE.parent, *HERE.parents]:
        if (parent / "outreach").is_dir():
            return parent / "outreach"
    return HERE.parent / "outreach"


OUTREACH = outreach_dir()
SETTINGS_FILE = OUTREACH / "panel.env"


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
    "followups": "Make follow-up batch",
    "followups_sent": "Mark follow-ups as sent",
    "autopilot_now": "Autopilot (run now)",
    "batch_sent": "Mark batch as sent",
    "send_batch": "Send today's batch",
    "send_followups": "Send follow-ups",
    "send_test": "Send a test to yourself",
    "launch_report": "Launch report",
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
    if action == "launch_report":
        from push_prospects import domain_of

        old, new = str(body.get("launch_old") or "").strip().lower(), str(body.get("launch_new") or "").strip().lower()
        old, new = domain_of(old), domain_of(new or old)
        if not (old and DOMAIN.match(old) and new and DOMAIN.match(new)):
            return None, "Type their old website (and the new one if it's a different domain), e.g. kerrroofing.co.uk"
        if not settings.get("PAGESPEED_API_KEY"):
            return None, "Add PAGESPEED_API_KEY in Settings first."
        return (lambda job: [(LAUNCH, ["--old", old, "--new", new])]), ""
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
    try:
        result = quotes.create_quote(settings, business, email, phone, package, slug)
    except quotes.QuoteFailed as e:
        return {"error": f"No quote made: {e}."}, 502
    quotes.record(OUTREACH, sheet, key, business, package, result)
    calls.log_call(OUTREACH, sheet, key, business, "Quoted", result.get("quote_number", ""))
    calls.mark_reply_handled(OUTREACH, business)
    signoff = settings.get("MAIL_FROM_NAME") or settings.get("LETTER_SIGNOFF") or "Scalar Digital"
    return {"ok": True, "quote_number": result.get("quote_number"), "total": (result.get("total_pence") or 0) / 100,
            "url": result["quote_url"], "mailto": quotes.email_link(email, str(body.get("contact") or ""), business, result, signoff)}, 200


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


def call_action(body: dict) -> tuple[dict, int]:
    import calls
    from contact_rules import add_to_blocklist

    sheet = str(body.get("sheet") or "")
    key = str(body.get("key") or "")
    outcome = str(body.get("outcome") or "")
    business = str(body.get("business") or "")[:150]
    if not sheet_path(sheet) or not REVIEW_KEY.match(key) or outcome not in calls.OUTCOMES or not business:
        return {"error": "That doesn't look right."}, 400
    note = str(body.get("note") or "")[:300]
    calls.log_call(OUTREACH, sheet, key, business, outcome, note)
    calls.mark_reply_handled(OUTREACH, business)
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
            return self._json({"remaining": email_batches.remaining(OUTREACH, scope) if OUTREACH.is_dir() else 0, "pending": batch})
        if route == "/api/email-template":
            import send_email

            return self._json(send_email.load_templates(OUTREACH))
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
            problem = send_email.save_templates(OUTREACH, {k: str(body.get(k) or "") for k in send_email.DEFAULT_TEMPLATES})
            return self._json({"error": problem}, 400) if problem else self._json({"ok": True})
        if route == "/api/quote":
            return self._json(*quote_action(body))
        if route == "/api/calls":
            return self._json(*call_action(body))
        if route == "/api/quote-email":
            return self._json(*quote_email_action(body))
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
  header { display:flex; align-items:center; gap:16px; padding:14px 20px; border-bottom:1px solid var(--line); flex-wrap:wrap; }
  header h1 { font-size:16px; margin:0; margin-right:auto; }
  header a { color:var(--dim); text-decoration:none; } header a:hover { color:var(--text); }
  main { display:grid; grid-template-columns: 380px 1fr; gap:16px; padding:16px 20px; }
  @media (max-width: 900px) { main { grid-template-columns: 1fr; } }
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
  pre { margin:0; background:#0b0d11; border:1px solid var(--line); border-radius:8px; padding:12px; height:calc(100vh - 260px); min-height:320px; overflow:auto; white-space:pre-wrap; word-break:break-word; font:12.5px/1.5 ui-monospace, Consolas, monospace; }
  .status { display:flex; align-items:center; gap:10px; margin-bottom:10px; }
  .dot { width:9px; height:9px; border-radius:50%; background:var(--dim); }
  .dot.run { background:var(--warn); animation:pulse 1s infinite; } .dot.ok { background:var(--ok); } .dot.bad { background:var(--bad); }
  @keyframes pulse { 50% { opacity:.3; } }
  .files { list-style:none; margin:0; padding:0; font-size:13px; }
  .files li { display:flex; justify-content:space-between; padding:3px 0; border-bottom:1px dashed var(--line); }
  .files span { color:var(--dim); }
  .msg { color:var(--bad); font-size:13px; margin-top:8px; min-height:1em; }
  .saved { color:var(--ok); font-size:12px; }
  details summary { cursor:pointer; color:var(--dim); font-size:12px; text-transform:uppercase; letter-spacing:.06em; }
  .chips { display:flex; flex-wrap:wrap; gap:6px; }
  .chip { display:inline-flex; align-items:center; gap:5px; margin:0; padding:5px 9px; border:1px solid var(--line); border-radius:999px; color:var(--text); font-size:13px; cursor:pointer; user-select:none; }
  .chip:has(input:checked) { border-color:var(--accent); background:rgba(79,140,255,.14); }
  .chip input { margin:0; accent-color:var(--accent); }
  .grid2 { display:grid; grid-template-columns:1fr 1fr; gap:8px; }
  .hint { color:var(--dim); font-size:12px; margin:4px 0 0; }
  .card.find { border-color:rgba(79,140,255,.45); }
  .tabs { display:flex; gap:4px; margin-bottom:10px; border-bottom:1px solid var(--line); }
  .tab { background:none; border:0; border-bottom:2px solid transparent; border-radius:0; padding:8px 12px; color:var(--dim); }
  .tab.on { color:var(--text); border-bottom-color:var(--accent); }
  .badge { display:inline-block; min-width:18px; padding:0 6px; margin-left:6px; border-radius:9px; background:var(--warn); color:#111; font-size:11px; font-weight:700; }
  #review { height:calc(100vh - 260px); min-height:320px; overflow:auto; }
  .ritem { border:1px solid var(--line); border-radius:8px; padding:10px 12px; margin-bottom:8px; background:#0f1115; }
  .ritem .top { display:flex; gap:10px; align-items:baseline; flex-wrap:wrap; }
  .ritem b { font-size:14px; } .ritem a { color:var(--accent); font-size:12px; text-decoration:none; }
  .ritem .why { color:var(--dim); font-size:12px; margin:4px 0 8px; }
  .ritem .btns { display:flex; gap:6px; flex-wrap:wrap; align-items:center; }
  .ritem .btns button { padding:5px 9px; font-size:12px; }
  .ritem input { width:auto; flex:1; min-width:180px; padding:5px 8px; }
  .kind { font-size:11px; color:var(--warn); text-transform:uppercase; letter-spacing:.05em; }
  .toast { color:var(--ok); font-size:12px; min-height:1em; margin-bottom:6px; }
  summary.card-title { font-size:12px; font-weight:700; color:var(--dim); list-style-position:inside; }
</style>
</head>
<body>
<header>
  <h1>Prospect Control Panel <span style="color:var(--dim); font-weight:400; font-size:12px">v__VERSION__ · __HERE__</span></h1>
  <a id="lnk-dash" href="#" target="_blank" rel="noopener">Dashboard ↗</a>
  <a id="lnk-site" href="#" target="_blank" rel="noopener">Website ↗</a>
  <a href="https://pagespeed.web.dev/" target="_blank" rel="noopener">PageSpeed ↗</a>
  <a href="https://mailmeteor.com/" target="_blank" rel="noopener">Mailmeteor ↗</a>
  <a href="https://www.tpsonline.org.uk/" target="_blank" rel="noopener">TPS check ↗</a>
</header>
<main>
  <div>
    <div class="card find">
      <details id="finder-box" open>
      <summary class="card-title">Find new prospects</summary>
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
      <p class="hint">Towns or postcode districts, separated by commas. Matched against where the company is registered.</p>
      <div class="grid2">
        <div>
          <label for="f-age">Company age</label>
          <select id="f-age">
            <option value="any">Any age</option>
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
        <p class="hint">With either ticked, Max counts the firms kept - it keeps looking until it has that many.</p>
        <label class="check"><input type="checkbox" id="f-no-directors"> Skip director names (a little faster)</label>
        <label class="check"><input type="checkbox" id="f-no-websites"> Skip the website search (much faster - every firm goes on the No website tab)</label>
      </details>
      <div class="row" style="margin-top:12px">
        <button data-find="count">Count matches</button>
        <button class="primary" data-find="find" style="flex:1">Find &amp; build list</button>
      </div>
      <p class="hint">Makes a new sheet in outreach/ - your existing sheets are never changed, and firms already in any of them are skipped, so running the same search again gives you the next batch.</p>
      <div class="msg" id="find-msg"></div>
      </details>
    </div>

    <div class="card">
      <details id="autopilot-box">
      <summary class="card-title">Autopilot <span id="ap-state" class="hint"></span></summary>
      <p class="hint">Every day at your time: check replies, run the saved search for new firms, run the whole list, make today's email batch and follow-ups, update the Excel export, and text you. It never sends an email - you import the READY files and send. The PC must be on.</p>
      <div class="grid2">
        <div><label for="ap-time">Time</label><input type="text" id="ap-time" value="07:30"></div>
        <div><label for="ap-batch">Emails a day</label><input type="number" id="ap-batch" value="20" min="1" max="500"></div>
      </div>
      <label class="check"><input type="checkbox" id="ap-followups" checked> Also make follow-ups (after <input type="number" id="ap-fdays" value="5" min="1" max="60" style="width:52px"> days, up to <input type="number" id="ap-fsize" value="20" min="1" max="500" style="width:60px">)</label>
      <p class="hint" id="ap-search">Search: none saved yet.</p>
      <div class="row" style="flex-wrap:wrap">
        <button id="ap-use-search">Use the search in Find new prospects</button>
        <button class="primary" id="ap-on">Save &amp; turn on</button>
        <button id="ap-off">Turn off</button>
        <button data-action="autopilot_now">Run now</button>
      </div>
      <p class="hint" id="ap-last"></p>
      <div class="msg" id="ap-msg"></div>
      </details>
    </div>

    <div class="card">
      <h2>List</h2>
      <select id="sheet"></select>
      <div class="stats" style="margin-top:10px">
        <div class="stat"><b id="s-total">–</b><span>prospects</span></div>
        <div class="stat"><b id="s-checked">–</b><span>speed checked</span></div>
        <div class="stat"><b id="s-failed">–</b><span>couldn't check</span></div>
        <div class="stat"><b id="s-remaining">–</b><span>still to do</span></div>
      </div>
      <div class="bar"><i id="b-ok" style="background:var(--ok)"></i><i id="b-bad" style="background:var(--bad)"></i></div>
      <div class="msg" id="progress-msg"></div>
    </div>

    <div class="card">
      <h2>Run</h2>
      <div class="action">
        <button class="primary" data-action="all">Run the whole list</button>
        <p>Looks up company types, finds missing emails &amp; phones, checks emails, guesses trades, then speed checks every site left (4 at once, pushed every 10). Keeps the PC awake; start it and walk away - Stop loses nothing.</p>
      </div>
      <label class="check" style="margin:14px 0 4px; border-top:1px solid var(--line); padding-top:10px"><input type="checkbox" id="dry"> Dry run - write the CSVs, send nothing to the dashboard</label>

      <div class="action">
        <div class="row" style="margin:0"><button data-action="speed">Speed check next</button><input type="number" id="limit" value="10" min="1" max="100"><span style="color:var(--dim)">sites</span></div>
        <label class="check"><input type="checkbox" id="recheck"> Include sites already checked</label>
        <p>Google mobile score + LCP and the website teardown, then pushed to their preview pages. ~20-60s a site.</p>
      </div>
      <div class="action">
        <div class="row" style="margin:0"><input type="text" id="only" placeholder="Business name or website"><button data-action="one">Check one</button></div>
        <p>Speed check + teardown on just the firms matching this text.</p>
      </div>
      <div class="action">
        <button class="primary" data-action="prepare">Prepare Mailmeteor send</button>
        <p>Pushes this sheet, then opens every link in the Mailmeteor file (not counted as a visit) and takes out any that don't load. When the log ends with <b>READY</b>, import the file into Mailmeteor and schedule.</p>
      </div>
      <div class="action">
        <div class="row" style="margin:0"><button data-action="batch">Make email batch</button><input type="number" id="batch-size" value="20" min="1" max="500"><select id="batch-scope" style="width:auto"><option value="all">from every list</option><option value="sheet">from this list</option></select></div>
        <p>The next firms not yet emailed, every link re-checked (the autopilot makes one each morning). <span id="batch-info"></span></p>
        <div class="row"><button data-action="send_test" data-test-kind="batch">Send a test to yourself</button><button class="primary" data-action="send_batch">Send today's batch</button></div>
        <p class="hint">Sends from your own email, 40-90 seconds apart (about half an hour for 20), each recorded as it goes - stop any time and press Send again to carry on. Anyone who said no or replied since is left out. Using Mailmeteor instead? Import <b>mailmeteor-batch-&lt;date&gt;.csv</b>, send, then <button data-action="batch_sent" style="padding:2px 8px">Mark batch as sent</button></p>
      </div>
      <div class="action">
        <div class="row" style="margin:0"><button data-action="followups">Make follow-up batch</button><input type="number" id="followup-size" value="20" min="1" max="500"><span class="hint">after</span><input type="number" id="followup-days" value="5" min="1" max="60" style="width:60px"><span class="hint">days</span></div>
        <p>One short second email to firms who haven't replied or opened their preview (those who opened it are on your Calls list - ring them instead). Never a third. It goes as a reply in the same thread as the first email.</p>
        <div class="row"><button data-action="send_test" data-test-kind="followups">Send a test to yourself</button><button class="primary" data-action="send_followups">Send follow-ups</button></div>
        <p class="hint">Using Mailmeteor instead? Import <b>mailmeteor-followup-&lt;date&gt;.csv</b> with the follow-up email below, send, then <button data-action="followups_sent" style="padding:2px 8px">Mark follow-ups as sent</button></p>
        <details style="margin-top:6px"><summary>Follow-up email (edit here - Send uses it)</summary>
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
        </details>
      </div>
      <div class="action">
        <button data-action="links">Refresh preview links + Mailmeteor CSV</button>
        <p>Rewrites preview-links and mailmeteor CSVs from the sheet. Never sends anything - and the Mailmeteor file only includes firms whose preview page is on your dashboard, so no email links to a 404. Push first to add new firms.</p>
        <details style="margin-top:6px"><summary>First email (edit here - Send uses it)</summary>
          <p class="hint">Subject</p>
          <textarea id="mm-subject" rows="1">A quick look at {{business}}'s website</textarea>
          <p class="hint">Body - {{score_line}} and {{issue_line}} are whole sentences, left empty when a site hasn't been checked, so it always reads right.</p>
          <textarea id="mm-body" rows="15">Hi {{greeting_name}},

I had a look at {{business}}'s website on my phone and ran it through Google's own speed test. {{score_line}} {{issue_line}}

I build fast, hand-coded websites for trade firms, and I've put together a short preview of what a new site for {{business}} could look like - next to how your current one measures up:

{{preview_url}}

There's nothing to sign up for. If it's of interest, just reply and I'll happily talk it through.

Kind regards,
[your name]
Scalar Digital · 07401 696272 · scalardigital.co.uk

If you'd rather not hear from me again, just reply and say so and I won't get in touch.</textarea>
          <div class="row"><button class="primary" id="em-save">Save both emails</button><button id="em-reset">Back to original</button><button id="mm-copy-subject">Copy subject</button><button id="mm-copy-body">Copy body</button><span class="saved" id="mm-copied"></span></div>
          <p class="hint">Fields: {{business}} {{greeting_name}} {{score_line}} {{issue_line}} {{preview_url}} {{trade}} {{area}} {{your_name}} (MAIL_FROM_NAME in Settings). For Mailmeteor, copy and swap {{your_name}} for your name.</p>
        </details>
      </div>
      <div class="action">
        <div class="row" style="margin:0"><input type="text" id="launch-old" placeholder="Their old website"><input type="text" id="launch-new" placeholder="New site (if a different domain)"><button data-action="launch_report">Launch report</button></div>
        <p>When a client's new site goes live: their old speed score and problems (from when you first checked them) next to the new site measured now. Writes a report for them in <b>outreach/sites/&lt;firm&gt;/</b> and adds a line to <b>case-studies.csv</b> - your proof for the next pitch.</p>
      </div>
      <div class="action">
        <button data-action="contacts">Find missing emails &amp; phones</button>
        <p>For firms with a blank email, phone or contact name: reads their own site, and takes the contact from their directors once Look up company types has confirmed them. Your sheet is never changed.</p>
      </div>
      <div class="action">
        <button data-action="emails">Check emails</button>
        <p>Finds addresses that can't take mail (typos, dead domains) and moves them to a letter. Free, a second or two each.</p>
      </div>
      <div class="action">
        <button data-action="companies">Look up company types</button>
        <p>Fills blank Company types from Companies House: Ltd/LLP can be emailed, the rest get a letter. Unsure = letter. Dissolved firms are left out.</p>
      </div>
      <div class="action">
        <button data-action="trades">Guess missing trades</button>
        <p>Reads each homepage with no Trade in the sheet, guesses one, and pushes it.</p>
      </div>
      <div class="action">
        <div class="row" style="margin:0"><button data-action="letters">Make letters</button><span id="letters-links" class="hint"></span></div>
        <label class="check"><input type="checkbox" id="letters-all"> Include firms already sent one</label>
        <p>A print-ready A4 letter for every letter-channel firm (and a finder sheet's No website tab): their address in the envelope window, their speed score and worst problem, and a QR code to their preview page. Also pushes, so every code works.</p>
        <details style="margin-top:6px"><summary>Edit letter text</summary>
          <p class="hint">Filled in per firm: {greeting} {business} {website} {score_sentence} {issue_sentence} {trade_plural} {area} {sender_email} {sender_phone} {signoff}</p>
          <label>Firms with a website</label><textarea id="tpl-site" rows="12"></textarea>
          <label>Firms with no website</label><textarea id="tpl-nosite" rows="10"></textarea>
          <div class="row"><button class="primary" id="tpl-save">Save text</button><button id="tpl-reset">Back to the original</button><span class="saved" id="tpl-saved"></span></div>
        </details>
      </div>
      <div class="action">
        <button data-action="push">Push to dashboard</button>
        <p>Sends the sheet's changes (names, trades, areas, scores) to the dashboard.</p>
      </div>
      <div class="msg" id="run-msg"></div>
    </div>

    <div class="card">
      <div style="display:flex; justify-content:space-between; align-items:center"><h2 style="margin:0">Files in outreach/</h2><button id="open-folder">Open folder</button></div>
      <div class="row" style="margin-top:10px"><button class="primary" data-action="export">Export to Excel</button><button id="open-results">Open results in Excel</button></div>
      <p class="hint">One workbook for every list: outreach-results.xlsx, grouped by the date each firm was added, with a Notes column that's kept every time. Also updated automatically at the end of Run the whole list and Prepare Mailmeteor send. Close it in Excel before exporting.</p>
      <ul class="files" id="files" style="margin-top:10px"></ul>
    </div>

    <div class="card">
      <details id="settings-box">
        <summary>Settings</summary>
        <label>PROSPECTS_API_SECRET <span id="set-secret"></span></label>
        <input type="password" id="PROSPECTS_API_SECRET" placeholder="leave blank to keep the saved one" autocomplete="off">
        <label>PAGESPEED_API_KEY <span id="set-psi"></span></label>
        <input type="password" id="PAGESPEED_API_KEY" placeholder="leave blank to keep the saved one" autocomplete="off">
        <label>COMPANIES_HOUSE_API_KEY <span id="set-ch"></span></label>
        <input type="password" id="COMPANIES_HOUSE_API_KEY" placeholder="leave blank to keep the saved one" autocomplete="off">
        <label>TELEGRAM_BOT_TOKEN <span id="set-tg"></span></label>
        <input type="password" id="TELEGRAM_BOT_TOKEN" placeholder="leave blank to keep the saved one" autocomplete="off">
        <label>TELEGRAM_CHAT_ID</label>
        <input type="text" id="TELEGRAM_CHAT_ID" placeholder="same as in Vercel">
        <p class="hint">Optional: a phone alert when a run longer than 3 minutes finishes. Use the same bot and chat as the website's preview alerts.</p>
        <label>MAIL_ADDRESS / MAIL_APP_PASSWORD <span id="set-mail"></span></label>
        <div class="grid2"><input type="text" id="MAIL_ADDRESS" placeholder="the Gmail you send from"><input type="password" id="MAIL_APP_PASSWORD" placeholder="app password (blank keeps the saved one)" autocomplete="off"></div>
        <div class="grid2" style="margin-top:6px"><input type="text" id="MAIL_FROM_NAME" placeholder="Your name (who emails are from, and the sign-off)"><input type="text" id="MAIL_IMAP_HOST" placeholder="imap.gmail.com (leave blank for Gmail)"></div>
        <p class="hint">For "Check replies". Not your normal password: Google Account &gt; Security &gt; 2-Step Verification &gt; App passwords. It only ever reads - nothing is marked read, moved or deleted.</p>
        <label>Quotes: build £ / landing page £ / VAT % / deposit %</label>
        <div class="grid2" style="grid-template-columns:1fr 1fr 1fr 1fr"><input type="text" id="QUOTE_PRICE_BUILD" placeholder="2500"><input type="text" id="QUOTE_PRICE_LANDING" placeholder="750"><input type="text" id="QUOTE_VAT_RATE" placeholder="0"><input type="text" id="QUOTE_DEPOSIT_PERCENT" placeholder="0"></div>
        <p class="hint">For the Calls tab's Quote buttons. VAT: 0 if you're not VAT-registered, 20 if you are.</p>
        <label>LETTER_SIGNOFF / LETTER_EMAIL / LETTER_PHONE</label>
        <div class="grid2" style="grid-template-columns:1fr 1fr 1fr"><input type="text" id="LETTER_SIGNOFF" placeholder="Scalar Digital"><input type="text" id="LETTER_EMAIL" placeholder="hello@scalardigital.co.uk"><input type="text" id="LETTER_PHONE" placeholder="07401 696272"></div>
        <p class="hint">Who the letters are from: the name they're signed with, and the email and phone they give.</p>
        <label>DASHBOARD_API_URL (optional)</label>
        <input type="text" id="DASHBOARD_API_URL" placeholder="https://admin.scalardigital.co.uk">
        <label>SITE_URL (optional)</label>
        <input type="text" id="SITE_URL" placeholder="https://www.scalardigital.co.uk">
        <div class="row"><button class="primary" id="save">Save</button><span class="saved" id="saved"></span></div>
        <div class="msg" id="settings-msg"></div>
        <p style="color:var(--dim); font-size:12px">Saved to __OUTREACH__\panel.env on this computer only.</p>
      </details>
    </div>
  </div>

  <div class="card" style="margin-bottom:0">
    <div class="tabs">
      <button class="tab on" data-tab="output">Output</button>
      <button class="tab" data-tab="review">Review<span class="badge" id="review-count" hidden></span></button>
      <button class="tab" data-tab="calls">Calls<span class="badge" id="calls-count" hidden style="background:var(--ok)"></span></button>
    </div>
    <div id="pane-output">
      <div class="status"><span class="dot" id="dot"></span><b id="job-label">Nothing running</b><span id="job-time" style="color:var(--dim)"></span><span style="margin-left:auto"></span><button class="danger" id="stop" disabled>Stop</button></div>
      <pre id="log">Pick a button on the left. Output appears here.</pre>
    </div>
    <div id="pane-calls" hidden>
      <div class="row" style="margin:0 0 8px"><button data-action="replies">Check replies</button><span class="hint">Reads your inbox (read-only): no's are blocked, bounces move to letters, real replies land here.</span></div>
      <div class="toast" id="calls-toast"></div>
      <div id="calls" style="height:calc(100vh - 230px); min-height:320px; overflow:auto"></div>
    </div>
    <div id="pane-review" hidden>
      <div class="chips" id="review-filters" style="margin-bottom:8px"></div>
      <div class="toast" id="review-toast"></div>
      <div id="review"></div>
    </div>
  </div>
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
    if (!$("pane-calls").hidden) loadCalls();
  }
  $("files").innerHTML = s.files.map((f) => `<li>${f.name.replace(/</g, "&lt;")}<span>${ago(f.modified)}</span></li>`).join("") || "<li><span>None yet</span></li>";
  if (!settingsLoaded) {
    settingsLoaded = true;
    $("DASHBOARD_API_URL").value = s.settings.DASHBOARD_API_URL || "";
    $("SITE_URL").value = s.settings.SITE_URL || "";
    $("TELEGRAM_CHAT_ID").value = s.settings.TELEGRAM_CHAT_ID || "";
    for (const k of ["LETTER_SIGNOFF", "LETTER_EMAIL", "LETTER_PHONE", "MAIL_ADDRESS", "MAIL_IMAP_HOST", "MAIL_FROM_NAME", "QUOTE_PRICE_BUILD", "QUOTE_PRICE_LANDING", "QUOTE_VAT_RATE", "QUOTE_DEPOSIT_PERCENT"]) $(k).value = s.settings[k] || "";
    quotePrices = { build: s.settings.QUOTE_PRICE_BUILD || "2500", landing: s.settings.QUOTE_PRICE_LANDING || "750" };
    if (!s.settings.PROSPECTS_API_SECRET) $("settings-box").open = true;
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
  if (wasRunning && !j.running) { loadReview(); loadLetters(); loadBatch(); loadAutopilot(); if (!$("pane-calls").hidden) loadCalls(); }
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
  const r = await post("/api/run", { action, sheet: $("sheet").value, dry_run: dry, limit: $("limit").value, recheck: $("recheck").checked, only: $("only").value, letters_all: $("letters-all").checked,
    batch_size: $("batch-size").value, batch_scope: $("batch-scope").value, followup_size: $("followup-size").value, followup_days: $("followup-days").value, test_kind: b.dataset.testKind || "",
    launch_old: $("launch-old").value, launch_new: $("launch-new").value });
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
try { if (localStorage.getItem("finderOpen") === "0") $("finder-box").open = false; } catch (e) {}
$("finder-box").addEventListener("toggle", () => { try { localStorage.setItem("finderOpen", $("finder-box").open ? "1" : "0"); } catch (e) {} });
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
let callData = { viewing: [], letters: [], outcomes: [] };
function agoIso(iso) { return iso ? ago(new Date(iso).getTime() / 1000) : ""; }
async function loadCalls() {
  const name = $("sheet").value;
  if (!name) return;
  callData = await (await fetch("/api/calls/" + encodeURIComponent(name))).json();
  renderCalls();
}
function callRow(i, section) {
  const phone = i.phone ? `<a href="tel:${esc(i.phone.replace(/\s/g, ""))}" style="font-size:14px">📞 ${esc(i.phone)}</a>` : '<span class="hint">no phone - check their site</span>';
  const seen = section === "replied"
    ? `<b style="color:var(--ok)">${i.kind === "interested" ? "Sounds interested" : "Wrote back"}</b> ${esc(agoIso(i.replied_at))} · ${esc(i.email)}<br><i>"${esc(i.snippet)}"</i>`
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
    <div class="btns" style="margin-top:6px"><button class="primary" data-quote="build">Quote: Scalar build £${esc(Number(quotePrices.build).toLocaleString())}</button><button data-quote="landing">Quote: landing page £${esc(Number(quotePrices.landing).toLocaleString())}</button><button data-draft>Draft their site</button></div>
    <div class="why" data-quote-result></div>
  </div>`;
}
function renderCalls() {
  const n = (callData.viewing || []).length + (callData.replied || []).length;
  $("calls-count").hidden = !n; $("calls-count").textContent = n;
  const msg = callData.message
    ? `<div class="ritem"><b>${esc(callData.message)}</b><div class="why">The call list needs one small, read-only addition to your dashboard: a list of who opened their preview. Until it's live the call list stays empty - nothing else is affected.</div></div>` : "";
  const tps = '<p class="hint">Check each number against <a href="https://www.tpsonline.org.uk/" target="_blank" rel="noopener" style="color:var(--accent)">TPS / CTPS</a> before you call.</p>';
  const rp = (callData.replied || []).map((i) => callRow(i, "replied")).join("");
  const v = (callData.viewing || []).map((i) => callRow(i, "viewing")).join("") || '<p class="hint">Nobody new has opened their preview since your last calls.</p>';
  const l = (callData.letters || []).map((i) => callRow(i, "letters")).join("") || '<p class="hint">No letters waiting on a follow-up.</p>';
  $("calls").innerHTML = msg + tps + (rp ? `<h2 style="font-size:12px;color:var(--ok);text-transform:uppercase;letter-spacing:.06em">Replied to your email - answer these first</h2>` + rp : "") + `<h2 style="font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:.06em">Looking at their preview - hottest first</h2>` + v
    + `<h2 style="font-size:12px;color:var(--dim);text-transform:uppercase;letter-spacing:.06em;margin-top:18px">Letter follow-ups (${LETTER_WAIT} days+, not opened)</h2>` + l;
  document.querySelectorAll("#calls [data-outcome]").forEach((b) => b.addEventListener("click", () => callOutcome(b)));
  document.querySelectorAll("#calls [data-quote]").forEach((b) => b.addEventListener("click", () => makeQuote(b)));
  document.querySelectorAll("#calls [data-draft]").forEach((b) => b.addEventListener("click", () => draftSite(b)));
}
async function draftSite(b) {
  const card = b.closest(".ritem");
  const item = (callData[card.dataset.sec] || []).find((x) => x.key === card.dataset.key);
  b.disabled = true; b.textContent = "Reading their site...";
  const r = await post("/api/draft-site", { sheet: $("sheet").value, key: item.key, business: item.business, website: item.website,
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
  const label = b.dataset.quote === "build" ? "Scalar build" : "landing page";
  if (!confirm(`Make a ${label} quote for ${item.business}? It's added to your dashboard as a sent quote - you send the link.`)) return;
  b.disabled = true;
  const r = await post("/api/quote", { sheet: $("sheet").value, key: item.key, business: item.business, email: item.email,
    phone: item.phone, website: item.website, contact: item.contact, package: b.dataset.quote });
  b.disabled = false;
  const box = card.querySelector("[data-quote-result]");
  if (r.error) { box.style.color = "var(--bad)"; box.textContent = r.error; return; }
  box.style.color = "var(--ok)";
  box.innerHTML = `Quote ${esc(r.quote_number)} (£${Number(r.total).toLocaleString()}) is ready: <a href="${esc(r.url)}" target="_blank" rel="noopener">open it ↗</a>
    <button data-copy="${esc(r.url)}">Copy link</button> <button class="primary" data-send-quote>Email it to them${item.email ? " (" + esc(item.email) + ")" : ""}</button>
    <a href="${esc(r.mailto)}" class="hint">or open in your mail app</a> <span data-sent></span>`;
  box.querySelector("[data-send-quote]").addEventListener("click", async (e) => {
    const btn = e.target;
    let to = item.email;
    if (!to) to = (prompt(`Email address to send ${item.business}'s quote to:`) || "").trim();
    if (!to) return;
    btn.disabled = true; btn.textContent = "Sending...";
    const s = await post("/api/quote-email", { sheet: $("sheet").value, key: item.key, to, contact: item.contact, quote_number: r.quote_number });
    btn.disabled = false; btn.textContent = s.ok ? "Sent" : "Email it to them";
    const note = box.querySelector("[data-sent]");
    note.style.color = s.ok ? "var(--ok)" : "var(--bad)";
    note.textContent = s.error || s.message;
  });
  box.querySelector("[data-copy]").addEventListener("click", async (e) => {
    try { await navigator.clipboard.writeText(e.target.dataset.copy); e.target.textContent = "Copied"; } catch (err) {}
  });
}
async function callOutcome(b) {
  const card = b.closest(".ritem");
  const list = callData[card.dataset.sec] || [];
  const item = list.find((x) => x.key === card.dataset.key);
  const outcome = b.dataset.outcome;
  if (outcome === "Not interested" && !confirm(`${item.business}: not interested? They won't be contacted again, from any list.`)) return;
  const r = await post("/api/calls", { sheet: $("sheet").value, key: item.key, business: item.business, outcome,
    note: card.querySelector("[data-note]").value, website: item.website, email: item.email });
  $("calls-toast").style.color = r.error ? "var(--bad)" : "var(--ok)";
  $("calls-toast").textContent = r.error || r.message;
  if (!r.error) loadCalls();
}
setInterval(() => { if (!$("pane-calls").hidden) loadCalls(); }, 60000);

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
}
$("batch-scope").addEventListener("change", loadBatch);

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
}
loadEmailTemplates();
$("em-save").addEventListener("click", async () => {
  const r = await post("/api/email-template", { first_subject: $("mm-subject").value, first_body: $("mm-body").value,
    followup_subject: $("fu-subject").value, followup_body: $("fu-body").value });
  $("mm-copied").textContent = r.error || "Saved"; setTimeout(() => ($("mm-copied").textContent = ""), r.error ? 8000 : 2500);
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
function showTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("on", t.dataset.tab === name));
  $("pane-output").hidden = name !== "output"; $("pane-review").hidden = name !== "review"; $("pane-calls").hidden = name !== "calls";
  if (name === "review") loadReview();
  if (name === "calls") loadCalls();
}
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.tab)));
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
  $("review-count").hidden = !n; $("review-count").textContent = n;
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
$("sheet").addEventListener("change", () => { try { localStorage.setItem("sheet", $("sheet").value); } catch (e) {} loadProgress(); loadReview(); loadLetters(); if (!$("pane-calls").hidden) loadCalls(); });
$("save").addEventListener("click", async () => {
  const body = {};
  for (const k of ["PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "LETTER_SIGNOFF", "LETTER_EMAIL", "LETTER_PHONE", "MAIL_ADDRESS", "MAIL_APP_PASSWORD", "MAIL_IMAP_HOST", "MAIL_FROM_NAME", "QUOTE_PRICE_BUILD", "QUOTE_PRICE_LANDING", "QUOTE_VAT_RATE", "QUOTE_DEPOSIT_PERCENT", "DASHBOARD_API_URL", "SITE_URL"]) body[k] = $(k).value;
  const r = await post("/api/settings", body);
  for (const k of ["PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "TELEGRAM_BOT_TOKEN", "MAIL_APP_PASSWORD"]) $(k).value = "";
  $("saved").textContent = "Saved"; setTimeout(() => ($("saved").textContent = ""), 2000);
  $("settings-msg").textContent = r.warning ? "Saved, but " + r.warning + "." : "";
});
if (location.hash === "#tab-review") showTab("review");
if (location.hash === "#tab-calls") showTab("calls");
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
