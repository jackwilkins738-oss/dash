"""Offline tests for the uptime check: a blip isn't an alert, and each outage is texted once each way."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import uptime_check as uc


class Uptime(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = mock.patch.object(uc, "STATE", Path(self.tmp.name) / "state.json")
        self.state.start()

    def tearDown(self):
        self.state.stop()
        self.tmp.cleanup()

    def run_with(self, answers):
        sent = []
        with mock.patch.object(uc, "status", side_effect=answers), mock.patch.object(uc, "send", sent.append), \
                mock.patch("builtins.print"):
            uc.main(sleep=lambda s: None)
        return sent

    def test_a_blip_is_not_an_outage(self):
        self.assertEqual(self.run_with(["HTTP 502", "up", "up"]), [])

    def test_down_once_then_quiet_then_back_once(self):
        down = ["unreachable (timed out)", "unreachable (timed out)", "up"]
        sent = self.run_with(down)
        self.assertEqual(len(sent), 1)
        self.assertIn("Website is DOWN", sent[0])
        self.assertEqual(self.run_with(down), [])  # still down: no repeat text
        sent = self.run_with(["up", "up"])
        self.assertEqual(sent, ["Website is back up: https://www.scalardigital.co.uk/."])

    def test_a_failed_text_is_retried(self):
        with mock.patch.object(uc, "status", side_effect=["HTTP 500", "HTTP 500", "up"]), \
                mock.patch.object(uc, "send", side_effect=OSError("down")), mock.patch("builtins.print"):
            self.assertEqual(uc.main(sleep=lambda s: None), 1)
        self.assertFalse(uc.STATE.exists())
        self.assertEqual(len(self.run_with(["HTTP 500", "HTTP 500", "up"])), 1)

    def test_state_remembers_each_site(self):
        self.run_with(["up", "HTTP 503", "HTTP 503"])
        self.assertEqual(json.loads(uc.STATE.read_text()), {"Website": "up", "Dashboard": "HTTP 503"})


if __name__ == "__main__":
    unittest.main()
