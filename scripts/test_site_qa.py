"""Offline tests for site_qa - real site_kit builds, then broken on purpose.

Run: python -m unittest scripts/test_site_qa.py
"""

import json
import tempfile
import unittest
from pathlib import Path

import site_kit
import site_qa
import test_site_kit


class SiteQA(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        (self.folder / "site.json").write_text(json.dumps(test_site_kit.config()))
        site_kit.build(self.folder)
        self.site = self.folder / "site"

    def test_a_real_build_passes_clean(self):
        self.assertEqual(site_qa.check(self.site), ([], []))
        self.assertEqual(site_qa.report(self.site), 0)

    def test_a_draft_build_is_stopped(self):
        cfg = test_site_kit.config(hours="[Confirm: hours]")
        (self.folder / "site.json").write_text(json.dumps(cfg))
        site_kit.build(self.folder, draft=True)
        problems, _ = site_qa.check(self.site)
        self.assertTrue(any("robots.txt blocks Google" in p for p in problems))
        self.assertTrue(any("placeholder text" in p for p in problems))

    def test_each_kind_of_breakage_is_named(self):
        home = self.site / "index.html"
        html = home.read_text(encoding="utf-8")
        html = html.replace("</body>", '<a href="/missing.html">x</a><img src="/logo-nope.png"><script type="application/ld+json">{bad</script></body>', 1)
        home.write_text(html, encoding="utf-8")
        contact = self.site / "contact.html"
        contact.write_text(contact.read_text(encoding="utf-8").replace("data-lead-form", "data-x"), encoding="utf-8")
        (self.site / "404.html").unlink()
        (self.site / "_redirects").write_text("/old-page /gone.html 301\n", encoding="utf-8")
        (self.site / "big.jpg").write_bytes(b"0" * (site_qa.BIG_IMAGE + 1))
        problems, warnings = site_qa.check(self.site)
        text = "\n".join(problems)
        for bit in ("broken link to /missing.html", "broken link to /logo-nope.png", "has no alt text", "isn't valid JSON",
                    "contact.html: the quote form", "no 404.html", "/old-page goes to /gone.html"):
            self.assertIn(bit, text)
        self.assertTrue(any("big.jpg" in w for w in warnings))
        self.assertEqual(site_qa.report(self.site), 1)

    def test_no_build_yet(self):
        problems, _ = site_qa.check(Path(tempfile.mkdtemp()) / "site")
        self.assertIn("Build site", problems[0])


if __name__ == "__main__":
    unittest.main()
