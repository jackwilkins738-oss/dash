"""auto_video: captions from measured numbers only, the upload, and the buttons - offline (no browser).

Run: python -m unittest scripts/test_auto_video.py
"""

import tempfile
import unittest
from pathlib import Path

import auto_video as av
import telegram_bot
from test_telegram_bot import CHAT, ITEM, fake_panel


class Captions(unittest.TestCase):
    def test_only_what_was_measured(self):
        row = {"website": "kerr.co.uk", "mobile_score": 34, "lcp_s": 6.12, "teardown": {"checks": {"tapToCall": False, "contactForm": False}}}
        w = av.captions(row, "Kerr Roofing", "Jack Wilkins", "07401 696272", 2026)
        self.assertEqual(w["site"][1], "Google's phone speed test: 34/100 - 6.1s before anything shows")
        self.assertIn("I noticed your phone number isn't tap-to-call on a mobile", w["site"])
        self.assertEqual(w["preview"][0], "A faster site, made for Kerr Roofing")
        self.assertEqual(w["end"][0], "Jack Wilkins · 07401 696272")
        bare = av.captions({"website": None, "mobile_score": None}, "Oak", "", "", 2026)
        self.assertEqual(bare["site"], ["your website today, on a phone"])
        self.assertEqual(bare["preview"][1], "Built to turn visits into calls")


class Upload(unittest.TestCase):
    def test_signed_upload_then_set_on_the_page(self):
        mp4 = Path(tempfile.mkdtemp()) / "v.mp4"
        mp4.write_bytes(b"mp4data")
        calls = []
        url = av.upload("https://api", "s", "kerr-1", mp4,
                        post=lambda u: calls.append(("post", u)) or {"upload_url": "https://store/sign?t=1", "video_url": "https://store/v.mp4"},
                        put=lambda u, data: calls.append(("put", u, data)),
                        patch=lambda u, body: calls.append(("patch", u, body)) or {"ok": True})
        self.assertEqual(url, "https://store/v.mp4")
        self.assertEqual(calls, [("post", "https://api/api/prospects/kerr-1/video-upload"), ("put", "https://store/sign?t=1", b"mp4data"),
                                 ("patch", "https://api/api/prospects/kerr-1", {"video_url": "https://store/v.mp4"})])
        with self.assertRaises(av.VideoUnavailable):
            av.upload("https://api", "s", "kerr-1", mp4, post=lambda u: {"upload_url": "x", "video_url": "y"},
                      put=lambda u, d: None, patch=lambda u, b: {"error": "Use a Loom link"})


class Buttons(unittest.TestCase):
    def test_panel_action_and_install(self):
        import control_panel as cp

        make, err = cp.build_steps({"action": "auto_video", "video_preview": "https://www.scalardigital.co.uk/for/kerr-a1b2c3"}, {})
        self.assertEqual(list(make(None)), [(cp.AUTO_VIDEO, ["--link", "kerr-a1b2c3"])])
        steps = list(cp.build_steps({"action": "install_video"}, {})[0](None))
        self.assertEqual(steps[1], ("pip-module", ["playwright", "install", "chromium"]))

    def test_telegram_button_starts_the_job(self):
        panel, _ = fake_panel(Path(tempfile.mkdtemp()))
        bot = telegram_bot.Bot(panel, "tok", CHAT, http=lambda m, p, timeout=30: {})
        started = []
        bot.start = lambda action, extra=None, then=None: started.append((action, extra))
        sid = bot._remember("nudge", ITEM)
        bot.handle({"callback_query": {"id": "q", "data": f"av:{sid}", "message": {"chat": {"id": int(CHAT)}}}})
        self.assertEqual(started, [("auto_video", {"video_preview": "https://x/for/kerr"})])


if __name__ == "__main__":
    unittest.main()
