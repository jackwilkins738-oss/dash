"""Start the panel (quietly, no browser) whenever you log in to Windows - so the Telegram controls
work whenever the PC is on, without opening the panel first.

    python scripts/panel_startup.py --install
    python scripts/panel_startup.py --remove

Puts "Scalar Panel.cmd" in your own Startup folder (Win+R, shell:startup) - no administrator rights
needed, unlike a Task Scheduler logon task. Delete that file to undo it by hand. Opening the panel as
usual (control_panel.bat) then just shows the one already running.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

NAME = "Scalar Panel.cmd"
PANEL = Path(__file__).resolve().parent / "control_panel.py"


def startup_folder() -> Path | None:
    appdata = os.environ.get("APPDATA")
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" if appdata else None


def launcher(runner: Path) -> str:
    # "start" hands over to pythonw and the window closes at once - no console left on screen.
    return f'@echo off\r\nstart "" "{runner}" "{PANEL}" --no-browser\r\n'


def install() -> str:
    if sys.platform != "win32":
        return "Starting at login needs Windows - elsewhere, add control_panel.py --no-browser to your startup items."
    folder = startup_folder()
    if folder is None or not folder.is_dir():
        return "Couldn't find your Startup folder (Win+R, shell:startup) - put a shortcut to control_panel.bat in it by hand."
    exe = Path(sys.executable)
    quiet = exe.with_name("pythonw.exe")  # no window sitting on the taskbar
    try:
        (folder / NAME).write_text(launcher(quiet if quiet.exists() else exe), encoding="utf-8", newline="")
    except OSError as e:
        return f"Couldn't write to your Startup folder ({e})."
    return ""


def remove() -> str:
    folder = startup_folder()
    if folder is not None:
        try:
            (folder / NAME).unlink(missing_ok=True)
        except OSError as e:
            return f"Couldn't remove {NAME} from your Startup folder ({e})."
    return ""


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("--install", "--remove"):
        sys.exit("Usage: python scripts/panel_startup.py --install | --remove")
    if sys.argv[1] == "--install":
        err = install()
        print(err or f"Done: the panel now starts by itself when you log in (no browser). It's {NAME} in your Startup "
                     "folder (Win+R, shell:startup). Telegram controls work whenever the PC is on and awake.")
    else:
        err = remove()
        print(err or "Done: the panel no longer starts with Windows.")
    sys.exit(1 if err else 0)


if __name__ == "__main__":
    main()
