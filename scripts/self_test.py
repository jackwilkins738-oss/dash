"""Self-test: every key, install and connection the panel relies on, checked in one go.

The panel's Settings -> "Run the self-test" (or type "selftest" in Telegram). Read-only: it only asks
each service "does this key work?" - nothing is sent, changed or charged (the Anthropic check lists
models, which is free). Each line is ✅ working, ⚠️ optional and not set up, or ❌ broken - with the fix.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

OK, OPTIONAL, BAD = "✅", "⚠️", "❌"
TENANT = os.environ.get("SCALAR_TENANT_ID", "abdc6408-1fd5-4fb6-9c4c-53600b571a6d")


def _get(url: str, headers: dict | None = None, timeout: int = 20) -> tuple[int, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": "ScalarSelfTest/1.0", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            body = res.read(200_000)
            try:
                return res.status, json.loads(body)
            except ValueError:
                return res.status, {}
    except urllib.error.HTTPError as e:
        try:  # the services here answer errors as JSON - keep it, so the reason can be shown
            return e.code, json.loads(e.read(20_000))
        except (ValueError, OSError):
            return e.code, {}
    except (urllib.error.URLError, OSError, TimeoutError):
        return 0, {}


def installed(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def checks(env: dict, outreach: Path, get=_get, have=installed) -> list[tuple[str, str, str]]:
    """[(mark, name, detail)] - the detail says what to do when it isn't ✅."""
    out: list[tuple[str, str, str]] = []

    def add(mark: str, name: str, detail: str) -> None:
        out.append((mark, name, detail))

    secret = env.get("PROSPECTS_API_SECRET", "")
    api = (env.get("DASHBOARD_API_URL") or "https://admin.scalardigital.co.uk").rstrip("/")
    if len(secret) < 32:
        add(BAD, "Dashboard secret", "PROSPECTS_API_SECRET missing or too short - copy it from Vercel (dashboard project)")
    else:
        code, body = get(f"{api}/api/prospects/activity?tenant_id={TENANT}", {"Authorization": f"Bearer {secret}"})
        if code == 200:
            add(OK, "Dashboard", f"connected - {len(body.get('prospects') or [])} preview pages")
        elif code == 401:
            add(BAD, "Dashboard", "refused the secret - PROSPECTS_API_SECRET must match the dashboard's in Vercel")
        else:
            add(BAD, "Dashboard", f"couldn't reach {api} (HTTP {code or 'no answer'})")
        code, body = get(f"{api}/api/prospects/quotes?tenant_id={TENANT}", {"Authorization": f"Bearer {secret}"})
        if code == 200 and body.get("warning"):
            add(BAD, "Quote chaser", f"{body['warning']} (Supabase -> SQL Editor)")
        elif code == 200:
            add(OK, "Quote chaser", f"{len(body.get('quotes') or [])} open quote(s) readable")
        else:
            add(BAD, "Quote chaser", f"HTTP {code or 'no answer'}" + (f" - {str(body['error'])[:120]}" if body.get("error") else " - redeploy the dashboard"))

        code, body = get(f"{api}/api/job-posts?tenant_id={TENANT}", {"Authorization": f"Bearer {secret}"})
        if code == 200:
            add(OK, "Job posts", "readable - Growth clients' finished jobs are written up each morning")
        else:
            add(BAD, "Job posts", f"HTTP {code or 'no answer'}" + (f" - {str(body['error'])[:120]}" if body.get("error") else " - redeploy the dashboard"))

    if env.get("MAIL_ADDRESS") and env.get("MAIL_APP_PASSWORD"):
        add(OK if env.get("MAIL_FROM_NAME") else BAD, "Email", f"{env['MAIL_ADDRESS']}" + ("" if env.get("MAIL_FROM_NAME") else
            " - add MAIL_FROM_NAME (your sign-off)") + " (login is tested by Send a test to yourself)")
    else:
        add(BAD, "Email", "MAIL_ADDRESS / MAIL_APP_PASSWORD missing - nothing can be sent or replies read")

    token, chat = env.get("TELEGRAM_BOT_TOKEN", ""), env.get("TELEGRAM_CHAT_ID", "")
    if token and chat:
        code, body = get(f"https://api.telegram.org/bot{token}/getMe")
        add(OK if code == 200 and body.get("ok") else BAD, "Telegram",
            f"@{(body.get('result') or {}).get('username', '?')}" if code == 200 else "the bot token was refused - check TELEGRAM_BOT_TOKEN")
    else:
        add(OPTIONAL, "Telegram", "not set up - the phone controls, nudges and alerts need TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID")

    key = env.get("ANTHROPIC_API_KEY", "")
    if key:
        code, _ = get("https://api.anthropic.com/v1/models?limit=1", {"x-api-key": key, "anthropic-version": "2023-06-01"})
        add(OK if code == 200 else BAD, "Claude (AI)", "key works - set a monthly spend limit at console.anthropic.com -> Billing"
            if code == 200 else f"key refused (HTTP {code or 'no answer'}) - check ANTHROPIC_API_KEY")
    else:
        add(OPTIONAL, "Claude (AI)", "no ANTHROPIC_API_KEY - AI drafts, coach, photo reading, website check and alt text are off")

    psi = env.get("PAGESPEED_API_KEY", "")
    if psi:
        code, _ = get(f"https://www.googleapis.com/pagespeedonline/v5/runPagespeed?url=https://example.com&strategy=mobile&category=performance&key={psi}",
                      timeout=90)
        add(OK if code == 200 else BAD, "Speed checks", "PageSpeed key works" if code == 200 else f"PageSpeed refused the key (HTTP {code or 'no answer'})")
    else:
        add(BAD, "Speed checks", "no PAGESPEED_API_KEY - previews get no score")

    places = env.get("GOOGLE_PLACES_API_KEY", "")
    add(OK if places else OPTIONAL, "Google ratings / rivals", "key set" if places else "no GOOGLE_PLACES_API_KEY - previews show no Google rating or competitors")
    ch = env.get("COMPANIES_HOUSE_API_KEY", "")
    if ch:
        from company_lookup import key_problem

        problem = key_problem(ch)
        add(BAD if problem else OK, "Companies House", problem or "key looks right")
    else:
        add(OPTIONAL, "Companies House", "no key - Find new prospects and company checks need COMPANIES_HOUSE_API_KEY")

    for setting, why in (("BOOKING_LINK", "emails carry no booking link"), ("REVIEW_LINK", "referral asks leave out the review"),
                         ("BACKUP_DIR", "no backups - your lists and opt-outs exist only on this PC")):
        add(OK if env.get(setting) else (BAD if setting == "BACKUP_DIR" else OPTIONAL), setting, "set" if env.get(setting) else why)

    for module, name, button in (("openpyxl", "Spreadsheets", "python -m pip install openpyxl"), ("segno", "Letters & cards (QR codes)", "Install segno"),
                                 ("PIL", "Photo processing", "python -m pip install pillow"), ("faster_whisper", "Voice notes", "Install voice notes"),
                                 ("playwright", "Video maker", "Install video maker"), ("imageio_ffmpeg", "Video maker (MP4)", "Install video maker")):
        add(OK if have(module) else OPTIONAL, name, "installed" if have(module) else f"not installed - Settings -> {button}")

    stop = outreach / "do-not-contact.csv"
    add(OK if stop.exists() else OPTIONAL, "Opt-out list", "do-not-contact.csv present" if stop.exists() else "none yet (made on the first 'no')")
    return out


def main() -> int:
    outreach = next((d / "outreach" for d in [HERE.parent, *HERE.parents] if (d / "outreach").is_dir()), HERE.parent / "outreach")
    rows = checks(dict(os.environ), outreach)
    for mark, name, detail in rows:
        print(f"{mark} {name}: {detail}", flush=True)
    bad = sum(1 for m, _, _ in rows if m == BAD)
    print("")
    print("All set." if not bad else f"{bad} thing(s) to fix (❌ above). ⚠️ lines are optional features not set up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
