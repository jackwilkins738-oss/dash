"""Autopilot's opt-in morning send: off unless ticked, sends with the card's inbox and gap, never without a login."""

import unittest

import autopilot
import control_panel as panel

MAIL = {"MAIL_ADDRESS": "a@b.co.uk", "MAIL_APP_PASSWORD": "x", "MAIL_FROM_NAME": "Ash"}


class FakeRun:
    def __init__(self):
        self.steps, self.lines = [], []

    def step(self, script, args):
        self.steps.append((script.name, list(args)))
        return 0

    def note(self, line):
        self.lines.append(line)


class MorningSend(unittest.TestCase):
    def test_off_by_default_sends_nothing(self):
        r = FakeRun()
        self.assertFalse(autopilot.DEFAULTS["auto_send"])
        self.assertFalse(autopilot.morning_send(r, dict(autopilot.DEFAULTS), MAIL))
        self.assertEqual(r.steps, [])

    def test_on_makes_the_batches_then_sends_them_with_the_cards_settings(self):
        r = FakeRun()
        cfg = {**autopilot.DEFAULTS, "auto_send": True, "send_gap": 5, "send_from": "Ash@GetScalar.co.uk"}
        self.assertTrue(autopilot.morning_send(r, cfg, MAIL))
        names = [s[0] for s in r.steps]
        self.assertEqual(names, ["email_batches.py", "email_batches.py", "send_email.py", "send_email.py"])
        self.assertEqual(r.steps[2][1], ["--gap-minutes=5", "--from", "ash@getscalar.co.uk"])
        self.assertEqual(r.steps[3][1][0], "--followups")

    def test_no_login_means_batches_only(self):
        r = FakeRun()
        cfg = {**autopilot.DEFAULTS, "auto_send": True}
        self.assertFalse(autopilot.morning_send(r, cfg, {"MAIL_ADDRESS": "a@b.co.uk"}))
        self.assertEqual(r.steps, [])
        self.assertTrue(any("without sending" in ln for ln in r.lines))

    def test_send_args_are_kept_in_range(self):
        self.assertEqual(autopilot.send_args({"send_gap": 500}), ["--gap-minutes=60"])
        self.assertEqual(autopilot.send_args({"send_gap": "soon"}), [])
        self.assertEqual(autopilot.send_args({}), [])


class AutopilotCard(unittest.TestCase):
    def test_saving_auto_send_is_validated(self):
        saved = {}
        orig_load, orig_save = autopilot.load_config, autopilot.save_config
        autopilot.load_config = lambda: dict(autopilot.DEFAULTS)
        autopilot.save_config = lambda cfg: saved.update(cfg)
        try:
            body = {"action": "save", "config": {"time": "06:45", "auto_send": True, "send_gap": "5", "send_from": "ash@getscalar.co.uk"}}
            out, code = panel.autopilot_action(body)
            self.assertEqual(code, 200)
            self.assertEqual((saved["auto_send"], saved["send_gap"], saved["send_from"]), (True, 5.0, "ash@getscalar.co.uk"))
            bad = {"action": "save", "config": {"time": "06:45", "send_gap": "90"}}
            self.assertEqual(panel.autopilot_action(bad)[1], 400)
        finally:
            autopilot.load_config, autopilot.save_config = orig_load, orig_save


if __name__ == "__main__":
    unittest.main()
