"""nudges: who gets a morning nudge, the draft, and the bot sending it only on your tap.

Run: python -m unittest scripts/test_nudges.py
"""

import csv
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import nudges
import telegram_bot
from test_telegram_bot import CHAT, fake_panel

NOW = datetime(2026, 10, 7, 9, 0, tzinfo=timezone.utc)


def viewer(name, views=3, last="2026-10-06T19:00:00Z", calls=0, heat=5.0):
    site = f"{name.lower()}.co.uk"
    return {"key": f"k-{name}", "sheet": "list.xlsx", "business": name, "website": site, "email": f"info@{site}",
            "contact": "Sam Kerr", "phone": "01483 111222", "views": views, "seconds": 80, "last_viewed": last,
            "calls": calls, "heat": heat, "preview": f"https://x/for/{name.lower()}?src=dashboard"}


class Setup(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        with (self.d / "emails-sent.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["email", "business", "preview_url", "sent", "followup_sent", "message_id", "subject"])
            for name, sent, fu in [("Hot", "2026-10-01", ""), ("Once", "2026-10-01", ""), ("Stale", "2026-09-01", ""),
                                   ("Rung", "2026-10-01", ""), ("Replied", "2026-10-01", ""), ("Fresh", "2026-10-06", ""),
                                   ("Followed", "2026-09-20", "2026-10-06"), ("Warm", "2026-10-02", "")]:
                w.writerow([f"info@{name.lower()}.co.uk", name, f"https://x/for/{name.lower()}?src=email", sent, fu,
                            f"<{name}@m>", f"{name}'s website"])
        self.data = {"viewing": [viewer("Hot", heat=9), viewer("Once", views=1), viewer("Stale", last="2026-09-20T10:00:00Z"),
                                 viewer("Rung", calls=1), viewer("Replied"), viewer("Fresh"), viewer("Followed"),
                                 viewer("Unsent"), viewer("Warm", heat=2)],
                     "replied": [{"website": "replied.co.uk"}]}


class Candidates(Setup):
    def test_only_repeat_recent_viewers_nobody_has_rung_or_heard_from(self):
        got = nudges.candidates(self.data, self.d, NOW)
        self.assertEqual([i["business"] for i in got], ["Hot", "Warm"])
        self.assertEqual(got[0]["sent"]["message_id"], "<Hot@m>")

    def test_once_ever(self):
        nudges.mark(self.d, "hot.co.uk", "Hot", NOW.date())
        self.assertEqual([i["business"] for i in nudges.candidates(self.data, self.d, NOW)], ["Warm"])

    def test_draft_threads_into_their_email(self):
        d = nudges.draft(nudges.candidates(self.data, self.d, NOW)[0], "Jack Wilkins")
        self.assertEqual((d["subject"], d["message_id"]), ("Hot's website", "<Hot@m>"))
        self.assertTrue(d["text"].startswith("Hi Sam,\n\n"))
        self.assertIn("https://x/for/hot?src=email", d["text"])
        self.assertIn("Jack Wilkins", d["text"])

    def test_due_once_a_day_from_half_eight(self):
        self.assertFalse(nudges.due(datetime(2026, 10, 7, 8, 29), ""))
        self.assertTrue(nudges.due(datetime(2026, 10, 7, 8, 30), "2026-10-06"))
        self.assertFalse(nudges.due(datetime(2026, 10, 7, 14, 0), "2026-10-07"))


class Morning(Setup):
    def test_texts_each_with_a_draft_and_sends_only_on_tap(self):
        panel, calls = fake_panel(self.d)
        panel.load_settings = lambda: {"PROSPECTS_API_SECRET": "x" * 40, "MAIL_FROM_NAME": "Jack"}
        sent = []
        bot = telegram_bot.Bot(panel, "tok", CHAT, http=lambda m, p, timeout=30: sent.append((m, p)) or {})
        bot._all_calls = lambda: self.data
        bot.chase_quotes = lambda: None
        orig = nudges.candidates
        nudges.candidates = lambda data, outreach: orig(data, outreach, NOW)
        try:
            bot.morning()
        finally:
            nudges.candidates = orig
        texts = [p["text"] for m, p in sent if m == "sendMessage"]
        self.assertIn("Hot - Sam Kerr opened their preview 3 times", texts[0])
        self.assertIn("ring 01483 111222", texts[0])
        self.assertTrue(texts[1].startswith("To info@hot.co.uk:\n\nHi Sam,"))
        self.assertEqual(calls, [])  # nothing goes out by itself
        self.assertEqual(nudges.nudged(self.d), {"hot.co.uk", "warm.co.uk"})
        button = next(b["callback_data"] for m, p in sent if "reply_markup" in p
                      for row in p["reply_markup"]["inline_keyboard"] for b in row if b["callback_data"].startswith("sendreply:"))
        bot.handle({"callback_query": {"id": "q", "data": button, "message": {"chat": {"id": int(CHAT)}}}})
        kind, body = calls[0]
        self.assertEqual((kind, body["to"], body["message_id"], body["subject"]), ("send", "info@hot.co.uk", "<Hot@m>", "Hot's website"))

    def test_runs_once_a_day(self):
        panel, _ = fake_panel(self.d)
        bot = telegram_bot.Bot(panel, "tok", CHAT, http=lambda m, p, timeout=30: {})
        bot.morning = lambda: None
        self.assertFalse(bot.maybe_morning(datetime(2026, 10, 7, 7, 0)))
        self.assertTrue(bot.maybe_morning(datetime(2026, 10, 7, 8, 45)))
        self.assertFalse(bot.maybe_morning(datetime(2026, 10, 7, 12, 0)))
        self.assertTrue(bot.maybe_morning(datetime(2026, 10, 8, 9, 0)))


if __name__ == "__main__":
    unittest.main()
