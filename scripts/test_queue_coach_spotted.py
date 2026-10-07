"""▶️ Next call, the weekly coach and photo-to-prospect - offline, Claude and Telegram faked.

Run: python -m unittest scripts/test_queue_coach_spotted.py
"""

import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import openpyxl

import coach
import spotted
import telegram_bot
from test_telegram_bot import CHAT, fake_panel


def firm(n, views=3):
    return {"key": f"name:firm {n}", "sheet": "list.xlsx", "business": f"Firm {n}", "website": f"firm{n}.co.uk",
            "phone": "01483 111222", "views": views, "seconds": 40, "preview": f"https://x/for/firm-{n}?src=dashboard"}


class Bot(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.panel, self.calls = fake_panel(self.d)
        self.sent = []
        self.bot = telegram_bot.Bot(self.panel, "tok", CHAT, http=lambda m, p, timeout=30: self.sent.append((m, p)) or {})

    def texts(self):
        return [p["text"] for m, p in self.sent if m == "sendMessage"]

    def tap(self, data):
        self.bot.handle({"callback_query": {"id": "q", "data": data, "message": {"chat": {"id": int(CHAT)}}}})

    def last_buttons(self):
        p = [p for m, p in self.sent if m == "sendMessage" and "reply_markup" in p and "inline_keyboard" in p["reply_markup"]][-1]
        return [b.get("callback_data") for row in p["reply_markup"]["inline_keyboard"] for b in row]


class Queue(Bot):
    def test_one_at_a_time_and_the_next_after_an_outcome(self):
        self.bot._all_calls = lambda: {"callbacks": [], "viewing": [firm(1), firm(2)], "replied": []}
        self.bot.handle({"message": {"chat": {"id": int(CHAT)}, "text": "▶️ Next call"}})
        self.assertIn("2 to ring", self.texts()[0])
        self.assertIn("📞 Firm 1", self.texts()[1])
        first = self.last_buttons()[0]  # No answer
        self.tap(first)
        self.assertEqual(self.calls[-1][1]["outcome"], "No answer")
        self.assertTrue(any("📞 Firm 2" in t for t in self.texts()))
        self.tap(self.last_buttons()[2])  # Interested on the last one
        self.assertEqual(self.texts()[-1], "That's everyone. ✅")

    def test_skip_and_stop(self):
        self.bot._all_calls = lambda: {"callbacks": [], "viewing": [firm(1), firm(2), firm(3)], "replied": []}
        self.bot.next_call()
        skip = next(b for b in self.last_buttons() if b.startswith("skip:"))
        self.tap(skip)
        self.assertIn("📞 Firm 2", self.texts()[-1])
        self.tap(next(b for b in self.last_buttons() if b.startswith("endq:")))
        self.assertIn("Calling stopped", self.texts()[-1])
        self.assertEqual(self.bot.queue, [])


class Coach(unittest.TestCase):
    def test_sends_counts_only_and_returns_three_changes(self):
        d = Path(tempfile.mkdtemp())
        import email_batches as eb

        with (d / eb.SENT).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=eb.SENT_FIELDS)
            w.writeheader()
            w.writerow({"email": "secret@kerr.co.uk", "business": "Kerr Roofing", "sent": "2026-10-01"})
        seen = {}

        def fake(path, key, payload, timeout=45):
            seen.update(payload)
            return {"content": [{"type": "text", "text": "1. Send more.\nWhy: 1 send."}]}

        out = coach.advise(d, None, "k", "m", date(2026, 10, 7), fake)
        self.assertTrue(out.startswith("🧠 Coach"))
        body = seen["messages"][0]["content"]
        self.assertNotIn("secret@kerr.co.uk", body)
        self.assertNotIn("Kerr Roofing", body)
        self.assertIn("Add ANTHROPIC_API_KEY", coach.advise(d, None, ""))


class Spotted(Bot):
    def test_reads_only_what_is_written(self):
        got = spotted.parse('Sure: {"business": "Kerr Roofing", "phone": "07700 900123", "website": null, "email": "nope", "trade": "roofing"}')
        self.assertEqual(got, {"business": "Kerr Roofing", "phone": "07700 900123", "website": "", "email": "", "trade": "roofing", "town": ""})
        self.assertEqual(spotted.parse("no json")["business"], "")

    def test_photo_is_sent_to_claude_as_an_image(self):
        seen = {}

        def fake(path, key, payload, timeout=45):
            seen.update(payload)
            return {"content": [{"type": "text", "text": json.dumps({"business": "Oak Lofts", "website": "oaklofts.co.uk"})}]}

        lead = spotted.read_photo(b"\xff\xd8jpeg", "k", "m", fake)
        self.assertEqual(lead["website"], "oaklofts.co.uk")
        block = seen["messages"][0]["content"][0]
        self.assertEqual((block["type"], block["source"]["media_type"]), ("image", "image/jpeg"))

    def test_no_website_goes_on_the_no_website_tab(self):
        self.panel.load_settings = lambda: {"PROSPECTS_API_SECRET": "x" * 40, "ANTHROPIC_API_KEY": "k"}
        old_dl, old_read = spotted.download, spotted.read_photo
        spotted.download = lambda token, file_id, http: b"img"
        spotted.read_photo = lambda image, key, model="": {"business": "Van Man Roofing", "phone": "07700 900123", "website": "",
                                                           "email": "", "trade": "roofing", "town": "Woking"}
        try:
            self.bot.handle({"message": {"chat": {"id": int(CHAT)}, "photo": [{"file_id": "a", "file_size": 10}, {"file_id": "b", "file_size": 99}]}})
            self.bot.handle({"message": {"chat": {"id": int(CHAT)}, "photo": [{"file_id": "a", "file_size": 10}]}})
        finally:
            spotted.download, spotted.read_photo = old_dl, old_read
        self.assertIn("added to the No website tab", self.texts()[1])
        self.assertIn("Ring 07700 900123", self.texts()[1])
        self.assertIn("already on the No website tab", self.texts()[3])
        rows = list(openpyxl.load_workbook(self.d / spotted.SHEET)["No website"].iter_rows(values_only=True))
        self.assertEqual(len(rows), 2)

    def test_with_a_website_the_list_is_run(self):
        self.panel.load_settings = lambda: {"PROSPECTS_API_SECRET": "x" * 40, "ANTHROPIC_API_KEY": "k"}
        self.panel.sheets = lambda: [spotted.SHEET]
        started = []
        self.bot.start = lambda action, extra=None, then=None: started.append((action, extra, then))
        old_dl, old_read = spotted.download, spotted.read_photo
        spotted.download = lambda token, file_id, http: b"img"
        spotted.read_photo = lambda image, key, model="": {"business": "Oak Lofts", "phone": "", "website": "www.oaklofts.co.uk",
                                                           "email": "", "trade": "", "town": ""}
        try:
            self.bot.handle({"message": {"chat": {"id": int(CHAT)}, "photo": [{"file_id": "a"}]}})
        finally:
            spotted.download, spotted.read_photo = old_dl, old_read
        self.assertIn("Oak Lofts added to spotted.xlsx", self.texts()[1])
        self.assertEqual(started[0][:2], ("all", {"sheet": spotted.SHEET}))
        self.assertIn("/for/oak-lofts-", started[0][2][0])


if __name__ == "__main__":
    unittest.main()
