"""panel_startup: a launcher in your own Startup folder - no administrator rights needed."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import panel_startup


class Startup(unittest.TestCase):
    def test_install_and_remove(self):
        appdata = Path(tempfile.mkdtemp())
        folder = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        folder.mkdir(parents=True)
        with mock.patch.dict("os.environ", {"APPDATA": str(appdata)}), mock.patch.object(sys, "platform", "win32"):
            self.assertEqual(panel_startup.install(), "")
            text = (folder / panel_startup.NAME).read_bytes().decode("utf-8")
            self.assertIn("control_panel.py\" --no-browser", text)
            self.assertTrue(text.startswith("@echo off\r\nstart \"\" "))
            self.assertEqual(panel_startup.remove(), "")
            self.assertFalse((folder / panel_startup.NAME).exists())
            self.assertEqual(panel_startup.remove(), "")  # nothing there: still fine

    def test_no_startup_folder(self):
        with mock.patch.dict("os.environ", {"APPDATA": str(Path(tempfile.mkdtemp()))}), mock.patch.object(sys, "platform", "win32"):
            self.assertIn("Startup folder", panel_startup.install())


if __name__ == "__main__":
    unittest.main()
