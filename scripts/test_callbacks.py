"""Offline tests for what a reply is asking for, and call-backs that come back on the day."""

import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

import openpyxl

import calls
import overrides
import reply_scanner as rs
from push_prospects import make_slug

SECRET = "x" * 40
TODAY = date(2026, 10, 1)


class Intent(unittest.TestCase):
    def test_reads_what_they_want(self):
        cases = {
            "How much would something like that cost?": "price",
            "Can you give me a ring on 07700 900123": "call",
            "Sounds good, tell me more about how it works": "info",
            "Not right now, maybe in the spring - how much would it be roughly?": "later",  # later wins
            "We're too busy at the moment, try me in a few months": "later",
            "Thanks for this": "",
        }
        for text, want in cases.items():
            self.assertEqual(rs.intent(text), want, text)


class Due(unittest.TestCase):
    def test_short_forms_and_dates(self):
        self.assertEqual(calls.parse_due("3d", TODAY), date(2026, 10, 4))
        self.assertEqual(calls.parse_due("2w", TODAY), date(2026, 10, 15))
        self.assertEqual(calls.parse_due("3m", TODAY), date(2026, 12, 30))
        self.assertEqual(calls.parse_due("tomorrow", TODAY), date(2026, 10, 2))
        self.assertEqual(calls.parse_due("2026-11-03", TODAY), date(2026, 11, 3))
        self.assertEqual(calls.parse_due("3/11/2026", TODAY), date(2026, 11, 3))

    def test_nonsense_and_the_past_are_refused(self):
        for bad in ("soon", "", "2026-09-01", "2029-01-01", "999d"):
            self.assertIsNone(calls.parse_due(bad, TODAY), bad)


class Callbacks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Outreach"
        ws.append(["Business", "Website", "Status", "Phone", "Contact name", "Email"])
        ws.append(["Hot Roofing", "hot.co.uk", "New", "01483 111111", "Amy", "amy@hot.co.uk"])
        ws.append(["Later Roofing", "later.co.uk", "New", "01483 222222", "Bob", "bob@later.co.uk"])
        wb.save(self.d / "s.xlsx")
        self.later_key = overrides.row_key({"Business": "Later Roofing"})
        self.hot_key = overrides.row_key({"Business": "Hot Roofing"})

    def tearDown(self):
        self.tmp.cleanup()

    def out(self, when, act=None):
        return calls.call_list(self.d, "s.xlsx", SECRET, "https://site", act or {}, when)

    def test_comes_back_on_the_day_not_before(self):
        calls.add_callback(self.d, "s.xlsx", self.later_key, "Later Roofing", date(2026, 10, 5), "spring job")
        self.assertEqual(self.out(datetime(2026, 10, 4, 9, tzinfo=timezone.utc))["callbacks"], [])
        due = self.out(datetime(2026, 10, 7, 9, tzinfo=timezone.utc))["callbacks"]
        self.assertEqual([(c["business"], c["phone"], c["overdue"], c["note"]) for c in due], [("Later Roofing", "01483 222222", 2, "spring job")])
        self.assertEqual(due[0]["sheet"], "s.xlsx")

    def test_a_new_date_replaces_the_old_and_any_outcome_closes_it(self):
        calls.add_callback(self.d, "s.xlsx", self.later_key, "Later Roofing", date(2026, 10, 2))
        calls.add_callback(self.d, "s.xlsx", self.later_key, "Later Roofing", date(2026, 10, 20))
        self.assertEqual(calls.due_callbacks(self.d, date(2026, 10, 10)), [])
        self.assertEqual(len(calls.due_callbacks(self.d, date(2026, 10, 20))), 1)
        calls.complete_callbacks(self.d, self.later_key)
        self.assertEqual(calls.due_callbacks(self.d, date(2026, 10, 30)), [])

    def test_not_listed_twice(self):
        calls.add_callback(self.d, "s.xlsx", self.hot_key, "Hot Roofing", date(2026, 10, 1))
        act = {make_slug("Hot Roofing", "hot.co.uk", SECRET): {"view_count": 4, "last_viewed_at": "2026-10-01T08:00:00Z"}}
        out = self.out(datetime(2026, 10, 1, 9, tzinfo=timezone.utc), act)
        self.assertEqual([c["business"] for c in out["callbacks"]], ["Hot Roofing"])
        self.assertEqual(out["callbacks"][0]["views"], 4)
        self.assertEqual(out["viewing"], [])

    def test_panel_call_back_needs_a_sensible_date(self):
        import control_panel as cp
        from unittest import mock

        with mock.patch.object(cp, "OUTREACH", self.d), mock.patch.object(cp, "sheet_path", lambda s: self.d / s):
            body = {"sheet": "s.xlsx", "key": self.later_key, "business": "Later Roofing", "outcome": "Call back"}
            self.assertEqual(cp.call_action({**body, "due": "whenever"})[1], 400)
            out, code = cp.call_action({**body, "due": "2w"})
            self.assertEqual(code, 200)
            self.assertIn("call back on", out["message"])
            self.assertEqual(len(calls._callback_rows(self.d)), 1)
            cp.call_action({**body, "outcome": "Interested"})
            self.assertTrue(calls._callback_rows(self.d)[0]["done"])


class RepliedCards(unittest.TestCase):
    def test_a_reply_shows_its_intent_and_preview_views(self):
        import csv

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Outreach"
            ws.append(["Business", "Website", "Status", "Phone"])
            ws.append(["Kerr Roofing", "kerr.co.uk", "New", "01483 111222"])
            wb.save(d / "s.xlsx")
            with (d / "replies.csv").open("w", newline="", encoding="utf-8") as f:  # an older file, no intent column
                w = csv.writer(f)
                w.writerow(["message_id", "date", "from", "business", "website", "kind", "subject", "snippet", "handled"])
                w.writerow(["<1@x>", "2026-10-01T09:00+00:00", "bill@kerr.co.uk", "Kerr Roofing", "kerr.co.uk", "interested", "Re", "How much is it?", ""])
            act = {make_slug("Kerr Roofing", "kerr.co.uk", SECRET): {"view_count": 2, "last_viewed_at": "2026-10-01T08:00:00Z"}}
            r = calls.call_list(d, "s.xlsx", SECRET, "https://site", act)["replied"][0]
            self.assertEqual((r["intent"], r["views"]), ("price", 2))
            self.assertTrue(r["preview"].startswith("https://site/for/"))


if __name__ == "__main__":
    unittest.main()
