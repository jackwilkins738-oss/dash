"""Checks every inbox for replies every 15 minutes through the working day - not just once a morning.

    python scripts/reply_watch.py --install   check every 15 min, 08:00-20:00 (Windows Task Scheduler)
    python scripts/reply_watch.py --remove    stop
    python scripts/reply_watch.py             one check now (what the schedule runs)

An interested reply answered within the hour turns into a call far more often than one answered the
next morning. Each check is the same read-only reply check as the panel's button (reply_scanner.py):
nothing is marked read, moved or deleted; no's are blocked, bounces go to letters, and an interested
reply texts you on Telegram straight away, with what they said. Replies it has already seen are
skipped, and it never runs at the same time as another reply check.

Each check adds one line to outreach/reply-watch.log, which the panel shows ("last checked 10:15").
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

TASK_NAME = "Scalar Reply Watch"
START, EVERY_MIN, HOURS = "08:00", 15, "12:00"
LOG = "reply-watch.log"
KEEP_LINES = 500


def schedule_command(runner: Path) -> list[str]:
    """Every 15 minutes from 08:00 for 12 hours, every day."""
    command = f'"{runner}" "{Path(__file__).resolve()}"'
    return ["schtasks", "/Create", "/F", "/SC", "DAILY", "/TN", TASK_NAME, "/TR", command,
            "/ST", START, "/RI", str(EVERY_MIN), "/DU", HOURS]


def install() -> str:
    if sys.platform != "win32":
        return "Scheduling needs Windows - elsewhere, run python scripts/reply_watch.py every 15 minutes (e.g. from cron)."
    exe = Path(sys.executable)
    quiet = exe.with_name("pythonw.exe")  # no window popping up every 15 minutes
    res = subprocess.run(schedule_command(quiet if quiet.exists() else exe), capture_output=True, text=True)
    return "" if res.returncode == 0 else (res.stderr or res.stdout).strip() or "Task Scheduler refused."


def remove() -> str:
    if sys.platform != "win32":
        return ""
    res = subprocess.run(["schtasks", "/Delete", "/F", "/TN", TASK_NAME], capture_output=True, text=True)
    out = (res.stderr or res.stdout).strip()
    return "" if res.returncode == 0 or "cannot find" in out.lower() else out


def summarise(output: str) -> str:
    """One line for the log from what the reply check printed."""
    lines = [x.strip() for x in output.splitlines() if x.strip()]
    found = next((x for x in lines if x.startswith("Found ") and " new:" in x), "")
    if found:
        return found
    for x in lines:
        if x.startswith(("No new replies", "Another reply check", "Add MAIL_ADDRESS", "The inbox refused", "Couldn't reach")):
            return x
    return lines[-1] if lines else "Checked."


def append_log(outreach: Path, line: str, now: datetime | None = None) -> None:
    path = outreach / LOG
    stamp = (now or datetime.now()).strftime("%Y-%m-%d %H:%M")
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    lines = (lines + [f"{stamp}  {line}"])[-KEEP_LINES:]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def last_check(outreach: Path) -> dict | None:
    """{at, line} of the latest check, for the panel - or None if it has never run."""
    path = outreach / LOG
    if not path.exists():
        return None
    rows = [x for x in path.read_text(encoding="utf-8").splitlines() if x.strip()]
    if not rows:
        return None
    m = re.match(r"(\d{4}-\d\d-\d\d \d\d:\d\d)\s+(.*)", rows[-1])
    return {"at": m.group(1), "line": m.group(2)} if m else None


def run() -> int:
    import control_panel as panel
    import reply_scanner

    # The same settings the panel saved (inboxes, Telegram) - this runs with no panel open.
    os.environ.update({k: v for k, v in panel.load_settings().items() if v})
    outreach = reply_scanner.outreach_dir()
    outreach.mkdir(exist_ok=True)
    buf = io.StringIO()
    code = 0
    with contextlib.redirect_stdout(buf):
        try:
            reply_scanner.main()
        except SystemExit as e:  # not set up, or the inbox refused - logged, never a crash dialog
            if e.code not in (None, 0):
                print(e.code if isinstance(e.code, str) else "Stopped.")
                code = 1
        except Exception as e:  # noqa: BLE001 - a dropped connection must not kill the schedule
            print(f"Couldn't check replies: {e}")
            code = 1
    append_log(outreach, summarise(buf.getvalue()))
    print(buf.getvalue(), end="")
    return code


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--remove", action="store_true")
    args = ap.parse_args()
    if args.install:
        err = install()
        print(err or "On: replies are checked every 15 minutes, 08:00-20:00, while this PC is on.")
        sys.exit(1 if err else 0)
    if args.remove:
        err = remove()
        print(err or "Off: replies are only checked when you press Check replies (and by the autopilot).")
        sys.exit(1 if err else 0)
    sys.exit(run())


if __name__ == "__main__":
    main()
