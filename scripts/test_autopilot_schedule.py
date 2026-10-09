"""autopilot: a random start inside a window, sending after the list run, and the gap per inbox.

Run: python -m unittest scripts/test_autopilot_schedule.py
"""

import unittest
from unittest import mock

import autopilot


class Schedule(unittest.TestCase):
    def test_random_start_inside_the_window(self):
        self.assertEqual(autopilot.start_delay({"time": "05:00", "time_to": "07:00"}, rand=lambda a, b: b), 7200)
        self.assertEqual(autopilot.start_delay({"time": "05:00", "time_to": "07:00"}, rand=lambda a, b: a), 0)
        self.assertEqual(autopilot.start_delay({"time": "05:00", "time_to": ""}), 0)
        self.assertEqual(autopilot.start_delay({"time": "07:00", "time_to": "05:00"}), 0)

    def test_send_args_gap_per_inbox_only_when_spreading(self):
        self.assertEqual(autopilot.send_args({"send_gap": 6, "gap_per_inbox": True}), ["--gap-minutes=6", "--gap-per-inbox"])
        self.assertEqual(autopilot.send_args({"send_gap": 6, "gap_per_inbox": True, "send_from": "a@b.co.uk"}),
                         ["--gap-minutes=6", "--from", "a@b.co.uk"])
        self.assertEqual(autopilot.send_args({"send_gap": 6}), ["--gap-minutes=6"])

    def test_panel_saves_the_window_and_options(self):
        import control_panel as cp

        saved = {}
        with mock.patch.object(autopilot, "load_config", lambda: dict(autopilot.DEFAULTS)), \
             mock.patch.object(autopilot, "save_config", lambda cfg: saved.update(cfg)), \
             mock.patch.object(autopilot, "install", lambda at: ""):
            out, code = cp.autopilot_action({"action": "on", "config": {
                "time": "05:00", "time_to": "07:00", "send_when": "last", "gap_per_inbox": True, "auto_send": True,
                "send_gap": 6, "batch_size": 100}})
            self.assertEqual(code, 200, out)
            self.assertEqual((saved["time_to"], saved["send_when"], saved["gap_per_inbox"]), ("07:00", "last", True))
            self.assertIn("random time between 05:00 and 07:00", out["message"])
            self.assertIn("after the search and list, 6 min apart per inbox", out["message"])
            bad, code = cp.autopilot_action({"action": "save", "config": {"time": "07:00", "time_to": "05:00"}})
            self.assertEqual(code, 400)

    def test_scheduled_run_waits_then_sends_after_the_lists(self):
        steps = []

        class R:
            def __init__(self, path):
                self.lines, self.log = [], mock.Mock()

            def note(self, line):
                steps.append(("note", line))

            def step(self, script, args):
                steps.append((getattr(script, "name", str(script)), tuple(args)))
                return 0

        cfg = {**autopilot.DEFAULTS, "time": "05:00", "time_to": "07:00", "auto_send": True, "send_when": "last",
               "send_gap": 6, "gap_per_inbox": True}
        settings = {"PROSPECTS_API_SECRET": "x" * 40, "MAIL_ADDRESS": "a@b.co.uk", "MAIL_APP_PASSWORD": "p", "MAIL_FROM_NAME": "J"}
        waited = []
        with mock.patch.object(autopilot, "is_running", lambda: False), mock.patch.object(autopilot, "load_config", lambda: cfg), \
             mock.patch.object(autopilot, "Run", R), mock.patch.object(autopilot, "start_delay", lambda c: 1234), \
             mock.patch.object(autopilot.panel, "keep_awake", lambda on: None), \
             mock.patch.object(autopilot.panel, "load_settings", lambda: settings), \
             mock.patch.object(autopilot.panel, "publish_quotes", lambda: (True, "")), \
             mock.patch.object(autopilot, "lists_to_run", lambda new: []), \
             mock.patch.object(autopilot, "summarise", lambda r, s, t: 0), \
             mock.patch.object(autopilot, "scorecard_day", lambda: False):
            autopilot.run(scheduled=True, sleep=waited.append)
        self.assertEqual(waited, [1234])
        names = [s[0] for s in steps if s[0] != "note"]
        send_at = names.index("send_email.py")
        self.assertGreater(send_at, names.index("email_batches.py"))
        self.assertEqual(names.count("reply_scanner.py"), 2)  # again just before sending
        self.assertIn("--gap-per-inbox", steps[[i for i, s in enumerate(steps) if s[0] == "send_email.py"][0]][1])


if __name__ == "__main__":
    unittest.main()
