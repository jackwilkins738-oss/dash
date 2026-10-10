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

By default it never sends an email: the batches wait for you to press Send today's batch
on the panel (or import them into Mailmeteor). Only if you tick "Send them automatically"
on the Autopilot card does it send - straight after checking replies, before the slow steps,
so the emails land early in the morning: today's batch (and follow-ups), from the inbox and
minutes apart you chose, with every check a manual send has (no's and replies left out, the
bounce pause, the daily cap per inbox). A step that fails is noted and the rest still run. Windows runs it
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
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

# A scheduled task can't set environment variables, so the US one names its workspace on the command
# line - read before the panel is imported, because the panel picks its folder when it loads.
if "--workspace" in sys.argv[:-1]:
    os.environ["OUTREACH_DIR"] = sys.argv[sys.argv.index("--workspace") + 1]

import control_panel as panel  # noqa: E402 - settings, list progress and the whole-list steps live there
import workspace  # noqa: E402


def task_name() -> str:
    """One Windows task per workspace, so the US autopilot never replaces the UK one."""
    label = workspace.config(panel.OUTREACH)["label"]
    return "Scalar Prospect Autopilot" + ("" if label == "UK" else f" ({label})")


TASK_NAME = task_name()
CONFIG = "autopilot.json"
LOCK = ".autopilot.lock"
DEFAULTS = {
    "enabled": False, "time": "07:30", "find": None, "batch_size": 20,
    "followups": True, "followup_size": 20, "followup_after_days": 5,
    "auto_send": False, "send_from": "", "send_gap": 5,
    # A start somewhere between "time" and "time_to" (e.g. 05:00-07:00), a different minute each day; blank = exactly "time".
    "time_to": "",
    # Send straight after checking replies ("first"), or after today's search and list run ("last").
    "send_when": "first",
    # The gap is per inbox: the inboxes take turns, each waiting its own gap.
    "gap_per_inbox": False,
    # Emails per inbox a day (0 = use batch_size): today's target is this x the inboxes sending, the search
    # finds only what's missing to reach it, and each inbox sends exactly this many first emails.
    "per_inbox": 0,
    # Which inboxes send first emails, and how many each ({address: n}). Set, it overrides per_inbox and
    # send_from: an inbox at 0 (or left out) sends none - its follow-ups still go from it, in the same thread.
    "inbox_plan": {},
    # Each inbox's number warmed up and protected (inbox_guard.py): new inboxes ramp up by themselves,
    # one with bounces or a domain problem is paused.
    "protect_inboxes": False,
    # Saturday and Sunday: replies and the lists only - no search, nothing sent.
    "weekdays_only": False,
    # A walkthrough video, made before the morning nudges, for each firm that opened its preview 2+ times.
    "auto_videos": False,
}
VIDEOS_A_MORNING = 5
FIND_BUFFER = 1.5  # not every firm found has an email - search for half as many again as are missing


def load_config() -> dict:
    path = panel.OUTREACH / CONFIG
    try:
        return {**DEFAULTS, **json.loads(path.read_text(encoding="utf-8"))}
    except (OSError, ValueError):
        return dict(DEFAULTS)


def save_config(cfg: dict) -> None:
    panel.OUTREACH.mkdir(exist_ok=True)
    (panel.OUTREACH / CONFIG).write_text(json.dumps({**DEFAULTS, **cfg}, indent=2), encoding="utf-8")


def _alive(pid: int) -> bool:
    """Whether that process is still a running Python (so a reused process number doesn't count)."""
    if pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
        k32.OpenProcess.restype = wintypes.HANDLE  # a pointer-sized handle, not the default 32-bit int
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        k32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = k32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = wintypes.DWORD()
            if not k32.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:  # 259 = STILL_ACTIVE
                return False
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(1024)
            if k32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                return "python" in buf.value.lower()
            return True
        finally:
            k32.CloseHandle(handle)
    try:
        os.kill(pid, 0)  # signal 0 only asks - never use this on Windows, where it would kill the process
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _started(pid: int) -> float | None:
    """When that process started (Unix time), or None where it can't be told."""
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        k32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
        k32.OpenProcess.restype = wintypes.HANDLE
        k32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        k32.GetProcessTimes.argtypes = [wintypes.HANDLE] + [ctypes.POINTER(wintypes.FILETIME)] * 4
        k32.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = k32.OpenProcess(0x1000, False, pid)
        if not handle:
            return None
        try:
            t = [wintypes.FILETIME() for _ in range(4)]
            if not k32.GetProcessTimes(handle, *(ctypes.byref(x) for x in t)):
                return None
            ticks = (t[0].dwHighDateTime << 32) | t[0].dwLowDateTime  # 100 ns since 1601
            return (ticks - 116444736000000000) / 1e7
        finally:
            k32.CloseHandle(handle)
    try:
        fields = Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()
        boot = next(float(ln.split()[1]) for ln in Path("/proc/stat").read_text().splitlines() if ln.startswith("btime"))
        return boot + int(fields[19]) / os.sysconf("SC_CLK_TCK")
    except (OSError, ValueError, IndexError, StopIteration):
        return None


