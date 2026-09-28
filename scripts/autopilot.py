"""The daily routine, on its own: replies, new firms, the whole list, today's batches, export, a text.

    python scripts/autopilot.py            run it now (the panel's "Run autopilot now")
    python scripts/autopilot.py --install  schedule it daily (Windows Task Scheduler)
    python scripts/autopilot.py --remove   stop the schedule

Set up from the panel's Autopilot card, which saves outreach/autopilot.json:
the search to run for new firms, how many to email a day, and whether to
make follow-ups. Each run:

  1. checks replies (if the inbox is set up) - no's blocked before anything else
  2. runs the saved search for new firms (a new sheet, like Find & build list)
  3. runs the whole list on that sheet and on any list with speed checks left
  4. makes today's email batch and follow-up batch
  5. updates the Excel export
  6. texts you a summary (Telegram), and writes outreach/autopilot-log.txt

It never sends an email: the batches wait for you to import into Mailmeteor
and send. A step that fails is noted and the rest still run. Windows runs it
at the time you choose while you're logged in; the PC must be on (it's kept
awake while it runs).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import control_panel as panel  # noqa: E402 - settings, list progress and the whole-list steps live there

TASK_NAME = "Scalar Prospect Autopilot"
CONFIG = "autopilot.json"
LOCK = ".autopilot.lock"
DEFAULTS = {
    "enabled": False, "time": "07:30", "find": None, "batch_size": 20,
    "followups": True, "followup_size": 20, "followup_after_days": 5,
}


def load_config() -> dict:
    path = panel.OUTREACH / CONFIG
    try:
        return {**DEFAULTS, **json.loads(path.read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def save_config(cfg: dict) -> None:
    panel.OUTREACH.mkdir(exist_ok=True)
    (panel.OUTREACH / CONFIG).write_text(json.dumps({**DEFAULTS, **cfg}, indent=2), encoding="utf-8")


def is_running() -> bool:
    """True while a run is going (a lock younger than 6 hours - an older one is from a crash)."""
    lock = panel.OUTREACH / LOCK
    return lock.exists() and time.time() - lock.stat().st_mtime < 6 * 3600


class Run:
    def __init__(self, log_path: Path) -> None:
        self.log = log_path.open("w", encoding="utf-8")
        self.failed: list[str] = []
        self.lines: list[str] = []
        self.env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
        self.env.update({k: v for k, v in panel.load_settings().items() if v})

    def note(self, line: str) -> None:
        stamp = datetime.now().strftime("%H:%M")
        print(line, flush=True)
        self.log.write(f"{stamp}  {line}\n")
        self.log.flush()
        self.lines.append(line)

    def step(self, script: Path, args: list[str]) -> int:
        self.note(f"> {script.name} {' '.join(args)}")
        proc = subprocess.Popen([sys.executable, "-u", str(script), *args], cwd=str(HERE), env=self.env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL)
        assert proc.stdout
        for raw in proc.stdout:
            self.note("  " + raw.decode("utf-8", errors="replace").rstrip())
        code = proc.wait()
        if code:
            self.failed.append(f"{script.name} {' '.join(a for a in args if a.startswith('--'))}")
            self.note(f"  (that step had a problem - carrying on)")
        return code


def lists_to_run(new_sheet: str | None) -> list[str]:
    """Today's new sheet, plus any list with speed checks still to do (the five most recent)."""
    names = [new_sheet] if new_sheet else []
    for name in sorted(panel.sheets(), key=lambda n: (panel.OUTREACH / n).stat().st_mtime, reverse=True):
        if name in names:
            continue
        if (panel.progress(name).get("remaining") or 0) > 0:
            names.append(name)
    return names[:5]


