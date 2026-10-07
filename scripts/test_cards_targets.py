"""Canvass cards, weekly targets and the best-time hint - offline.

Run: python -m unittest scripts/test_cards_targets.py
"""

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

import openpyxl

import call_script
import cards
import daily
from push_prospects import make_slug

SECRET = "x" * 40


class Cards(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Outreach"
        ws.append(["Business", "Website", "Area", "Status"])
        ws.append(["Fast Roofing", "fast.co.uk", "Guildford", ""])
        ws.append(["Slow Roofing", "slow.co.uk", "Guildford", ""])
        ws.append(["Woking Roofs", "woking.co.uk", "Woking", ""])
        ws.append(["Said No Roofing", "no.co.uk", "Guildford", ""])
        wb.save(self.d / "list.xlsx")
        with (self.d / "teardown-log.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["website", "checked_at", "result", "mobile_score"])
            w.writerows([["fast.co.uk", "", "ok", "91"], ["slow.co.uk", "", "ok", "22"]])
        with (self.d / "do-not-contact.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["kind", "value", "reason"])
            w.writerow(["website", "no.co.uk", "not interested"])

    def test_picks_the_town_slowest_first(self):
        firms = cards.pick(self.d, "list.xlsx", "guildford", SECRET)
        self.assertEqual([f["business"] for f in firms], ["Slow Roofing", "Fast Roofing"])
        self.assertEqual(firms[0]["slug"], make_slug("Slow Roofing", "slow.co.uk", SECRET))

    def test_four_to_a_page_with_their_own_code(self):
        firms = cards.pick(self.d, "list.xlsx", "", SECRET)
        page = cards.render(firms * 2, "https://www.scalardigital.co.uk", {"name": "Jack", "phone": "07401 696272"})
        self.assertEqual(page.count('class="card"'), 6)
        self.assertEqual(page.count('class="page"'), 2)
        self.assertIn("scalardigital.co.uk/for/" + firms[0]["slug"], page)

    def test_panel_action(self):
        from unittest import mock

        import control_panel as cp

        with mock.patch.object(cp, "sheet_path", lambda s: self.d / s):
            make, err = cp.build_steps({"action": "cards", "sheet": "list.xlsx", "cards_area": "Guildford"}, {})
            self.assertEqual(list(make(None)), [(cp.CARDS, ["--sheet", "list.xlsx", "--area", "Guildford"])])
            self.assertIn("Area", cp.build_steps({"action": "cards", "sheet": "list.xlsx", "cards_area": "<b>"}, {})[1])


class Targets(unittest.TestCase):
    def test_counts_this_week_against_the_targets(self):
        d = Path(tempfile.mkdtemp())
        import email_batches as eb

        with (d / eb.SENT).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=eb.SENT_FIELDS)
            w.writeheader()
            w.writerow({"email": "a@x", "sent": "2026-10-05"})
            w.writerow({"email": "b@x", "sent": "2026-09-30", "followup_sent": "2026-10-06"})
            w.writerow({"email": "c@x", "sent": "2026-10-02"})  # last week
        with (d / "calls.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["key", "sheet", "business", "outcome", "note", "at"])
            w.writerows([["k", "s", "A", "No answer", "", "2026-10-06T09:00"], ["k", "s", "A", "Replied to them", "", "2026-10-06T09:00"]])
        daily.log_video(d, "kerr-1", date(2026, 10, 7))
        self.assertEqual(daily.done_this_week(d, date(2026, 10, 7)), {"emails": 2, "calls": 1, "videos": 1, "quotes": 0})
        self.assertEqual(daily.progress(d, date(2026, 10, 7), "emails 2, calls 10"), "🎯 This week so far: emails 2/2 ✅ · calls 1/10")
        self.assertEqual(daily.targets(""), {"emails": 100, "calls": 40, "videos": 5, "quotes": 2})


class BestTime(unittest.TestCase):
    def test_from_when_they_looked(self):
        self.assertIn("evenings suit them", call_script.best_time({"first_viewed": "2026-10-06T18:10:00Z", "last_viewed": "2026-10-07T17:40:00Z"}))
        self.assertIn("7am", call_script.best_time({"last_viewed": "2026-12-07T07:40:00Z"}))  # GMT in winter
        self.assertEqual(call_script.best_time({}), "")
        lines = call_script.script({"business": "K", "website": "k.co.uk", "last_viewed": "2026-10-07T11:00:00Z"}, Path(tempfile.mkdtemp()))
        self.assertTrue(lines[1].startswith("When: opened it around 12pm"))


if __name__ == "__main__":
    unittest.main()