def is_running() -> bool:
    """True while a run is actually going. A lock left behind by a run that was stopped, crashed or
    lost to a shutdown is cleared here, so the panel never shows a run that isn't happening."""
    lock = panel.OUTREACH / LOCK
    if not lock.exists():
        return False
    try:
        pid = int(lock.read_text().strip() or 0)
    except (OSError, ValueError):
        pid = 0
    written = lock.stat().st_mtime
    # The run writes the lock just after it starts. A process that started later only has a reused
    # number (Windows hands them out again after a crash or restart) - it isn't the run.
    started = _started(pid) if pid > 0 else None
    if time.time() - written < 6 * 3600 and _alive(pid) and (started is None or started <= written + 60):
        return True
    lock.unlink(missing_ok=True)
    return False


def now_doing(outreach: Path | None = None) -> dict:
    """While a run is going: how long it's been running and the last thing it said - so a long run
    (speed checks, a send spread over hours) reads as busy, not stuck."""
    outreach = outreach or panel.OUTREACH
    lock, log = outreach / LOCK, outreach / "autopilot-log.txt"
    if not lock.exists():
        return {}
    minutes = int((time.time() - lock.stat().st_mtime) // 60)
    last = ""
    if log.exists():
        lines = [ln.strip() for ln in log.read_text(encoding="utf-8", errors="replace").splitlines() if ln.strip()]
        last = lines[-1].split("  ", 1)[-1].strip() if lines else ""
    return {"minutes": minutes, "last": last[:160]}


def stop(outreach: Path | None = None) -> str:
    """Ends a run that's going (and whatever step it's on), and clears its lock."""
    outreach = outreach or panel.OUTREACH
    lock = outreach / LOCK
    if not lock.exists():
        return "The autopilot isn't running."
    try:
        pid = int(lock.read_text().strip() or 0)
    except (OSError, ValueError):
        pid = 0
    if pid and _alive(pid):
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True, timeout=30)
        else:
            import signal

            try:
                os.kill(pid, signal.SIGTERM)
            except OSError:
                pass
    lock.unlink(missing_ok=True)
    try:
        with (outreach / "autopilot-log.txt").open("a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%H:%M')}  Stopped from the panel.\n")
    except OSError:
        pass
    return "Autopilot stopped. Anything already sent stays sent; the next run picks up from there."


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
            self.note("  (that step had a problem - carrying on)")
        return code


def scorecard_day() -> bool:
    return date.today().weekday() == 0


def lists_to_run(new_sheet: str | None) -> list[str]:
    """Today's new sheet, plus any list with speed checks still to do (the five most recent)."""
    names = [new_sheet] if new_sheet else []
    for name in sorted(panel.sheets(), key=lambda n: (panel.OUTREACH / n).stat().st_mtime, reverse=True):
        if name in names:
            continue
        if (panel.progress(name).get("remaining") or 0) > 0:
            names.append(name)
    return names[:5]


def inbox_count(cfg: dict, settings: dict) -> int:
    import mail_accounts

    if str(cfg.get("send_from") or "").strip():
        return 1
    return max(1, len(mail_accounts.accounts(settings)))


def plan_of(cfg: dict) -> dict[str, int]:
    return {str(k).lower(): int(v) for k, v in (cfg.get("inbox_plan") or {}).items() if int(v or 0) > 0}


def daily_target(cfg: dict, settings: dict) -> int:
    """First emails to send today: the inbox plan's total, or Emails per inbox x the inboxes, or the batch size."""
    plan = plan_of(cfg)
    if plan:
        return sum(plan.values())
    per = int(cfg.get("per_inbox") or 0)
    return per * inbox_count(cfg, settings) if per > 0 else int(cfg.get("batch_size") or 20)


def search_size(cfg: dict, settings: dict, waiting: int) -> int:
    """How many new firms today's search should find: enough to reach the target, given those already waiting."""
    import math

    short = daily_target(cfg, settings) - waiting
    return 0 if short <= 0 else min(1000, math.ceil(short * FIND_BUFFER))


