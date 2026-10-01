"""The panel's page (panel.html) - loads, has its placeholders, and its JavaScript parses."""

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import control_panel as cp  # noqa: E402


class PanelPage(unittest.TestCase):
    def test_loaded_from_panel_html(self):
        self.assertEqual(cp.PAGE, (HERE / "panel.html").read_text(encoding="utf-8"))
        self.assertTrue(cp.PAGE.startswith("<!doctype html>"))

    def test_placeholders_the_server_fills_in(self):
        self.assertIn("__TOKEN__", cp.PAGE)
        self.assertIn("__VERSION__", cp.PAGE)

    @unittest.skipUnless(shutil.which("node"), "node isn't installed")
    def test_script_parses(self):
        scripts = re.findall(r"<script>(.*?)</script>", cp.PAGE, re.S)
        self.assertTrue(scripts)
        with tempfile.TemporaryDirectory() as d:
            for n, js in enumerate(scripts):
                path = Path(d) / f"panel{n}.js"
                path.write_text(js.replace("__TOKEN__", "t").replace("__VERSION__", "0"), encoding="utf-8")
                res = subprocess.run(["node", "--check", str(path)], capture_output=True, text=True)
                self.assertEqual(res.returncode, 0, res.stderr)


if __name__ == "__main__":
    unittest.main()
