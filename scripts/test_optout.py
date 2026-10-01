"""Offline tests: "not for us" on a preview page stops every email and call to that firm."""

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

import openpyxl

import calls
import email_batches as eb
from push_prospects import make_slug

SECRET = "x" * 40


class OptOut(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        with (self.d / "mailmeteor-list.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["business", "email", "preview_url"])
            w.writerow(["Gone Roofing", "info@gone.co.uk", "https://s/for/gone-roofing-aaa111"])
            w.writerow(["Keen Roofing", "info@keen.co.uk", "https://s/for/keen-roofing-bbb222"])
        self.views = {"gone-roofing-aaa111": {"status": "lost"}, "keen-roofing-bbb222": {"status": "viewed"}}

    def tearDown(self):
        self.tmp.cleanup()

    def test_lost_firms_never_make_the_next_batch(self):
        self.assertEqual(eb.block_optouts(self.d, self.views), 2)  # their email and name
        self.assertEqual(eb.block_optouts(self.d, self.views), 0)  # once is enough
        path, notes = eb.make_batch(self.d, 20, check=lambda u: None, today=date(2026, 10, 1))
        self.assertEqual([r["business"] for r in csv.DictReader(path.open(encoding="utf-8"))], ["Keen Roofing"])

    def test_nothing_to_do_without_the_dashboard(self):
        self.assertEqual(eb.block_optouts(self.d, None), 0)
        self.assertFalse((self.d / "do-not-contact.csv").exists())

    def test_off_the_call_list_too(self):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Outreach"
        ws.append(["Business", "Website", "Status", "Phone"])
        ws.append(["Gone Roofing", "gone.co.uk", "New", "01483 111111"])
        ws.append(["Keen Roofing", "keen.co.uk", "New", "01483 222222"])
        wb.save(self.d / "s.xlsx")
        act = {make_slug("Gone Roofing", "gone.co.uk", SECRET): {"status": "lost", "view_count": 3, "last_viewed_at": "2026-10-01T08:00:00Z"},
               make_slug("Keen Roofing", "keen.co.uk", SECRET): {"status": "viewed", "view_count": 1, "last_viewed_at": "2026-10-01T08:00:00Z"}}
        out = calls.call_list(self.d, "s.xlsx", SECRET, "https://site", act)
        self.assertEqual([i["business"] for i in out["viewing"]], ["Keen Roofing"])
        with (self.d / "do-not-contact.csv").open(encoding="utf-8") as f:
            self.assertIn("gone.co.uk", [r["value"] for r in csv.DictReader(f)])


if __name__ == "__main__":
    unittest.main()
