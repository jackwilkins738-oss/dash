"""The call list: tests and "maybe later" taps kept off it, older clicks kept on it.

Run: python -m unittest scripts/test_call_list_filters.py
"""

import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

import openpyxl

import calls
import overrides
from push_prospects import make_slug

SECRET = "x" * 40
NOW = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)


class Filters(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Outreach"
        ws.append(["Business", "Website", "Status", "Phone", "Email"])
        ws.append(["Old Roofing", "old.co.uk", "New", "01483 111111", "a@old.co.uk"])
        ws.append(["Test Roofing", "test.co.uk", "New", "01483 222222", "b@test.co.uk"])
        ws.append(["Later Roofing", "later.co.uk", "New", "01483 333333", "c@later.co.uk"])
        ws.append(["Done Roofing", "done.co.uk", "New", "01483 444444", "d@done.co.uk"])
        wb.save(self.d / "s.xlsx")
        self.act = {
            make_slug("Old Roofing", "old.co.uk", SECRET): {"view_count": 2, "last_viewed_at": "2026-08-01T10:00:00Z"},
            make_slug("Test Roofing", "test.co.uk", SECRET): {"view_count": 1, "last_viewed_at": "2026-10-12T09:00:00Z"},
            make_slug("Later Roofing", "later.co.uk", SECRET): {"view_count": 1, "last_viewed_at": "2026-10-11T09:00:00Z",
                                                                 "choice": "not_now", "choice_at": "2026-10-11T09:01:00Z",
                                                                 "slug": make_slug("Later Roofing", "later.co.uk", SECRET)},
            make_slug("Done Roofing", "done.co.uk", SECRET): {"view_count": 1, "last_viewed_at": "2026-10-10T09:00:00Z"},
        }

    def tearDown(self):
        self.tmp.cleanup()

    def out(self, act=None, now=NOW):
        return calls.call_list(self.d, "s.xlsx", SECRET, "https://site", act or self.act, now)

    def names(self, section, **kw):
        return [i["business"] for i in self.out(**kw)[section]]

    def test_a_click_from_two_months_ago_is_still_on_the_list(self):
        self.assertIn("Old Roofing", self.names("viewing"))

    def test_hidden_test_stays_off_until_they_look_again(self):
        calls.hide(self.d, overrides.row_key({"Business": "Test Roofing"}), "Test Roofing", "my test")
        self.assertNotIn("Test Roofing", self.names("viewing"))
        act = dict(self.act)
        later = "2099-01-01T00:00:00Z"
        act[make_slug("Test Roofing", "test.co.uk", SECRET)] = {"view_count": 2, "last_viewed_at": later}
        self.assertIn("Test Roofing", self.names("viewing", act=act, now=datetime(2099, 1, 1, 1, tzinfo=timezone.utc)))

    def test_maybe_later_is_not_on_the_list_anywhere(self):
        out = self.out()
        everyone = [i["business"] for s in ("viewing", "replied", "callbacks") for i in out[s]]
        self.assertNotIn("Later Roofing", everyone)
        with (self.d / "replies.csv").open(encoding="utf-8") as f:
            self.assertEqual([r["business"] for r in csv.DictReader(f)], ["Later Roofing"])  # still recorded

    def test_handled_since_they_looked_drops_off_but_no_answer_stays(self):
        key = overrides.row_key({"Business": "Done Roofing"})
        with mock.patch.object(calls, "datetime", wraps=datetime) as dt:
            dt.now.return_value = datetime(2026, 10, 11, 9, tzinfo=timezone.utc)
            calls.log_call(self.d, "s.xlsx", key, "Done Roofing", "No answer")
            self.assertIn("Done Roofing", self.names("viewing"))
            self.assertEqual(self.names("viewing")[-1], "Done Roofing")  # tried since: below the untried
            calls.log_call(self.d, "s.xlsx", key, "Done Roofing", "Replied to them")
        self.assertNotIn("Done Roofing", self.names("viewing"))


class EveryList(unittest.TestCase):
    def test_clicks_from_an_older_list_show_with_their_own_sheet(self):
        import control_panel as cp

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            for name, firm, site in (("new.xlsx", "New Roofing", "new.co.uk"), ("old.xlsx", "Old Roofing", "old.co.uk")):
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "Outreach"
                ws.append(["Business", "Website", "Status", "Phone"])
                ws.append([firm, site, "New", "01483 111111"])
                wb.save(d / name)
            act = {make_slug("Old Roofing", "old.co.uk", SECRET): {"view_count": 1, "last_viewed_at": "2026-09-01T10:00:00Z"}}
            settings = {"PROSPECTS_API_SECRET": SECRET, "DASHBOARD_API_URL": "", "SITE_URL": "", "MAIL_FROM_NAME": ""}
            with mock.patch.object(cp, "OUTREACH", d), mock.patch.object(cp, "load_settings", lambda: settings), \
                 mock.patch.object(calls, "fetch_activity", lambda *a: act):
                out = cp.calls_for("new.xlsx")
        self.assertEqual([(i["business"], i["sheet"]) for i in out["viewing"]], [("Old Roofing", "old.xlsx")])


if __name__ == "__main__":
    unittest.main()
