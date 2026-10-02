"""autopilot.now_doing / stop: a long run reads as busy, and a stuck one can be stopped from the panel."""

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

import autopilot


class NowAndStop(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp())

    def test_says_what_it_is_doing_and_for_how_long(self):
        self.assertEqual(autopilot.now_doing(self.out), {})
        lock = self.out / autopilot.LOCK
        lock.write_text("1")
        old = time.time() - 42 * 60
        os.utime(lock, (old, old))
        (self.out / "autopilot-log.txt").write_text("07:30  Autopilot started\n07:31  > send_email.py\n08:12    [7/20] sent to Kerr Roofing\n", encoding="utf-8")
        self.assertEqual(autopilot.now_doing(self.out), {"minutes": 42, "last": "[7/20] sent to Kerr Roofing"})

    def test_stop_ends_the_run_and_clears_the_lock(self):
        proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        try:
            (self.out / autopilot.LOCK).write_text(str(proc.pid))
            msg = autopilot.stop(self.out)
            self.assertIn("stopped", msg.lower())
            self.assertEqual(proc.wait(timeout=10), -15 if sys.platform != "win32" else proc.returncode)
            self.assertFalse((self.out / autopilot.LOCK).exists())
            self.assertIn("Stopped from the panel", (self.out / "autopilot-log.txt").read_text(encoding="utf-8"))
        finally:
            if proc.poll() is None:
                proc.kill()

    def test_stop_with_nothing_running(self):
        self.assertIn("isn't running", autopilot.stop(self.out))

    def test_a_reused_process_number_is_not_the_run(self):
        from unittest import mock

        import control_panel as panel

        started = autopilot._started(os.getpid())
        if started is None:
            self.skipTest("can't read process start times here")
        lock = self.out / autopilot.LOCK
        with mock.patch.object(panel, "OUTREACH", self.out):
            # Written after this process started: it's the run.
            lock.write_text(str(os.getpid()))
            self.assertTrue(autopilot.is_running())
            # Written well before this process existed: the number was handed out again - stale, cleared.
            os.utime(lock, (started - 600, started - 600))
            self.assertFalse(autopilot.is_running())
            self.assertFalse(lock.exists())


if __name__ == "__main__":
    unittest.main()
