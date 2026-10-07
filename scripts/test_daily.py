"""daily: the 8:30 plan, Sunday's week-on-week, referral asks and the objection sheet - offline.

Run: python -m unittest scripts/test_daily.py
"""

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

import daily
import email_batches as eb
import objections
import telegram_bot
from test_telegram_bot import CHAT, fake_panel


def write(path, header, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


class Plan(unittest.TestCase):
    def test_only_what_is_waiting(self):
        data = {"callbacks": [{}], "viewing": [{"views": 3}, {"views": 1}], "replied": []}
        text = daily.plan(data, 2, 40)
        self.assertIn("1 call-back(s) due", text)
        self.assertIn("1 firm(s) opened their preview 2+ times", text)
        self.assertIn("2 quote(s) open", text)
        self.assertNotIn("repl", text)
        self.assertIn("Nothing waiting", daily.plan({}, 0, 0))


class Week(unittest.TestCase):
    def test_this_week_against_last(self):
        d = Path(tempfile.mkdtemp())
        write(d / eb.SENT, eb.SENT_FIELDS, [
            ["a@x.co.uk", "A", "https://s/for/a-1", "b", "2026-10-05"], ["b@x.co.uk", "B", "https://s/for/b-1", "b", "2026-10-06"],
            ["c@x.co.uk", "C", "https://s/for/c-1", "b", "2026-09-29"]])
        write(d / "calls.csv", ["key", "sheet", "business", "outcome", "note", "at"], [
            ["k", "s", "A", "Interested", "", "2026-10-06T10:00"], ["k", "s", "B", "No answer", "", "2026-10-06T11:00"]])
        text = daily.week(d, {"a-1": {"view_count": 2}}, date(2026, 10, 11))
        self.assertIn("sent 2 (+1)", text)
        self.assertIn("opened 1 (+1)", text)
        self.assertIn("calls 2 (+2)", text)
        self.assertIn("conversations 1 (+1)", text)


class Referrals(unittest.TestCase):
    def test_a_month_after_launch_once(self):
        d = Path(tempfile.mkdtemp())
        write(d / "case-studies.csv", ["business", "launched", "new_site", "score_before", "score_after"], [
            ["Kerr Roofing", "2026-09-01", "kerr.co.uk", "31", "96"], ["New One", "2026-10-01", "new.co.uk", "", ""]])
        due = daily.referrals_due(d, date(2026, 10, 7))
        self.assertEqual([r["new_site"] for r in due], ["kerr.co.uk"])
        text = daily.referral_text(due[0], "https://www.scalardigital.co.uk")
        self.assertIn("from 31 to 96", text)
        self.assertIn("https://www.scalardigital.co.uk/refer", text)
        self.assertNotIn("review", text)  # no review link set: no review ask
        self.assertIn("https://g.page/r/x", daily.referral_text(due[0], "https://s", "https://g.page/r/x"))
        daily.mark_asked(d, "kerr.co.uk", date(2026, 10, 7))
        self.assertEqual(daily.referrals_due(d, date(2026, 10, 8)), [])

    def test_bot_sends_the_words(self):
        d = Path(tempfile.mkdtemp())
        write(d / "case-studies.csv", ["business", "launched", "new_site"], [["Kerr Roofing", "2020-01-01", "kerr.co.uk"]])
        panel, _ = fake_panel(d)
        sent = []
        bot = telegram_bot.Bot(panel, "tok", CHAT, http=lambda m, p, timeout=30: sent.append(p["text"]) or {})
        bot.ask_referrals()
        self.assertIn("Kerr Roofing went live a month ago", sent[0])
        self.assertIn("/refer", sent[1])
        bot.ask_referrals()
        self.assertEqual(len(sent), 2)


class Objections(unittest.TestCase):
    def test_typed_in_telegram(self):
        panel, _ = fake_panel(Path(tempfile.mkdtemp()))
        sent = []
        bot = telegram_bot.Bot(panel, "tok", CHAT, http=lambda m, p, timeout=30: sent.append(p["text"]) or {})
        bot.handle({"message": {"chat": {"id": int(CHAT)}, "text": "Objections"}})
        self.assertEqual(sent[0], objections.text())
        self.assertIn("Checkatrade", sent[0])


if __name__ == "__main__":
    unittest.main()
