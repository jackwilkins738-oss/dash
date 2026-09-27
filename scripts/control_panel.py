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
SETTING_KEYS = [
    "PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    "DASHBOARD_API_URL", "SITE_URL",
]
SECRET_KEYS = {"PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "TELEGRAM_BOT_TOKEN"}
# A run this long gets a phone alert when it ends (if Telegram is set up).
ALERT_AFTER_S = 180
RUN_ALL_BATCH = 10
# Shown in the header. Bump it with every change, so an old panel still running is obvious.
PANEL_VERSION = "13"
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
    names = sorted(p.name for p in OUTREACH.glob("*.xlsx") if not p.name.startswith("~$"))
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
    "speed": "Speed check the next batch",
    "one": "Check one firm",
    "contacts": "Find missing emails & phones",
    "emails": "Check emails",
    "companies": "Look up company types",
    "trades": "Guess missing trades",
    "push": "Push to dashboard",
}


def run_all_steps(job: "Job", sheet: str, name: str, settings: dict[str, str]):
    """Everything the list needs, in order: the quick checks for everyone, then
    speed checks in batches - each batch pushed and logged, so stopping part-way
    loses nothing."""
    first = ["--sheet", sheet, "--find-contacts", "--check-emails", "--guess-trades"]
    if settings.get("COMPANIES_HOUSE_API_KEY"):
        first.append("--lookup-companies")
    else:
        job.note("No COMPANIES_HOUSE_API_KEY in Settings - skipping the company type lookup.")
    yield first
    if not settings.get("PAGESPEED_API_KEY"):
        job.note("No PAGESPEED_API_KEY in Settings - skipping the speed checks.")
        return
    last = None
    while True:
        now = progress(name)
        remaining = now.get("remaining")
        if not remaining:
            failed = now.get("failed") or 0
            job.note(
                f"List done: {now.get('checked', 0)} speed checked"
                + (f", {failed} couldn't be checked (site down or blocking Google - Speed check next with 'Include sites already checked' retries them)." if failed else ".")
            )
            return
        if remaining == last:
            job.note(f"{remaining} still to check but the last batch made no progress - stopping.")
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

    def start(self, label: str, steps, settings: dict[str, str], needs_secret: bool = True) -> str:
        with self.lock:
            if self.running():
                return "Something is already running - wait for it or press Stop."
            if needs_secret and len(settings["PROSPECTS_API_SECRET"]) < 32:
                return "Add PROSPECTS_API_SECRET in Settings first (32+ characters, same value as in Vercel)."
            env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
            env.update({k: v for k, v in settings.items() if v})
            self.lines = [f"> {label}"]
            self.seq += 1
            self.label, self.started, self.exit_code, self.stopping = label, time.time(), None, False
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
                self.note(f"> python {script.name} {' '.join(a if ' ' not in a else repr(a) for a in args)}")
                self.note("")
                with self.lock:
                    self.proc = subprocess.Popen(
                        [sys.executable, "-u", str(script), *args],
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
                if code != 0 or self.stopping:
                    break
        except Exception as e:  # never leave the panel stuck on "running"
            self.note(f"Panel error: {e}")
            code = 1
        keep_awake(False)
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
ALERT_LINE = re.compile(r"^(List done|Logged|Pushed|Wrote|\d+ prospects|\d+ companies|Only \d+|Stopped|  (Outreach|Check website|No website) )")


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
            error = JOB.start(label, steps, settings, needs_secret=not finder)
            return self._json({"error": error} if error else {"ok": True}, 409 if error else 200)
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
  body { margin:0; background:var(--bg); color:var(--text); font:14px/1.45 system-ui, -apple-system, Segoe UI, sans-serif; }
  header { display:flex; align-items:center; gap:16px; padding:14px 20px; border-bottom:1px solid var(--line); flex-wrap:wrap; }
  header h1 { font-size:16px; margin:0; margin-right:auto; }
  header a { color:var(--dim); text-decoration:none; } header a:hover { color:var(--text); }
  main { display:grid; grid-template-columns: 380px 1fr; gap:16px; padding:16px 20px; }
  @media (max-width: 900px) { main { grid-template-columns: 1fr; } }
  .card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; margin-bottom:16px; }
  .card h2 { font-size:12px; text-transform:uppercase; letter-spacing:.06em; color:var(--dim); margin:0 0 10px; }
  label { display:block; color:var(--dim); font-size:12px; margin:8px 0 4px; }
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
        <button data-action="links">Refresh preview links + Mailmeteor CSV</button>
        <p>Rewrites preview-links and mailmeteor CSVs from the sheet. Never sends anything.</p>
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
        <button data-action="push">Push to dashboard</button>
        <p>Sends the sheet's changes (names, trades, areas, scores) to the dashboard.</p>
      </div>
      <div class="msg" id="run-msg"></div>
    </div>

    <div class="card">
      <div style="display:flex; justify-content:space-between; align-items:center"><h2 style="margin:0">Files in outreach/</h2><button id="open-folder">Open folder</button></div>
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
    </div>
    <div id="pane-output">
      <div class="status"><span class="dot" id="dot"></span><b id="job-label">Nothing running</b><span id="job-time" style="color:var(--dim)"></span><span style="margin-left:auto"></span><button class="danger" id="stop" disabled>Stop</button></div>
      <pre id="log">Pick a button on the left. Output appears here.</pre>
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
  }
  $("files").innerHTML = s.files.map((f) => `<li>${f.name.replace(/</g, "&lt;")}<span>${ago(f.modified)}</span></li>`).join("") || "<li><span>None yet</span></li>";
  if (!settingsLoaded) {
    settingsLoaded = true;
    $("DASHBOARD_API_URL").value = s.settings.DASHBOARD_API_URL || "";
    $("SITE_URL").value = s.settings.SITE_URL || "";
    $("TELEGRAM_CHAT_ID").value = s.settings.TELEGRAM_CHAT_ID || "";
    if (!s.settings.PROSPECTS_API_SECRET) $("settings-box").open = true;
  }
  $("set-secret").textContent = s.settings.PROSPECTS_API_SECRET ? "(saved)" : "(not set)";
  $("set-psi").textContent = s.settings.PAGESPEED_API_KEY ? "(saved)" : "(not set - needed for speed checks)";
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
  if (wasRunning && !j.running) loadReview();
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
  const r = await post("/api/run", { action, sheet: $("sheet").value, dry_run: dry, limit: $("limit").value, recheck: $("recheck").checked, only: $("only").value });
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
// ---- Review tab
let reviewItems = [], reviewKinds = {}, reviewFilter = "all";
function esc(t) { return String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])); }
function showTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("on", t.dataset.tab === name));
  $("pane-output").hidden = name !== "output"; $("pane-review").hidden = name !== "review";
  if (name === "review") loadReview();
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
$("sheet").addEventListener("change", () => { try { localStorage.setItem("sheet", $("sheet").value); } catch (e) {} loadProgress(); loadReview(); });
$("save").addEventListener("click", async () => {
  const body = {};
  for (const k of ["PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "DASHBOARD_API_URL", "SITE_URL"]) body[k] = $(k).value;
  const r = await post("/api/settings", body);
  for (const k of ["PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "TELEGRAM_BOT_TOKEN"]) $(k).value = "";
  $("saved").textContent = "Saved"; setTimeout(() => ($("saved").textContent = ""), 2000);
  $("settings-msg").textContent = r.warning ? "Saved, but " + r.warning + "." : "";
});
if (location.hash === "#tab-review") showTab("review");
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
