"""AI website check, voice notes, /update, route-ordered cards, out-of-office - offline.

Run: python -m unittest scripts/test_timesavers.py
"""

import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import openpyxl

import cards
import email_batches as eb
import overrides
import site_check
import telegram_bot
import voice
from reply_scanner import back_on
from test_telegram_bot import CHAT, ITEM, fake_panel


def claude(reply):
    return lambda path, key, payload, timeout=45: {"content": [{"type": "text", "text": json.dumps(reply)}]}


class SiteCheck(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        wb = openpyxl.Workbook()
        wb.active.title = "Outreach"
        wb.active.append(["Business", "Website"])
        ws = wb.create_sheet("Check website")
        ws.append(["Business", "Website", "Possible website", "Company number", "Registered address"])
        ws.append(["Kerr Roofing Ltd", "", "kerrroofing.co.uk", "01234567", "1 High St, Guildford GU1 1AA"])
        ws.append(["Oak Lofts Ltd", "", "oaklofts.com", "07654321", "2 Rd, Woking GU21 5AB"])
        ws.append(["Elm Ltd", "", "elm.co.uk", "09999999", "3 Rd, Epsom KT17 1AA"])
        wb.save(self.d / "list.xlsx")

    def test_confirms_rejects_and_leaves_the_unsure(self):
        verdicts = {"kerrroofing.co.uk": "same", "oaklofts.com": "different", "elm.co.uk": "unsure"}

        def request(path, key, payload, timeout=45):
            site = payload["messages"][0]["content"].split('domain="')[1].split('"')[0]
            return {"content": [{"type": "text", "text": json.dumps({"verdict": verdicts[site], "why": "test"})}]}

        lines = []
        tally = site_check.run(self.d, "list.xlsx", "k", "m", fetch=lambda url: ("<p>Roofers in Guildford</p>", url),
                               request=request, out=lines.append)
        self.assertEqual(tally, {"same": 1, "different": 1, "unsure": 1})
        decided = overrides.load(self.d, "list.xlsx")
        self.assertEqual(decided["no:01234567"], {"website": "kerrroofing.co.uk"})
        self.assertEqual(decided["no:07654321"], {"skip": "yes"})
        self.assertNotIn("no:09999999", decided)
        self.assertEqual([c["Business"] for c in site_check.checks_waiting(self.d, "list.xlsx")], ["Elm Ltd"])
        with (self.d / site_check.LOG).open(encoding="utf-8") as f:
            self.assertEqual(len(list(csv.DictReader(f))), 3)

    def test_unloadable_page_is_unsure_without_asking(self):
        self.assertEqual(site_check.judge({"site": "x.co.uk"}, "", "k")["verdict"], "unsure")
        self.assertEqual(site_check.judge({"site": "x.co.uk", "Business": "X"}, "text", "k", "m", claude({"verdict": "maybe"}))["verdict"], "unsure")


class Voice(unittest.TestCase):
    OUTCOMES = ["No answer", "Call back", "Replied to them", "Interested", "Quoted", "Not interested", "Won"]

    def test_reads_outcome_date_and_note(self):
        got = voice.read("interested, call back thursday", self.OUTCOMES, "k", "m", date(2026, 10, 7),
                         claude({"outcome": "Call back", "due": "2026-10-09", "note": "wants landing page"}))
        self.assertEqual(got, {"outcome": "Call back", "due": "2026-10-09", "note": "wants landing page"})
        odd = voice.read("x", self.OUTCOMES, "k", "m", date(2026, 10, 7), claude({"outcome": "Maybe", "due": "2020-01-01"}))
        self.assertEqual((odd["outcome"], odd["due"]), (None, ""))
        dated = voice.read("x", self.OUTCOMES, "k", "m", date(2026, 10, 7), claude({"outcome": "No answer", "due": "2026-10-10"}))
        self.assertEqual(dated["outcome"], "Call back")  # a date means a call-back

    def test_bot_asks_before_logging(self):
        d = Path(tempfile.mkdtemp())
        panel, calls = fake_panel(d)
        panel.load_settings = lambda: {"PROSPECTS_API_SECRET": "x" * 40, "ANTHROPIC_API_KEY": "k"}
        sent = []
        bot = telegram_bot.Bot(panel, "tok", CHAT, http=lambda m, p, timeout=30: sent.append((m, p)) or {})
        bot.voice_note({"file_id": "v"})
        self.assertIn("Open one with ▶️ Next call", sent[-1][1]["text"])
        bot.focus_sid = bot._remember("call", ITEM)
        with mock.patch("spotted.download", lambda token, fid, http: b"ogg"), \
             mock.patch("voice.transcribe", lambda path: "call back thursday, wants a price"), \
             mock.patch("voice.read", lambda text, outcomes, key, model="": {"outcome": "Call back", "due": "2026-10-09", "note": "wants a price"}):
            bot.voice_note({"file_id": "v"})
        self.assertIn("Log for Kerr Roofing: Call back, call back 2026-10-09 - wants a price", sent[-1][1]["text"])
        self.assertEqual(calls, [])
        button = sent[-1][1]["reply_markup"]["inline_keyboard"][0][0]["callback_data"]
        bot.handle({"callback_query": {"id": "q", "data": button, "message": {"chat": {"id": int(CHAT)}}}})
        self.assertEqual((calls[-1][1]["outcome"], calls[-1][1]["due"], calls[-1][1]["note"]), ("Call back", "2026-10-09", "wants a price"))


class Update(unittest.TestCase):
    def test_restarts_only_into_a_new_version(self):
        panel, _ = fake_panel(Path(tempfile.mkdtemp()))
        restarted = []
        panel.pull_update = lambda: ("Updated to v99 - restarting", "99")
        panel.restart = lambda: restarted.append(True)
        sent = []
        bot = telegram_bot.Bot(panel, "tok", CHAT, http=lambda m, p, timeout=30: sent.append(p["text"]) or {})
        bot.handle({"message": {"chat": {"id": int(CHAT)}, "text": "/update"}})
        self.assertEqual((sent[-1], restarted), ("Updated to v99 - restarting", [True]))
        panel.pull_update = lambda: ("Already up to date (v88).", None)
        bot.handle({"message": {"chat": {"id": int(CHAT)}, "text": "update"}})
        self.assertEqual(restarted, [True])

    def test_pull_refuses_mid_run(self):
        import control_panel as cp

        with mock.patch.object(cp.JOB, "running", lambda: True):
            self.assertIn("A run is going", cp.pull_update()[0])


class Route(unittest.TestCase):
    def test_cards_in_postcode_order_with_maps_links(self):
        firms = [{"business": "B", "address": "1 High St, Woking GU21 5AB"}, {"business": "A", "address": "2 Rd, Guildford GU1 3XX"},
                 {"business": "C", "address": ""}, {"business": "D", "address": "Guildford GU2 4AA"}]
        ordered = cards.route(firms)
        self.assertEqual([f["business"] for f in ordered], ["A", "D", "B", "C"])
        links = cards.maps_links(ordered * 4)
        self.assertEqual(len(links), 2)  # 12 stops: 10 + 2
        self.assertTrue(links[0].startswith("https://www.google.com/maps/dir/2%20Rd"))


class OutOfOffice(unittest.TestCase):
    def test_return_dates(self):
        got = date(2026, 10, 7)
        self.assertEqual(back_on("I'm away and back on Monday 19th October.", got), date(2026, 10, 19))
        self.assertEqual(back_on("Returning 14/10 - for urgent matters call", got), date(2026, 10, 14))
        self.assertEqual(back_on("Out of the office until January 5th", got), date(2027, 1, 5))
        self.assertEqual(back_on("I am on holiday.", got), date(2026, 10, 14))

    def test_follow_up_waits_until_they_are_back(self):
        d = Path(tempfile.mkdtemp())
        with (d / eb.SENT).open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(eb.SENT_FIELDS)
            w.writerow(["away@x.co.uk", "Away", "https://s/for/away-1", "b", "2026-09-28", ""])
            w.writerow(["here@x.co.uk", "Here", "https://s/for/here-1", "b", "2026-09-28", ""])
        with (d / "replies.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["message_id", "date", "from", "business", "kind", "snippet", "message"])
            w.writerow(["1", "2026-09-29", "away@x.co.uk", "Away", "out of office", "", "Back on 12th October."])
        rows, _ = eb.followup_candidates(d, 5, date(2026, 10, 7), {})
        self.assertEqual([r["email"] for r in rows], ["here@x.co.uk"])
        rows, _ = eb.followup_candidates(d, 5, date(2026, 10, 13), {})
        self.assertEqual(sorted(r["email"] for r in rows), ["away@x.co.uk", "here@x.co.uk"])


if __name__ == "__main__":
    unittest.main()
