"""Call briefs from Cal.com bookings, and the client's nameserver guide - offline.

Run: python -m unittest scripts/test_brief_dns.py
"""

import json
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import openpyxl

import go_live
import telegram_bot
from test_telegram_bot import CHAT, fake_panel


class Brief(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Outreach"
        ws.append(["Business", "Website", "Email", "Phone", "Contact name"])
        ws.append(["Kerr Roofing", "kerr.co.uk", "Sam@Kerr.co.uk", "01483 111222", "Sam Kerr"])
        wb.save(self.d / "list.xlsx")
        self.panel, _ = fake_panel(self.d)
        self.sent = []
        self.bot = telegram_bot.Bot(self.panel, "tok", CHAT,
                                    http=lambda m, p, timeout=30: (self.sent.append(p["text"]) if m == "sendMessage" else None) or {})

    def alert(self, start):
        return f"📅 Call booked: Sam Kerr\nWhen: Wed 14 Oct, 10:30 (UK)\nEmail: sam@kerr.co.uk\nStart: {start}"

    def test_brief_now_and_fifteen_minutes_before(self):
        start = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        self.bot.handle({"callback_query": {"id": "q", "data": "brief", "message": {"chat": {"id": int(CHAT)}, "text": self.alert(start)}}})
        self.assertIn("📋 Brief: Kerr Roofing - Sam Kerr", self.sent[0])
        self.assertIn("01483 111222", self.sent[0])
        self.assertIn("Company: KERR ROOFING LTD", self.sent[0])  # the research card
        saved = json.loads((self.d / "briefs.json").read_text())
        self.bot.maybe_briefs(saved[0]["at"] + 60)
        self.assertTrue(self.sent[-1].startswith("⏰ In 15 minutes:"))
        self.bot.maybe_briefs(saved[0]["at"] + 120)
        self.assertEqual(sum(t.startswith("⏰") for t in self.sent), 1)

    def test_unknown_email_is_a_new_lead_and_a_soon_call_gets_no_reminder(self):
        start = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        self.bot.brief(self.alert(start).replace("sam@kerr.co.uk", "new@else.co.uk"))
        self.assertIn("isn't in your lists - a new lead", self.sent[0])
        self.assertFalse((self.d / "briefs.json").exists())


class Handover(unittest.TestCase):
    NS = ["ada.ns.cloudflare.com", "bob.ns.cloudflare.com"]

    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        snap = go_live.snapshot_path(self.d, "kerr.co.uk", None)
        snap.parent.mkdir(parents=True)
        snap.write_text(json.dumps({"taken": "x", "records": {"kerr.co.uk MX": ["10 aspmx.l.google.com."]}}))

    def rdap(self, url):
        return {"entities": [{"roles": ["registrar"], "vcardArray": ["vcard", [["version", {}, "text", "4.0"], ["fn", {}, "text", "123-Reg Limited"]]]}]}

    def test_guide_for_their_registrar_and_the_watch(self):
        ns_now = {"kerr.co.uk": ["ns1.123-reg.co.uk."]}
        ask = lambda name, rtype: ns_now[name]  # noqa: E731
        self.assertEqual(go_live.run_handover("kerr.co.uk", self.NS, self.d, None, ask=ask, get=self.rdap), 0)
        page = (self.d / "dns" / "kerr.co.uk-guide.html").read_text()
        self.assertIn("123 Reg", page)
        self.assertIn("https://www.123-reg.co.uk/secure/", page)
        self.assertIn("<code>ada.ns.cloudflare.com</code>", page)
        self.assertIn("Google", page)  # their email host, named
        self.assertEqual(go_live.switched(self.d, ask), [])
        ns_now["kerr.co.uk"] = ["bob.ns.cloudflare.com.", "ada.ns.cloudflare.com."]
        self.assertEqual([i["domain"] for i in go_live.switched(self.d, ask)], ["kerr.co.uk"])
        self.assertEqual(go_live.switched(self.d, ask), [])  # told once

    def test_needs_the_snapshot_and_real_nameservers(self):
        ask = lambda name, rtype: []  # noqa: E731
        self.assertEqual(go_live.run_handover("kerr.co.uk", ["a.example.com", "b"], self.d, None, ask=ask, get=self.rdap), 1)
        self.assertEqual(go_live.run_handover("other.co.uk", self.NS, self.d, None, ask=ask, get=self.rdap), 1)
        self.assertEqual(go_live.registrar("x.co.uk", lambda url: (_ for _ in ()).throw(OSError())), "")

    def test_bot_texts_when_switched(self):
        panel, _ = fake_panel(self.d)
        sent = []
        bot = telegram_bot.Bot(panel, "tok", CHAT, http=lambda m, p, timeout=30: (sent.append(p["text"]) if m == "sendMessage" else None) or {})
        go_live.watch(self.d, "kerr.co.uk", self.NS, None)
        old = go_live.lookup
        go_live.lookup = lambda name, rtype: [n + "." for n in self.NS]
        try:
            bot.maybe_dns_check(time.time())
        finally:
            go_live.lookup = old
        self.assertIn("kerr.co.uk now points at Cloudflare", sent[0])


if __name__ == "__main__":
    unittest.main()
