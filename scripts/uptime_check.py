"""Is scalardigital.co.uk up? And the dashboard? Run by GitHub Actions every 30 minutes.

    .github/workflows/uptime.yml runs:  python scripts/uptime_check.py

The dashboard already watches every client's site (and texts the owner); nothing watched Scalar's
own. Each address gets two tries a minute apart before it counts as down - a blip isn't an alert.
You're texted (Telegram) once when something goes down and once when it's back, never every half
hour in between: the last state is kept in the Actions cache. Prints only the public addresses
checked and their status.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

SITES = {
    "Website": "https://www.scalardigital.co.uk/",
    "Dashboard": "https://admin.scalardigital.co.uk/login",
}
STATE = Path(os.environ.get("UPTIME_STATE", ".uptime/state.json"))


def status(url: str, timeout: int = 20) -> str:
    """'up', or why not."""
    req = urllib.request.Request(url, headers={"User-Agent": "ScalarUptime/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return "up" if 200 <= res.status < 400 else f"HTTP {res.status}"
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        return f"unreachable ({getattr(e, 'reason', e)})"


def check(url: str, sleep=time.sleep) -> str:
    first = status(url)
    if first == "up":
        return "up"
    sleep(60)
    return status(url)


def changes(before: dict, now: dict) -> list[str]:
    out = []
    for name, state in now.items():
        was = before.get(name, "up")
        if state != "up" and was == "up":
            out.append(f"{name} is DOWN: {SITES[name]} - {state}.")
        elif state == "up" and was != "up":
            out.append(f"{name} is back up: {SITES[name]}.")
    return out


def send(text: str) -> None:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    if not (token and chat):
        print("(Telegram not set up - nobody to tell.)")
        return
    req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                 data=json.dumps({"chat_id": chat, "text": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    urllib.request.urlopen(req, timeout=20).close()


def main(sleep=time.sleep) -> int:
    before = json.loads(STATE.read_text()) if STATE.exists() else {}
    now = {name: check(url, sleep) for name, url in SITES.items()}
    for name, state in now.items():
        print(f"{name} ({SITES[name]}): {state}")
    news = changes(before, now)
    if news:
        try:
            send("\n".join(news))
        except OSError as e:
            print(f"Telegram didn't take the message ({type(e).__name__}) - will try again next run.")
            return 1  # state not saved, so the change is reported next time
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(now))
    return 0


if __name__ == "__main__":
    sys.exit(main())
