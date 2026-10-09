"""Inbox guard (warm-up, auto-pause), weekdays only and automatic videos - offline.

Run: python -m unittest scripts/test_autopilot_extras.py
"""

import csv
import json
import tempfile
import unittest
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

import autopilot
import inbox_guard as ig

TODAY = date(2026, 10, 12)  # a Monday


def sent(d: Path, rows):
    with (d / "emails-sent.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["email", "sent", "sent_from"])
        w.writeheader()
        w.writerows(rows)


class Guard(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_warm_up_by_week(self):
        self.assertEqual(ig.warm_limit(None, TODAY), 10)
        self.assertEqual(ig.warm_limit(TODAY - timedelta(days=6), TODAY), 10)
        self.assertEqual(ig.warm_limit(TODAY - timedelta(days=14), TODAY), 20)

    def test_new_inbox_warms_old_one_runs_full_bad_one_paused(self):
        rows = [{"email": f"o{i}@x.co.uk", "sent": "2026-09-01", "sent_from": "old@a.co.uk"} for i in range(5)]
        rows += [{"email": f"b{i}@x.co.uk", "sent": "2026-10-05", "sent_from": "bad@b.co.uk"} for i in range(20)]
        sent(self.d, rows)
        with (self.d / "email-checks.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["email", "result", "checked_at"])
            w.writerows([[f"b{i}@x.co.uk", "bounced", ""] for i in range(3)])
        (self.d / "sending-health.json").write_text(json.dumps({"problems": ["dns.co.uk: no SPF record"]}))
        plan, notes = ig.plan_for_today({"old@a.co.uk": 25, "new@c.co.uk": 25, "bad@b.co.uk": 25, "dns@dns.co.uk": 25},
                                        self.d, "old@a.co.uk", TODAY)
        self.assertEqual(plan, {"old@a.co.uk": 25, "new@c.co.uk": 10, "bad@b.co.uk": 0, "dns@dns.co.uk": 0})
        text = "\n".join(notes)
        self.assertIn("new@c.co.uk warming up - 10 today (of your 25)", text)
        self.assertIn("bad@b.co.uk paused - 3 of its last 20 emails bounced (15%)", text)
        self.assertIn("dns@dns.co.uk paused - dns.co.uk: no SPF record", text)


class Run(unittest.TestCase):
    def go(self, cfg, today=TODAY, activity=None, installed=True):
        steps, notes = [], []

        class R:
            def __init__(self, path):
                self.lines, self.log = [], mock.Mock()

            def note(self, line):
                notes.append(line)

            def step(self, script, args):
                steps.append((getattr(script, "name", str(script)), tuple(args)))
                return 0

        settings = {"PROSPECTS_API_SECRET": "x" * 40, "MAIL_ADDRESS": "a@a.co.uk", "MAIL_APP_PASSWORD": "p", "MAIL_FROM_NAME": "J"}
        cfg = {**autopilot.DEFAULTS, "auto_send": True, "send_gap": 6, **cfg}

        class FakeDate(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(today.year, today.month, today.day, 6, 0)

        import calls
        import importlib.util as iu

        with mock.patch.object(autopilot, "is_running", lambda: False), mock.patch.object(autopilot, "load_config", lambda: cfg), \
             mock.patch.object(autopilot, "Run", R), mock.patch.object(autopilot, "datetime", FakeDate), \
             mock.patch.object(autopilot.panel, "keep_awake", lambda on: None), \
             mock.patch.object(autopilot.panel, "load_settings", lambda: settings), \
             mock.patch.object(autopilot.panel, "publish_quotes", lambda: (True, "")), \
             mock.patch.object(autopilot.panel, "OUTREACH", Path(tempfile.mkdtemp())), \
             mock.patch.object(calls, "fetch_activity", lambda api, s, t: activity or {}), \
             mock.patch.object(iu, "find_spec", lambda name: object() if installed else None), \
             mock.patch.object(autopilot, "lists_to_run", lambda new: []), \
             mock.patch.object(autopilot, "summarise", lambda r, s, t: 0), mock.patch.object(autopilot, "scorecard_day", lambda: False):
            autopilot.run()
        return [s[0] for s in steps], steps, notes

    def test_weekend_sends_nothing(self):
        names, _, notes = self.go({"weekdays_only": True, "per_inbox": 20}, today=date(2026, 10, 10))
        self.assertNotIn("send_email.py", names)
        self.assertNotIn("email_batches.py", names)
        self.assertIn("Weekend: replies and the lists only today - no search, nothing sent (Weekdays only is on).", notes)

    def test_weekday_sends_with_the_guarded_plan(self):
        names, steps, notes = self.go({"protect_inboxes": True, "per_inbox": 25})
        send = next(s for s in steps if s[0] == "send_email.py")
        self.assertIn("--inbox-plan=a@a.co.uk=10", send[1])  # a brand-new inbox starts at 10
        self.assertTrue(any("warming up" in n for n in notes))

    def test_videos_for_repeat_viewers_only(self):
        recent = (datetime(2026, 10, 11, 20, 0)).isoformat()
        activity = {"hot-1": {"view_count": 3, "last_viewed_at": recent, "status": "viewed"},
                    "once-1": {"view_count": 1, "last_viewed_at": recent, "status": "viewed"},
                    "won-1": {"view_count": 5, "last_viewed_at": recent, "status": "won"},
                    "old-1": {"view_count": 4, "last_viewed_at": "2026-09-01T10:00:00", "status": "viewed"}}
        names, steps, _ = self.go({"auto_videos": True}, activity=activity)
        self.assertEqual([s[1] for s in steps if s[0] == "auto_video.py"], [("--link", "hot-1")])
        _, _, notes = self.go({"auto_videos": True}, activity=activity, installed=False)
        self.assertTrue(any("Install video maker" in n for n in notes))


if __name__ == "__main__":
    unittest.main()
