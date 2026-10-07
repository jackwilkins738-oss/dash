"""quote_chase: which open quotes get chased, and the bot offering the follow-up - offline.

Run: python -m unittest scripts/test_quote_chase.py
"""

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import quote_chase as qc
import telegram_bot
from test_telegram_bot import CHAT, fake_panel

NOW = datetime(2026, 10, 7, 9, 0, tzinfo=timezone.utc)


def quote(n, sent="2026-10-04T09:00:00Z", views=2, slug="kerr-roofing-4a7bc2", business="Kerr Roofing"):
    return {"slug": slug, "business_name": business, "quote_number": f"SD-{n}", "total_pence": 250000, "sent_at": sent,
            "view_count": views, "last_viewed_at": "2026-10-05T10:00:00Z", "quote_url": f"https://admin/quote/{n}/tok"}


class Due(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_opened_two_days_ago_and_never_chased(self):
        quotes = [quote(1, views=2), quote(2, views=0), quote(3, sent="2026-10-06T09:00:00Z"), quote(4, views=5)]
        self.assertEqual([q["quote_number"] for q in qc.due(quotes, self.d, NOW)], ["SD-4", "SD-1"])
        qc.mark(self.d, quotes[3], NOW.date())
        self.assertEqual([q["quote_number"] for q in qc.due(quotes, self.d, NOW)], ["SD-1"])

    def test_fetch_never_fails(self):
        def boom(url):
            raise OSError("offline")
        self.assertEqual(qc.fetch("https://api", "s", "t", boom), [])
        self.assertEqual(qc.fetch("https://api", "s", "t", lambda url: {"quotes": [quote(1)]})[0]["quote_number"], "SD-1")

    def test_draft_and_money(self):
        text = qc.draft(quote(1), {"contact": "Sam Kerr"}, "Jack Wilkins")
        self.assertTrue(text.startswith("Hi Sam,"))
        self.assertIn("https://admin/quote/1/tok", text)
        self.assertEqual(qc.pounds(250000), "£2,500")


class Bot(unittest.TestCase):
    def test_texts_the_chase_and_sends_only_on_tap(self):
        d = Path(tempfile.mkdtemp())
        panel, calls = fake_panel(d)
        panel.load_settings = lambda: {"PROSPECTS_API_SECRET": "x" * 40, "MAIL_FROM_NAME": "Jack"}
        sent = []
        bot = telegram_bot.Bot(panel, "tok", CHAT, http=lambda m, p, timeout=30: sent.append((m, p)) or {})
        bot.find_by_slug = lambda slug: {"key": "name:kerr roofing", "sheet": "list.xlsx", "business": "Kerr Roofing",
                                         "website": "kerr.co.uk", "email": "info@kerr.co.uk", "phone": "01483 111222", "contact": "Sam"}
        old_fetch, old_due = qc.fetch, qc.due
        qc.fetch = lambda api, secret, tenant: [quote(1)]
        qc.due = lambda quotes, outreach: old_due(quotes, outreach, NOW)
        try:
            bot.chase_quotes()
        finally:
            qc.fetch, qc.due = old_fetch, old_due
        texts = [p["text"] for m, p in sent if m == "sendMessage"]
        self.assertIn("Kerr Roofing opened their £2,500 quote 2 time(s)", texts[0])
        self.assertIn("Ring 01483 111222", texts[0])
        self.assertTrue(texts[1].startswith("To info@kerr.co.uk:\n\nHi Sam,"))
        self.assertEqual(calls, [])
        self.assertEqual(qc.chased(d), {"SD-1"})
        button = next(b["callback_data"] for m, p in sent if "reply_markup" in p
                      for row in p["reply_markup"]["inline_keyboard"] for b in row if b.get("callback_data", "").startswith("sendreply:"))
        bot.handle({"callback_query": {"id": "q", "data": button, "message": {"chat": {"id": int(CHAT)}}}})
        self.assertEqual((calls[0][0], calls[0][1]["to"]), ("send", "info@kerr.co.uk"))


if __name__ == "__main__":
    unittest.main()