def guarded(cfg: dict, settings: dict, r: "Run", today) -> tuple[dict, bool]:
    """(today's config, whether anything may be sent): the inbox plan after warm-up and protection."""
    import inbox_guard
    import mail_accounts

    if not cfg.get("protect_inboxes"):
        return cfg, True
    inboxes = [a.address for a in mail_accounts.accounts(settings)]
    base = plan_of(cfg)
    if not base and int(cfg.get("per_inbox") or 0) > 0:
        frm = str(cfg.get("send_from") or "").strip().lower()
        base = {a: int(cfg["per_inbox"]) for a in ([frm] if frm else inboxes)}
    if not base:
        return cfg, True
    plan, notes = inbox_guard.plan_for_today(base, panel.OUTREACH, inboxes[0] if inboxes else "", today)
    for line in notes:
        r.note(line)
    live = {k: v for k, v in plan.items() if v > 0}
    if not live:
        r.note("Inbox plan: every inbox is paused today - nothing will be sent (see above).")
        return {**cfg, "inbox_plan": {}}, False
    return {**cfg, "inbox_plan": live}, True


def video_targets(settings: dict, today, made: set[str]) -> list[str]:
    """Firms that opened their preview 2+ times in the last 3 days, have no video yet, and aren't won or lost."""
    import calls

    secret = settings.get("PROSPECTS_API_SECRET", "")
    api = (settings.get("DASHBOARD_API_URL") or "https://admin.scalardigital.co.uk").rstrip("/")
    tenant = os.environ.get("SCALAR_TENANT_ID", "abdc6408-1fd5-4fb6-9c4c-53600b571a6d")
    try:
        activity = calls.fetch_activity(api, secret, tenant)
    except calls.DashboardMissing:
        return []
    out = []
    for slug, a in activity.items():
        last = str(a.get("last_viewed_at") or "")[:10]
        try:
            recent = (today - datetime.fromisoformat(last).date()).days <= 3
        except ValueError:
            recent = False
        if int(a.get("view_count") or 0) >= 2 and recent and a.get("status") not in ("won", "lost") and slug not in made:
            out.append((a.get("last_viewed_at") or "", slug))
    return [s for _, s in sorted(out, reverse=True)][:VIDEOS_A_MORNING]


def make_videos(r: "Run", settings: dict, today) -> None:
    import importlib.util

    import daily

    if not (importlib.util.find_spec("playwright") and importlib.util.find_spec("imageio_ffmpeg")):
        r.note("Walkthrough videos are on, but the video maker isn't installed - Settings -> Install video maker.")
        return
    made = {row.get("slug") for row in _csv_rows(panel.OUTREACH / daily.VIDEOS)}
    targets = video_targets(settings, today, made)
    if targets:
        r.note(f"--- Walkthrough videos for {len(targets)} repeat viewer(s)")
    for slug in targets:
        r.step(panel.AUTO_VIDEO, ["--link", slug])


def _csv_rows(path: Path) -> list[dict]:
    import csv

    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def make_batches(r: "Run", cfg: dict, settings: dict | None = None) -> None:
    size = daily_target(cfg, settings or {}) if settings is not None else int(cfg.get("batch_size") or 20)
    r.step(panel.BATCHES, ["--size", str(size)])
    if cfg.get("followups"):
        r.step(panel.BATCHES, ["--followups", "--size", str(int(cfg.get("followup_size") or 20)),
                               "--after-days", str(int(cfg.get("followup_after_days") or 5))])


def send_args(cfg: dict) -> list[str]:
    """--gap-minutes and --from for the send step, from the Autopilot card."""
    try:
        gap = min(60.0, max(0.0, float(cfg.get("send_gap") or 0)))
    except (TypeError, ValueError):
        gap = 0.0
    frm = str(cfg.get("send_from") or "").strip().lower()
    plan = plan_of(cfg)
    if plan:  # the plan says which inboxes send - not one "send from" inbox
        frm = ""
    per_inbox = bool(cfg.get("gap_per_inbox")) and gap and not frm
    limit = 0 if plan else int(cfg.get("per_inbox") or 0)
    return ([f"--gap-minutes={gap:g}"] if gap else []) + (["--from", frm] if frm else []) + (["--gap-per-inbox"] if per_inbox else []) \
        + ([f"--per-inbox-limit={limit}"] if limit > 0 else []) \
        + (["--inbox-plan=" + ",".join(f"{k}={v}" for k, v in plan.items())] if plan else [])


