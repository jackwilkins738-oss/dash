"""Offline tests for the 15-minute reply check (reply_watch.py) and the reply check's lock and alert."""

import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

import reply_scanner as rs
import reply_watch as rw


class Lock(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_two_checks_never_run_at_once(self):
        with rs.reply_lock(self.d):
            with self.assertRaises(rs.Busy):
                with rs.reply_lock(self.d):
                    pass
        with rs.reply_lock(self.d):  # released afterwards
            pass

    def test_a_lock_left_by_a_crashed_check_expires(self):
        lock = self.d / rs.LOCK
        lock.write_text("")
        old = datetime.now().timestamp() - rs.LOCK_STALE_S - 60
        import os

        os.utime(lock, (old, old))
        with rs.reply_lock(self.d):
            pass

    def test_a_busy_check_says_so_and_does_nothing(self):
        with mock.patch.object(rs, "outreach_dir", return_value=self.d), mock.patch.object(rs, "_check") as check:
            with rs.reply_lock(self.d):
                with mock.patch("builtins.print") as printed:
                    rs.main()
        check.assert_not_called()
        self.assertIn("skipped", str(printed.call_args[0][0]))


class Alert(unittest.TestCase):
    def test_says_who_and_what_they_said(self):
        text = rs.alert_text([
            {"kind": "interested", "business": "Kerr Roofing", "from": "bill@kerr.co.uk", "snippet": "Yes  please,\nhow much?"},
            {"kind": "not interested", "business": "Nope Ltd", "from": "x@nope.co.uk", "snippet": "no"},
        ])
        self.assertIn('Kerr Roofing replied and sounds interested (bill@kerr.co.uk):\n"Yes please, how much?"', text)
        self.assertNotIn("Nope", text)

    def test_nothing_hot_no_alert(self):
        self.assertEqual(rs.alert_text([{"kind": "bounce", "business": "", "from": "a@b.c", "snippet": ""}]), "")


class Watch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_schedule_is_every_15_minutes_through_the_working_day(self):
        cmd = rw.schedule_command(Path("C:/Python/pythonw.exe"))
        self.assertEqual(cmd[cmd.index("/SC") + 1], "DAILY")
        self.assertEqual((cmd[cmd.index("/ST") + 1], cmd[cmd.index("/RI") + 1], cmd[cmd.index("/DU") + 1]), ("08:00", "15", "12:00"))
        self.assertIn("pythonw.exe", cmd[cmd.index("/TR") + 1])

    def test_log_keeps_one_line_per_check_for_the_panel(self):
        self.assertIsNone(rw.last_check(self.d))
        rw.append_log(self.d, "No new replies from anyone you've contacted.", datetime(2026, 10, 1, 10, 15))
        rw.append_log(self.d, "Found 2 new: 1 interested, 1 read it.", datetime(2026, 10, 1, 10, 30))
        self.assertEqual(rw.last_check(self.d), {"at": "2026-10-01 10:30", "line": "Found 2 new: 1 interested, 1 read it."})

    def test_summary_picks_the_line_that_matters(self):
        out = "Checking a@x.co.uk ...\n  interested   Kerr\nFound 1 new: 1 interested.\n  Replies worth answering..."
        self.assertEqual(rw.summarise(out), "Found 1 new: 1 interested.")
        self.assertEqual(rw.summarise("Checking...\nNo new replies from anyone you've contacted."), "No new replies from anyone you've contacted.")

    def test_a_failed_check_is_logged_not_crashed(self):
        import control_panel

        def boom():
            raise SystemExit("The inbox refused the login (bad password).")

        import contextlib
        import io

        with mock.patch.object(control_panel, "load_settings", return_value={}), \
                mock.patch.object(rs, "outreach_dir", return_value=self.d), mock.patch.object(rs, "main", boom), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(rw.run(), 1)
        self.assertIn("refused the login", rw.last_check(self.d)["line"])

    def test_panel_buttons_install_and_remove(self):
        import control_panel as cp

        settings = {"MAIL_ADDRESS": "a@x.co.uk", "MAIL_APP_PASSWORD": "p"}
        make, err = cp.build_steps({"action": "reply_watch_on"}, settings)
        self.assertEqual(make(None), [(cp.REPLY_WATCH, ["--install"])])
        make, err = cp.build_steps({"action": "reply_watch_off"}, {})
        self.assertEqual(make(None), [(cp.REPLY_WATCH, ["--remove"])])
        self.assertIsNone(cp.build_steps({"action": "reply_watch_on"}, {})[0])


if __name__ == "__main__":
    unittest.main()
