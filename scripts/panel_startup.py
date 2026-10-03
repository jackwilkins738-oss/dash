"""Start the panel (quietly, no browser) whenever you log in to Windows - so the Telegram controls
work whenever the PC is on, without opening the panel first.

    python scripts/panel_startup.py --install
    python scripts/panel_startup.py --remove

Opening the panel as usual (control_panel.bat) then just shows the one already running.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

TASK_NAME = "Scalar Panel"
PANEL = Path(__file__).resolve().parent / "control_panel.py"


def command(runner: Path) -> list[str]:
    return ["schtasks", "/Create", "/F", "/SC", "ONLOGON", "/TN", TASK_NAME, "/TR", f'"{runner}" "{PANEL}" --no-browser']


def install() -> str:
    if sys.platform != "win32":
        return "Starting at login needs Windows - elsewhere, add control_panel.py --no-browser to your startup items."
    exe = Path(sys.executable)
    quiet = exe.with_name("pythonw.exe")  # no window sitting on the taskbar
    res = subprocess.run(command(quiet if quiet.exists() else exe), capture_output=True, text=True)
    return "" if res.returncode == 0 else (res.stderr or res.stdout).strip() or "Task Scheduler refused."


def remove() -> str:
    if sys.platform != "win32":
        return ""
    res = subprocess.run(["schtasks", "/Delete", "/F", "/TN", TASK_NAME], capture_output=True, text=True)
    out = (res.stderr or res.stdout).strip()
    return "" if res.returncode == 0 or "cannot find" in out.lower() else out


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("--install", "--remove"):
        sys.exit("Usage: python scripts/panel_startup.py --install | --remove")
    if sys.argv[1] == "--install":
        err = install()
        print(err or "Done: the panel now starts by itself when you log in to Windows (no window, no browser). "
                     "Telegram controls work whenever the PC is on and awake.")
    else:
        err = remove()
        print(err or "Done: the panel no longer starts with Windows.")
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
