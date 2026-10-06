"""Offline tests for check_preview - no dashboard, no network.

Run: python -m unittest scripts/test_check_preview.py
"""

import csv
import tempfile
import unittest
from pathlib import Path

import openpyxl

import check_preview as cp
from push_prospects import make_slug

SECRET = "x" * 40


class Slug(unittest.TestCase):
    def test_from_a_link_or_bare(self):
        self.assertEqual(cp.slug_from("https://www.scalardigital.co.uk/for/chemplas-a76f9c?src=email"), "chemplas-a76f9c")
        self.assertEqual(cp.slug_from("  chemplas-a76f9c "), "chemplas-a76f9c")
        self.assertIsNone(cp.slug_from("https://example.com/nope"))
        self.assertIsNone(cp.slug_from("rm -rf /"))


class Diagnose(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Outreach"
        ws.append(["Business", "Website"])
        ws.append(["Chemplas", "https://www.chemplas.co.uk/"])
        wb.save(self.dir / "leads.xlsx")
        self.slug = make_slug("Chemplas", "chemplas.co.uk", SECRET)

    def tearDown(self):
        self.tmp.cleanup()

    def log(self, result, score):
        with (self.dir / "teardown-log.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["website", "checked_at", "result", "mobile_score", "lcp_s", "top_issue", "issue_count"])
            w.writerow(["chemplas.co.uk", "2026-10-05T10:00", result, score, "", "", ""])

    def test_finds_the_sheet_row_for_the_link(self):
        m = cp.sheet_matches(self.dir, self.slug, SECRET)
        self.assertEqual([(x["sheet"], x["domain"]) for x in m], [("leads.xlsx", "chemplas.co.uk")])

    def test_names_a_missing_website(self):
        self.log("ok", "41")
        row = {"business_name": "Chemplas", "website": None, "mobile_score": 41, "teardown_at": "2026-10-05T10:00:00Z",
               "teardown": {"checks": {"tapToCall": False}}}
        out = "\n".join(cp.diagnose(self.slug, row, cp.sheet_matches(self.dir, self.slug, SECRET),
                                    cp.log_row(self.dir, "chemplas.co.uk"), 2026))
        self.assertIn("Website:  NONE", out)
        self.assertIn("Findings: 1", out)
        self.assertIn("The dashboard has no website for this page although your sheet does", out)

    def test_score_in_log_but_not_on_the_dashboard(self):
        self.log("ok", "41")
        row = {"business_name": "Chemplas", "website": "chemplas.co.uk", "mobile_score": None, "teardown_at": None}
        out = "\n".join(cp.diagnose(self.slug, row, cp.sheet_matches(self.dir, self.slug, SECRET),
                                    cp.log_row(self.dir, "chemplas.co.uk"), 2026))
        self.assertIn("The speed log has a score but the dashboard doesn't", out)
        self.assertIn("No findings have reached the page", out)

    def test_a_failed_check_and_a_page_no_sheet_makes(self):
        self.log("failed", "")
        row = {"business_name": "Old Name", "website": "chemplas.co.uk", "mobile_score": None, "teardown_at": None}
        out = "\n".join(cp.diagnose("old-name-123abc", row, [], cp.log_row(self.dir, "chemplas.co.uk"), 2026))
        self.assertIn("press Retry failed speed checks", out)
        self.assertIn("No sheet row produces this link any more", out)

    def test_all_good(self):
        self.log("ok", "41")
        row = {"business_name": "Chemplas", "website": "chemplas.co.uk", "mobile_score": 41, "teardown_at": "2026-10-05T10:00:00Z",
               "teardown": {"checks": {}}}
        out = cp.diagnose(self.slug, row, cp.sheet_matches(self.dir, self.slug, SECRET), cp.log_row(self.dir, "chemplas.co.uk"), 2026)
        self.assertIn("  Nothing - the page has its website, score and findings.", out)

    def test_dashboard_has_it_but_the_page_does_not(self):
        self.log("ok", "41")
        row = {"business_name": "Chemplas", "website": "chemplas.co.uk", "mobile_score": 41, "teardown_at": "2026-10-05T10:00:00Z",
               "teardown": {"checks": {}}}
        live = cp.live_page(self.slug, lambda url: "<h1>Prepared for Chemplas</h1>")
        out = "\n".join(cp.diagnose(self.slug, row, cp.sheet_matches(self.dir, self.slug, SECRET),
                                    cp.log_row(self.dir, "chemplas.co.uk"), 2026, live))
        self.assertIn("Live page: score NOT shown", out)
        self.assertIn("the website is reading a different dashboard", out)
        self.assertEqual(cp.live_page(self.slug, lambda url: '<span>/ 100 on mobile</span><section id="findings">'),
                         {"score": True, "findings": True})

    def test_no_page_on_the_dashboard(self):
        out = "\n".join(cp.diagnose(self.slug, None, [], None, 2026))
        self.assertIn("no page with this link", out)


class LastRun(unittest.TestCase):
    def test_keeps_how_it_went_and_this_firm(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "last-run-log.txt").write_text("\n".join([
                "2026-10-06 09:00 > Run the whole list", "> python push_prospects.py --sheet x", "",
                "Speed checking 10 sites, 4 at a time ...", "[1/10] other.co.uk: 55/100, 1 issue",
                "[2/10] churchillroofingsouth.co.uk: 33/100, 2 issues", "Traceback (most recent call last):",
                "urllib.error.HTTPError: HTTP Error 500", "Some chatter", "Done."]), encoding="utf-8")
            out = cp.last_run(Path(d), "churchillroofingsouth.co.uk", "Churchill Roofing South")
        text = "\n".join(out)
        self.assertIn("Last run: 2026-10-06 09:00 > Run the whole list", text)
        self.assertIn("churchillroofingsouth.co.uk: 33/100", text)
        self.assertIn("HTTPError: HTTP Error 500", text)
        self.assertNotIn("other.co.uk", text)
        self.assertNotIn("Some chatter", text)

    def test_no_saved_log(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("no saved log yet", cp.last_run(Path(d), "x.co.uk", "X")[0])


class Panel(unittest.TestCase):
    def test_check_preview_action(self):
        import control_panel as panel

        make, err = panel.build_steps({"action": "check_preview", "preview_link": "https://www.scalardigital.co.uk/for/chemplas-a76f9c?src=email"}, {})
        self.assertEqual((err, list(make(None))), ("", [(panel.CHECK_PREVIEW, ["--link", "chemplas-a76f9c"])]))
        self.assertIn("Paste a preview link", panel.build_steps({"action": "check_preview", "preview_link": "; rm"}, {})[1])


if __name__ == "__main__":
    unittest.main()
