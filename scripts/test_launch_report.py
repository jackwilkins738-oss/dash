"""launch_report.py: the before comes from the first check, the after is the median of today's runs, nothing is flattered."""

import csv
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock

import launch_report as lr
from test_pipeline_rules import make_sheet

BEFORE = {"mobile_score": 38, "lcp_s": 6.1, "trade": "Roofing", "area": "Guildford", "teardown_at": "2026-06-02T10:00:00Z",
          "teardown": {"v": 1, "checks": {"tapToCall": False, "contactForm": False, "https": True}, "imageSavingsKb": 2100,
                       "pageWeightKb": 4800, "seoScore": 70, "copyrightYear": 2019}}
AFTER = {"v": 1, "checks": {"tapToCall": True, "contactForm": True, "https": True}, "imageSavingsKb": 600,
         "pageWeightKb": 420, "seoScore": 100, "_mobile_score": 96, "_lcp_s": 1.1, "_runs": 3}


class LaunchReport(unittest.TestCase):
    def test_compare_lists_what_was_fixed_and_what_still_isnt(self):
        c = lr.compare(BEFORE, AFTER, 2026, 2026)
        self.assertEqual(c["score"], (38, 96))
        self.assertEqual(c["lcp"], (6.1, 1.1))
        self.assertIn("your phone number isn't tap-to-call on a mobile", c["fixed"])
        self.assertIn("your website footer still says © 2019", c["fixed"])
        # Images still 600 KB heavier than they could be: the same problem, smaller - not claimed as fixed.
        self.assertTrue(any("images" in i for i in c["still"]))
        self.assertFalse(any("images" in i for i in c["fixed"]))

    def test_after_is_the_median_of_three_runs(self):
        runs = iter([{"_mobile_score": 99, "_lcp_s": 0.9}, {"_mobile_score": 88, "_lcp_s": 1.6}])
        with mock.patch("site_teardown.teardown", return_value={"v": 1, "checks": {}, "_mobile_score": 93, "_lcp_s": 1.2}), \
             mock.patch("site_teardown.run_pagespeed", side_effect=lambda *a, **k: next(runs)):
            after = lr.measure_after("kerr.co.uk", "key")
        self.assertEqual((after["_mobile_score"], after["_lcp_s"], after["_runs"]), (93, 1.2, 3))

    def test_report_is_escaped_and_honest(self):
        c = lr.compare(BEFORE, AFTER, 2026, 2026)
        page = lr.report_html("Kerr <Roofing>", "kerr.co.uk", "kerr.co.uk", c, "02 June 2026", 3, date(2026, 10, 20))
        self.assertIn("Kerr &lt;Roofing&gt;", page)
        self.assertNotIn("<Roofing>", page)
        self.assertIn("Speed score 38 &rarr; 96, showing in 1.1s instead of 6.1s", page)
        self.assertIn("Still worth doing", page)
        self.assertIn("the middle of 3 runs", page)

    def test_end_to_end_writes_the_report_and_one_case_study_line_per_site(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            make_sheet(out / "list.xlsx", [{"Business": "Kerr Roofing", "Website": "https://www.kerr.co.uk/", "Trade": "Roofing"}])
            env = {"PAGESPEED_API_KEY": "k", "PROSPECTS_API_SECRET": "s" * 40}
            with mock.patch.dict(os.environ, env), mock.patch.object(lr, "outreach_dir", return_value=out), \
                 mock.patch.object(lr, "before_from_dashboard", return_value=BEFORE) as bd, \
                 mock.patch.object(lr, "measure_after", return_value=AFTER), \
                 mock.patch.object(sys, "argv", ["launch_report.py", "--old", "kerr.co.uk"]):
                for _ in range(2):  # a re-run replaces the line rather than adding another
                    with redirect_stdout(io.StringIO()) as printed:
                        lr.main()
            self.assertEqual(bd.call_args.args[1:], ("Kerr Roofing", "kerr.co.uk"))
            self.assertTrue((out / "sites" / "kerr-roofing" / "launch-report.html").exists())
            with (out / "case-studies.csv").open(encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual((rows[0]["score_before"], rows[0]["score_after"], rows[0]["lcp_after"]), ("38", "96", "1.1s"))
            self.assertIn("READY: sites/kerr-roofing/launch-report.html", printed.getvalue().replace(os.sep, "/"))

    def test_no_earlier_measurement_is_refused_not_invented(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            make_sheet(out / "list.xlsx", [{"Business": "Kerr Roofing", "Website": "kerr.co.uk"}])
            with mock.patch.dict(os.environ, {"PAGESPEED_API_KEY": "k"}), mock.patch.object(lr, "outreach_dir", return_value=out), \
                 mock.patch.object(lr, "before_from_dashboard", return_value=None), \
                 mock.patch.object(sys, "argv", ["launch_report.py", "--old", "kerr.co.uk"]):
                with self.assertRaises(SystemExit) as e:
                    lr.main()
            self.assertIn("No earlier measurement", str(e.exception))


if __name__ == "__main__":
    unittest.main()
