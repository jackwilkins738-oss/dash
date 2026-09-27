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
SETTING_KEYS = ["PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "DASHBOARD_API_URL", "SITE_URL"]
SECRET_KEYS = {"PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY"}
RUN_ALL_BATCH = 10
# Shown in the header. Bump it with every change, so an old panel still running is obvious.
PANEL_VERSION = "6"
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
        from push_prospects import SKIP_STATUSES, domain_of
    except (ImportError, SystemExit):
        return {"error": "Needs openpyxl: python -m pip install openpyxl"}
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
    "all": "Run the whole list",
    "links": "Refresh preview links + Mailmeteor CSV",
    "speed": "Speed check the next batch",
    "one": "Check one firm",
    "emails": "Check emails",
    "companies": "Look up company types",
    "trades": "Guess missing trades",
    "push": "Push to dashboard",
}


def run_all_steps(job: "Job", sheet: str, name: str, settings: dict[str, str]):
    """Everything the list needs, in order: the quick checks for everyone, then
    speed checks in batches - each batch pushed and logged, so stopping part-way
    loses nothing."""
    first = ["--sheet", sheet, "--check-emails", "--guess-trades"]
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


def build_steps(body: dict, settings: dict[str, str]):
    """(steps, error): steps is an iterable of push_prospects.py argument lists."""
    action = body.get("action")
    if action not in ACTIONS:
        return None, "Unknown action."
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
    elif action == "one":
        only = str(body.get("only") or "").strip()
        if not only:
            return None, "Type part of the business name or website."
        args += ["--teardown", "--only", only]
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

    def start(self, label: str, steps, settings: dict[str, str]) -> str:
        with self.lock:
            if self.running():
                return "Something is already running - wait for it or press Stop."
            if len(settings["PROSPECTS_API_SECRET"]) < 32:
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
        try:
            for args in steps(self):
                if self.stopping:
                    break
                self.note(f"> python push_prospects.py {' '.join(a if ' ' not in a else repr(a) for a in args)}")
                self.note("")
                with self.lock:
                    self.proc = subprocess.Popen(
                        [sys.executable, "-u", str(PUSH), *args],
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
        with self.lock:
            self.exit_code = code if not self.stopping else -1
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
                    "files": output_files(),
                    "settings": {
                        k: (bool(settings[k]) if k in SECRET_KEYS else settings[k]) for k in SETTING_KEYS
                    },
                    "dashboard": (settings["DASHBOARD_API_URL"] or "https://admin.scalardigital.co.uk").rstrip("/"),
                    "site": (settings["SITE_URL"] or "https://www.scalardigital.co.uk").rstrip("/"),
                }
            )
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
            error = JOB.start(ACTIONS[body["action"]] + (" (dry run)" if body.get("dry_run") else ""), steps, settings)
            return self._json({"error": error} if error else {"ok": True}, 409 if error else 200)
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
        <p>Checks emails, looks up company types, guesses trades, then speed checks every site left, 10 at a time - each batch pushed as it goes. Start it and walk away; Stop loses nothing.</p>
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
    <div class="status"><span class="dot" id="dot"></span><b id="job-label">Nothing running</b><span id="job-time" style="color:var(--dim)"></span><span style="margin-left:auto"></span><button class="danger" id="stop" disabled>Stop</button></div>
    <pre id="log">Pick a button on the left. Output appears here.</pre>
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
  }
  $("files").innerHTML = s.files.map((f) => `<li>${f.name.replace(/</g, "&lt;")}<span>${ago(f.modified)}</span></li>`).join("") || "<li><span>None yet</span></li>";
  if (!settingsLoaded) {
    settingsLoaded = true;
    $("DASHBOARD_API_URL").value = s.settings.DASHBOARD_API_URL || "";
    $("SITE_URL").value = s.settings.SITE_URL || "";
    if (!s.settings.PROSPECTS_API_SECRET) $("settings-box").open = true;
  }
  $("set-secret").textContent = s.settings.PROSPECTS_API_SECRET ? "(saved)" : "(not set)";
  $("set-psi").textContent = s.settings.PAGESPEED_API_KEY ? "(saved)" : "(not set - needed for speed checks)";
  $("set-ch").textContent = s.settings.COMPANIES_HOUSE_API_KEY ? "(saved)" : "(not set - free at developer.company-information.service.gov.uk)";

  const j = s.job;
  $("dot").className = "dot " + (j.running ? "run" : j.exit_code === 0 ? "ok" : j.exit_code != null ? "bad" : "");
  $("job-label").textContent = j.label || "Nothing running";
  $("job-time").textContent = j.started ? (j.running ? "started " : "ran ") + ago(j.started) : "";
  $("stop").disabled = !j.running;
  document.querySelectorAll("[data-action]").forEach((b) => (b.disabled = j.running));
  if (j.lines.length && j.seq !== lastLines) {
    const log = $("log");
    const atBottom = log.scrollHeight - log.scrollTop - log.clientHeight < 40;
    log.textContent = j.lines.join("\n");
    if (atBottom || lastLines === -1) log.scrollTop = log.scrollHeight;
    lastLines = j.seq;
  }
  if ((wasRunning && !j.running) || (j.running && ++polls % 15 === 0)) loadProgress();
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
$("stop").addEventListener("click", () => post("/api/stop"));
$("open-folder").addEventListener("click", () => post("/api/open-folder"));
$("sheet").addEventListener("change", () => { try { localStorage.setItem("sheet", $("sheet").value); } catch (e) {} loadProgress(); });
$("save").addEventListener("click", async () => {
  const body = {};
  for (const k of ["PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY", "DASHBOARD_API_URL", "SITE_URL"]) body[k] = $(k).value;
  const r = await post("/api/settings", body);
  for (const k of ["PROSPECTS_API_SECRET", "PAGESPEED_API_KEY", "COMPANIES_HOUSE_API_KEY"]) $(k).value = "";
  $("saved").textContent = "Saved"; setTimeout(() => ($("saved").textContent = ""), 2000);
  $("settings-msg").textContent = r.warning ? "Saved, but " + r.warning + "." : "";
});
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