def start_delay(cfg: dict, rand=None) -> int:
    """Seconds to wait before a scheduled run starts: a random moment between "time" and "time_to"."""
    import random

    at, until = str(cfg.get("time") or ""), str(cfg.get("time_to") or "")
    if not (re.fullmatch(r"\d{2}:\d{2}", at) and re.fullmatch(r"\d{2}:\d{2}", until)):
        return 0
    span = (int(until[:2]) * 60 + int(until[3:])) - (int(at[:2]) * 60 + int(at[3:]))
    if span <= 0:
        return 0
    return int((rand or random.uniform)(0, span * 60))


def morning_send(r: "Run", cfg: dict, settings: dict) -> bool:
    """Opt-in only: make today's batches and send them now. True if it ran."""
    if not cfg.get("auto_send"):
        return False
    if not (settings.get("MAIL_ADDRESS") and settings.get("MAIL_APP_PASSWORD") and settings.get("MAIL_FROM_NAME")):
        r.note("Send automatically is on, but MAIL_ADDRESS, MAIL_APP_PASSWORD or MAIL_FROM_NAME isn't in Settings - "
               "making the batches without sending them.")
        return False
    r.note("--- Morning send")
    make_batches(r, cfg, settings)
    r.step(panel.SEND, send_args(cfg))
    if cfg.get("followups"):
        r.step(panel.SEND, ["--followups", *send_args(cfg)])
    return True


def run(scheduled: bool = False, sleep=time.sleep) -> int:
    panel.OUTREACH.mkdir(exist_ok=True)
    if is_running():
        print("Autopilot is already running.")
        return 1
    lock = panel.OUTREACH / LOCK
    lock.write_text(str(os.getpid()))
    cfg = load_config()
    r = Run(panel.OUTREACH / "autopilot-log.txt")
    panel.keep_awake(True)
    try:
        wait = start_delay(cfg) if scheduled else 0
        if wait:
            start_at = datetime.fromtimestamp(time.time() + wait)
            r.note(f"Scheduled run: starting at {start_at:%H:%M} (a random time between {cfg['time']} and {cfg['time_to']}).")
            sleep(wait)  # keep_awake holds the PC awake through the wait
    except BaseException:
        panel.keep_awake(False)
        lock.unlink(missing_ok=True)
        r.log.close()
        raise
    started = time.time()
    try:
        r.note(f"Autopilot started {datetime.now().strftime('%A %d %B %Y %H:%M')}")
        settings = panel.load_settings()
        if len(settings.get("PROSPECTS_API_SECRET", "")) < 32:
            r.note("PROSPECTS_API_SECRET isn't in Settings - nothing can be pushed. Stopping.")
            return 1

        ok, published = panel.publish_quotes()  # keeps "See my quote" on preview pages in step with Settings
        if not ok:
            r.note(f"Self-serve quotes: {published}")

        if settings.get("MAIL_ADDRESS") and settings.get("MAIL_APP_PASSWORD"):
            r.step(panel.REPLIES, [])

        if settings.get("MAIL_ADDRESS"):
            r.step(panel.SENDING_HEALTH, [])  # before anything is sent: a blocklisting stops the send
        today = datetime.now().date()
        weekend = bool(cfg.get("weekdays_only")) and today.weekday() >= 5
        if weekend:
            r.note("Weekend: replies and the lists only today - no search, nothing sent (Weekdays only is on).")
        cfg, may_send = guarded(cfg, settings, r, today)
        sending_today = may_send and not weekend
        if cfg.get("auto_videos"):
            make_videos(r, settings, today)  # before the 8:30 nudges, so the video's on the page when you follow up
        send_last = cfg.get("send_when") == "last"
        sent_early = False if send_last or not sending_today else morning_send(r, cfg, settings)

        new_sheet = None
        find = cfg.get("find") or {}
        if weekend or not may_send:
            find = {}
        if find.get("trades") and find.get("areas") and (int(cfg.get("per_inbox") or 0) > 0 or plan_of(cfg)):
            import email_batches

            waiting = email_batches.remaining(panel.OUTREACH, None)
            need = search_size(cfg, settings, waiting)
            split = (", ".join(f"{k} {v}" for k, v in plan_of(cfg).items()) if plan_of(cfg)
                     else f"{cfg['per_inbox']} x {inbox_count(cfg, settings)} inbox(es)")
            r.note(f"Today's target: {daily_target(cfg, settings)} emails ({split}); "
                   f"{waiting} checked firms already waiting" + (f" - searching for {need} more." if need else " - no search needed today."))
            find = {**find, "max": need} if need else {}
        if find.get("trades") and find.get("areas"):
            before = set(panel.sheets())
            args, error = panel.build_find_args({**find, "action": "find"}, settings)
            if args is None:
                r.note(f"Saved search skipped: {error}")
            else:
                r.step(panel.FIND, args)
                made = set(panel.sheets()) - before
                new_sheet = max(made, key=lambda n: (panel.OUTREACH / n).stat().st_mtime) if made else None
                if new_sheet and settings.get("ANTHROPIC_API_KEY"):
                    # "Possible" websites confirmed (or ruled out) before the list runs, so more of today's
                    # firms get a preview and an email instead of waiting on the Review tab.
                    r.step(panel.SITE_CHECK, ["--sheet", new_sheet])
        elif not cfg.get("find") and sending_today:
            r.note("No saved search - skipping new firms (save one on the panel's Autopilot card).")

        for name in lists_to_run(new_sheet):
            r.note(f"--- {name}")
            path = str(panel.OUTREACH / name)
            for step in panel.run_all_steps(r, path, name, settings):
                script, args = step if isinstance(step, tuple) else (panel.PUSH, step)
                if script in (panel.REPLIES, panel.EXPORT):
                    continue  # once per run, not per list
                r.step(script, args)

        if send_last and sending_today:
            if settings.get("MAIL_ADDRESS") and settings.get("MAIL_APP_PASSWORD"):
                r.step(panel.REPLIES, [])  # anyone who said no while the list ran is left out of the send
            sent_early = morning_send(r, cfg, settings)
        if not sent_early and sending_today:
            make_batches(r, cfg, settings)
        r.sent_early = sent_early
        r.step(panel.EXPORT, [])
        r.step(panel.BACKUP, [])  # last, so the copy includes everything today changed
        if scorecard_day():  # the weekly scorecard goes in Monday's text too
            start = len(r.lines)
            r.step(panel.HERE / "scorecard.py", [])
            r.scorecard = [ln.strip() for ln in r.lines[start + 1:] if ln.strip() and not ln.startswith("> ") and "had a problem" not in ln]
        return summarise(r, settings, time.time() - started)
    finally:
        panel.keep_awake(False)
        lock.unlink(missing_ok=True)
        r.log.close()


