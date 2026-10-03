"""telegram_bot: only your chat, confirm before anything is sent, and drafts you see before they go."""

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import telegram_bot

CHAT = "12345"
ITEM = {"key": "k1", "sheet": "list.xlsx", "business": "Kerr Roofing", "website": "kerrroofing.co.uk",
        "email": "info@kerrroofing.co.uk", "contact": "John", "phone": "01483 111222", "snippet": "How much?",
        "message": "How much would it be?", "subject": "Your website", "message_id": "<a@b>", "views": 3, "seconds": 90,
        "preview": "https://x/for/kerr"}


class FakeJob:
    def __init__(self):
        self.started = []
        self.thread = None

    def start(self, label, steps, settings, needs_secret=True, keep_going=False):
        self.started.append(label)
        return ""

    def running(self):
        return False

    def state(self):
        return {"running": False, "label": "x", "lines": [], "started": 0}

    def stop(self):
        pass


def fake_panel(d):
    calls = []
    p = SimpleNamespace(
        OUTREACH=d, JOB=FakeJob(), ACTIONS={"send_batch": "Send today's batch", "batch": "Make email batch", "all": "Run the whole list"},
        load_settings=lambda: {"PROSPECTS_API_SECRET": "x" * 40},
        build_steps=lambda body, s: ((lambda job: []), ""),
        call_action=lambda body: (calls.append(("call", body)) or ({"ok": True, "message": f"{body['business']}: {body['outcome']} logged"}, 200)),
        reply_ai_action=lambda body: ({"ok": True, "text": "Hi John, it's £1,500."}, 200),
        reply_send_action=lambda body: (calls.append(("send", body)) or ({"ok": True, "message": "Replied"}, 200)),
        research_action=lambda body: ({"lines": ["Company: KERR ROOFING LTD"], "google": "https://g"}, 200),
        sheets=lambda: ["list.xlsx"],
    )
    return p, calls


class Bot(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        self.panel, self.calls = fake_panel(self.d)
        self.sent = []
        self.bot = telegram_bot.Bot(self.panel, "tok", CHAT, http=lambda method, payload, timeout=30: self.sent.append((method, payload)) or {})

    def texts(self):
        return [p["text"] for m, p in self.sent if m == "sendMessage"]

    def buttons(self):
        return [b["callback_data"] for m, p in self.sent if m == "sendMessage" and "reply_markup" in p
                for row in p["reply_markup"].get("inline_keyboard", []) for b in row]

    def tap(self, data, chat=CHAT):
        self.bot.handle({"callback_query": {"id": "q", "data": data, "message": {"chat": {"id": int(chat)}}}})

    def say(self, text, chat=CHAT):
        self.bot.handle({"message": {"chat": {"id": int(chat)}, "text": text}})

    def test_strangers_get_silence(self):
        self.say("/start", chat="999")
        self.tap("run:send_batch", chat="999")
        self.assertEqual(self.sent, [])
        self.assertEqual(self.panel.JOB.started, [])

    def test_start_shows_the_menu(self):
        self.say("/start")
        payload = self.sent[-1][1]
        self.assertIn("keyboard", payload["reply_markup"])

    def test_sending_needs_a_second_tap(self):
        self.tap("send?")
        self.assertEqual(self.panel.JOB.started, [])
        self.assertIn("run:send_batch", self.buttons())
        with mock.patch("autopilot.is_running", return_value=False), mock.patch.object(telegram_bot.threading, "Thread"):
            self.tap("run:send_batch")
        self.assertEqual(self.panel.JOB.started, ["Send today's batch"])

    def test_only_safe_jobs_can_start(self):
        self.bot.start("publish_site")
        self.assertIn("only be done on the panel", self.texts()[-1])
        self.assertEqual(self.panel.JOB.started, [])

    def test_call_outcomes_and_not_interested_confirm(self):
        sid = self.bot._remember("call", ITEM)
        self.tap(f"o:{sid}:Interested")
        self.assertEqual(self.calls[-1][1]["outcome"], "Interested")
        self.tap(f"ni?:{sid}")
        self.assertEqual(len(self.calls), 1)  # asked, not done
        self.tap(f"ni:{sid}")
        self.assertEqual(self.calls[-1][1]["outcome"], "Not interested")
        self.tap(f"cb:{sid}")
        self.assertEqual((self.calls[-1][1]["outcome"], self.calls[-1][1]["due"]), ("Call back", "tomorrow"))

    def test_ai_draft_is_shown_then_sent_only_on_tap(self):
        sid = self.bot._remember("reply", ITEM)
        self.tap(f"ai:{sid}")
        self.assertIn("Hi John, it's £1,500.", self.texts()[-1])
        self.assertFalse(any(c[0] == "send" for c in self.calls))
        self.tap(f"sendreply:{sid}")
        sent = [c[1] for c in self.calls if c[0] == "send"][0]
        self.assertEqual((sent["to"], sent["text"], sent["message_id"]), ("info@kerrroofing.co.uk", "Hi John, it's £1,500.", "<a@b>"))
        self.tap(f"sendreply:{sid}")  # a second tap never sends twice
        self.assertEqual(len([c for c in self.calls if c[0] == "send"]), 1)

    def test_written_reply_is_previewed_first(self):
        sid = self.bot._remember("reply", ITEM)
        self.tap(f"wr:{sid}")
        self.say("Hi John - give me a ring on 07401 696272.")
        self.assertIn("give me a ring", self.texts()[-1])
        self.assertIn(f"sendreply:{sid}", self.buttons())
        self.assertFalse(any(c[0] == "send" for c in self.calls))

    def test_stale_buttons_say_so(self):
        self.tap("o:deadbeef00:Won")
        self.assertIn("out of date", self.texts()[-1])

    def test_research(self):
        sid = self.bot._remember("call", ITEM)
        self.tap(f"rs:{sid}")
        self.assertIn("KERR ROOFING LTD", self.texts()[-1])

    def test_no_bot_without_settings(self):
        telegram_bot._BOT = None
        self.assertIsNone(telegram_bot.start(SimpleNamespace(load_settings=lambda: {"TELEGRAM_BOT_TOKEN": "", "TELEGRAM_CHAT_ID": ""})))


if __name__ == "__main__":
    unittest.main()