def run() -> int:
    panel.OUTREACH.mkdir(exist_ok=True)
    if is_running():
        print("Autopilot is already running.")
        return 1
    lock = panel.OUTREACH / LOCK
    lock.write_text(str(os.getpid()))
    cfg = load_config()
    r = Run(panel.OUTREACH / "autopilot-log.txt")
    panel.keep_awake(True)
    started = time.time()
    try:
        r.note(f"Autopilot started {datetime.now().strftime('%A %d %B %Y %H:%M')}")
        settings = panel.load_settings()
        if len(settings.get("PROSPECTS_API_SECRET", "")) < 32:
            r.note("PROSPECTS_API_SECRET isn't in Settings - nothing can be pushed. Stopping.")
            return 1

        if settings.get("MAIL_ADDRESS") and settings.get("MAIL_APP_PASSWORD"):
            r.step(panel.REPLIES, [])

        new_sheet = None
        find = cfg.get("find") or {}
        if find.get("trades") and find.get("areas"):
            before = set(panel.sheets())
            args, error = panel.build_find_args({**find, "action": "find"}, settings)
            if args is None:
                r.note(f"Saved search skipped: {error}")
            else:
                r.step(panel.FIND, args)
                made = set(panel.sheets()) - before
                new_sheet = max(made, key=lambda n: (panel.OUTREACH / n).stat().st_mtime) if made else None
        else:
            r.note("No saved search - skipping new firms (save one on the panel's Autopilot card).")

        for name in lists_to_run(new_sheet):
            r.note(f"--- {name}")
            path = str(panel.OUTREACH / name)
            for step in panel.run_all_steps(r, path, name, settings):
                script, args = step if isinstance(step, tuple) else (panel.PUSH, step)
                if script in (panel.REPLIES, panel.EXPORT):
                    continue  # once per run, not per list
                r.step(script, args)

        r.step(panel.BATCHES, ["--size", str(int(cfg.get("batch_size") or 20))])
        if cfg.get("followups"):
            r.step(panel.BATCHES, ["--followups", "--size", str(int(cfg.get("followup_size") or 20)),
                                   "--after-days", str(int(cfg.get("followup_after_days") or 5))])
        r.step(panel.EXPORT, [])
        return summarise(r, settings, time.time() - started)
    finally:
        panel.keep_awake(False)
        lock.unlink(missing_ok=True)
        r.log.close()


SUMMARY_LINE = re.compile(r"^\s*(READY|Found \d+ new|Wrote .*(firms|\.xlsx)|List done|No follow-ups|Nobody left|  \d+ (added|bounced))")


def summarise(r: Run, settings: dict, seconds: float) -> int:
    picked = [l.strip() for l in r.lines if SUMMARY_LINE.match(l)]
    replies = next((l.strip() for l in r.lines if "Found " in l and " new:" in l), "")
    mins = int(seconds // 60)
    head = f"Autopilot done in {mins // 60}h {mins % 60}m" if mins >= 60 else f"Autopilot done in {mins}m"
    body = [head]
    if replies:
        body.append("Replies: " + replies.split(": ", 1)[-1])
    body += [l for l in picked if l.startswith("READY")]
    if r.failed:
        body.append(f"{len(r.failed)} step(s) had problems - see autopilot-log.txt")
    body.append("Next: import the READY files into Mailmeteor and send.")
    r.note("")
    for line in body:
        r.note(line)
    token, chat = settings.get("TELEGRAM_BOT_TOKEN", ""), settings.get("TELEGRAM_CHAT_ID", "")
    if token and chat:
        import urllib.request

        try:
            req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                         data=json.dumps({"chat_id": chat, "text": "\n".join(body)}).encode(),
                                         headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=15).close()
        except OSError:
            pass
    return 1 if r.failed else 0


# ---------------------------------------------------------------- schedule (Windows)


def install(at: str) -> str:
    if not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", at):
        return "The time must look like 07:30."
    if sys.platform != "win32":
        return "Scheduling needs Windows - on this computer, run: python scripts/autopilot.py (e.g. from cron)."
    # pythonw runs it without a window popping up; the log and the text say how it went.
    exe = Path(sys.executable)
    quiet = exe.with_name("pythonw.exe")
    runner = quiet if quiet.exists() else exe
    command = f'"{runner}" "{Path(__file__).resolve()}"'
    res = subprocess.run(["schtasks", "/Create", "/F", "/SC", "DAILY", "/TN", TASK_NAME, "/TR", command, "/ST", at],
                         capture_output=True, text=True)
    return "" if res.returncode == 0 else (res.stderr or res.stdout).strip() or "Task Scheduler refused."


def remove() -> str:
    if sys.platform != "win32":
        return ""
    res = subprocess.run(["schtasks", "/Delete", "/F", "/TN", TASK_NAME], capture_output=True, text=True)
    out = (res.stderr or res.stdout).strip()
    return "" if res.returncode == 0 or "cannot find" in out.lower() else out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--remove", action="store_true")
    args = ap.parse_args()
    if args.install:
        err = install(load_config().get("time") or "07:30")
        sys.exit(err or 0)
    if args.remove:
        sys.exit(remove() or 0)
    sys.exit(run())


if __name__ == "__main__":
    main()
