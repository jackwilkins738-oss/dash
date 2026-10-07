"""call_script, the lost-deal reasons and the WhatsApp after no answer - offline.

Run: python -m unittest scripts/test_call_script.py
"""

import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import call_script
import scorecard
import telegram_bot
from test_telegram_bot import CHAT, ITEM, fake_panel


class Script(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_uses_only_real_numbers(self):
        with (self.d / "teardown-log.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["website", "checked_at", "result", "mobile_score", "lcp_s", "top_issue", "issue_count"])
            w.writerow(["kerr.co.uk", "2026-10-01", "ok", "34", "6.1", "There's no tap-to-call button on a phone.", "3"])
        (self.d / "google-ratings.json").write_text(json.dumps({"kerr.co.uk": {"at": "2026-10-01", "google": {"rating": 4.9, "reviews": 63}}}))
        (self.d / "rivals.json").write_text(json.dumps({"roofer in Guildford": {
            "at": "2026-10-01", "query": "roofer in Guildford", "order": ["top.co.uk", "", "kerr.co.uk"],
            "firms": [{"name": "Top Roofing", "domain": "top.co.uk", "score": 88}, {"name": "Slow", "domain": "slow.co.uk", "score": 20}]}}))
        lines = call_script.script({"business": "Kerr Roofing", "website": "kerr.co.uk", "contact": "Sam Kerr"}, self.d, "Jack Wilkins")
        text = "\n".join(lines)
        self.assertEqual(lines[0], "Ask for Sam Kerr.")
        self.assertIn("Hi Sam, it's Jack from Scalar Digital", text)
        self.assertIn("34/100 on Google's phone test - there's no tap-to-call button on a phone.", text)
        self.assertIn('Top Roofing scores 88 for "roofer in Guildford" (they\'re #3)', text)
        self.assertIn("4.9★ from 63 Google reviews", text)

    def test_nothing_known_means_no_made_up_lines(self):
        text = "\n".join(call_script.script({"business": "Oak Lofts", "website": "oak.co.uk"}, self.d))
        self.assertIn("Ask for the owner.", text)
        self.assertNotIn("Hook", text)
        self.assertNotIn("Rival", text)
        self.assertIn("<your name>", text)


class Reasons(unittest.TestCase):
    def test_scorecard_counts_why_they_said_no(self):
        d = Path(tempfile.mkdtemp())
        with (d / "calls.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["key", "sheet", "business", "outcome", "note", "at"])
            w.writerow(["a", "s", "A", "Not interested", "Reason: Price - wants £500", "2026-10-01T10:00"])
            w.writerow(["b", "s", "B", "Not interested", "Reason: Price", "2026-10-02T10:00"])
            w.writerow(["c", "s", "C", "Not interested", "Reason: Has someone", "2026-10-03T10:00"])
            w.writerow(["d", "s", "D", "Not interested", "", "2026-10-03T10:00"])
        self.assertEqual(scorecard.lost_reasons(d, date(2026, 10, 7)), "Why they said no on the phone (last 90 days): Price 2 · Has someone 1")

    def test_panel_keeps_the_reason_in_the_note(self):
        from unittest import mock

        import control_panel as cp

        d = Path(tempfile.mkdtemp())
        with mock.patch.object(cp, "OUTREACH", d), mock.patch.object(cp, "sheet_path", lambda s: d / s):
            out, status = cp.call_action({"sheet": "list.xlsx", "key": "name:kerr", "business": "Kerr", "outcome": "Not interested",
                                          "reason": "Timing", "note": "busy till spring"})
        self.assertEqual(status, 200, out)
        with (d / "calls.csv").open(encoding="utf-8") as f:
            self.assertEqual(next(csv.DictReader(f))["note"], "Reason: Timing - busy till spring")


class Telegram(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.panel, self.calls = fake_panel(self.d)
        self.panel.load_settings = lambda: {"PROSPECTS_API_SECRET": "x" * 40, "MAIL_FROM_NAME": "Jack Wilkins"}
        self.sent = []
        self.bot = telegram_bot.Bot(self.panel, "tok", CHAT, http=lambda m, p, timeout=30: self.sent.append((m, p)) or {})

    def tap(self, data):
        self.bot.handle({"callback_query": {"id": "q", "data": data, "message": {"chat": {"id": int(CHAT)}}}})

    def test_mobile_numbers(self):
        self.assertEqual(telegram_bot.mobile("07700 900123"), "447700900123")
        self.assertEqual(telegram_bot.mobile("+44 7700 900123"), "447700900123")
        self.assertEqual(telegram_bot.mobile("01483 111222"), "")

    def test_no_answer_offers_whatsapp_for_a_mobile(self):
        sid = self.bot._remember("call", {**ITEM, "phone": "07700 900123", "preview": "https://x/for/kerr?src=dashboard"})
        self.tap(f"o:{sid}:No answer")
        url = self.sent[-1][1]["reply_markup"]["inline_keyboard"][0][0]["url"]
        self.assertTrue(url.startswith("https://wa.me/447700900123?text=Hi+John%2C+it%27s+Jack+from+Scalar+Digital"))
        self.assertIn("src%3Dwhatsapp", url)

    def test_landline_gets_the_text_only(self):
        sid = self.bot._remember("call", {**ITEM, "phone": "01483 111222"})
        self.tap(f"o:{sid}:No answer")
        self.assertNotIn("reply_markup", self.sent[-1][1])
        self.assertIn("isn't a mobile", self.sent[-1][1]["text"])

    def test_not_interested_asks_why(self):
        sid = self.bot._remember("call", ITEM)
        self.tap(f"ni?:{sid}")
        datas = [b["callback_data"] for row in self.sent[-1][1]["reply_markup"]["inline_keyboard"] for b in row]
        self.assertIn(f"ni:{sid}:Price", datas)
        self.tap(f"ni:{sid}:Price")
        self.assertEqual(self.calls[-1][1]["reason"], "Price")


if __name__ == "__main__":
    unittest.main()