SUMMARY_LINE = re.compile(r"^\s*(READY|Inbox plan:|Weekend:|Found \d+ new|Wrote .*(firms|\.xlsx)|List done|No follow-ups|Nobody left|  \d+ (added|bounced))")


def summarise(r: Run, settings: dict, seconds: float) -> int:
    picked = [ln.strip() for ln in r.lines if SUMMARY_LINE.match(ln)]
    replies = next((ln.strip() for ln in r.lines if "Found " in ln and " new:" in ln), "")
    mins = int(seconds // 60)
    head = f"Autopilot done in {mins // 60}h {mins % 60}m" if mins >= 60 else f"Autopilot done in {mins}m"
    body = [head]
    if replies:
        body.append("Replies: " + replies.split(": ", 1)[-1])
    body += [ln for ln in picked if ln.startswith(("READY", "Inbox plan:", "Weekend:"))]
    if r.failed:
        body.append(f"{len(r.failed)} step(s) had problems - see autopilot-log.txt")
    sent = [ln.strip() for ln in r.lines if ln.strip().startswith("Done: ") and " sent" in ln]
    if getattr(r, "sent_early", False):
        body += sent or ["Send automatically was on, but nothing was sent - see autopilot-log.txt."]
    else:
        body.append("Next: open the panel and press Send today's batch (and Send follow-ups).")
    if getattr(r, "scorecard", None):
        body += ["", "Weekly scorecard:", *r.scorecard]
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
    command = f'"{runner}" "{Path(__file__).resolve()}" --scheduled'
    if workspace.folder_name() != workspace.DEFAULT:
        command += f' --workspace "{workspace.folder_name()}"'
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
    ap.add_argument("--scheduled", action="store_true", help="started by the daily schedule: wait for the random start")
    ap.add_argument("--workspace", default="", help="outreach folder, e.g. outreach-us (read before anything loads)")
    args = ap.parse_args()
    if args.install:
        err = install(load_config().get("time") or "07:30")
        sys.exit(err or 0)
    if args.remove:
        sys.exit(remove() or 0)
    sys.exit(run(scheduled=args.scheduled))


if __name__ == "__main__":
    main()
