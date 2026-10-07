"""self_test: each check's verdict from faked answers - no network.

Run: python -m unittest scripts/test_self_test.py
"""

import tempfile
import unittest
from pathlib import Path

import self_test as st


class Checks(unittest.TestCase):
    def run_with(self, env, answers, have=lambda m: True):
        def get(url, headers=None, timeout=20):
            for part, ans in answers.items():
                if part in url:
                    return ans
            return 0, {}

        return {name: (mark, detail) for mark, name, detail in st.checks(env, Path(tempfile.mkdtemp()), get, have)}

    def test_all_good(self):
        env = {"PROSPECTS_API_SECRET": "x" * 40, "MAIL_ADDRESS": "a@b.co.uk", "MAIL_APP_PASSWORD": "p", "MAIL_FROM_NAME": "Jack",
               "TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "1", "ANTHROPIC_API_KEY": "k", "PAGESPEED_API_KEY": "p",
               "GOOGLE_PLACES_API_KEY": "g", "BOOKING_LINK": "https://cal.com/x", "REVIEW_LINK": "https://g.page/r/x", "BACKUP_DIR": "D:/b"}
        got = self.run_with(env, {"/activity": (200, {"prospects": [1, 2]}), "/quotes": (200, {}), "telegram": (200, {"ok": True, "result": {"username": "scalarbot"}}),
                                  "anthropic": (200, {}), "pagespeed": (200, {})})
        self.assertEqual(got["Dashboard"], (st.OK, "connected - 2 preview pages"))
        self.assertEqual(got["Telegram"], (st.OK, "@scalarbot"))
        self.assertIn("spend limit", got["Claude (AI)"][1])
        self.assertTrue(all(m != st.BAD for m, _ in got.values()), got)

    def test_broken_and_missing(self):
        got = self.run_with({"PROSPECTS_API_SECRET": "x" * 40, "ANTHROPIC_API_KEY": "k"},
                            {"/activity": (401, {}), "anthropic": (401, {})}, have=lambda m: m == "openpyxl")
        self.assertEqual(got["Dashboard"][0], st.BAD)
        self.assertIn("must match", got["Dashboard"][1])
        self.assertEqual(got["Claude (AI)"][0], st.BAD)
        self.assertEqual(got["Email"][0], st.BAD)
        self.assertEqual(got["BACKUP_DIR"][0], st.BAD)
        self.assertEqual(got["Voice notes"], (st.OPTIONAL, "not installed - Settings -> Install voice notes"))
        self.assertEqual(got["Telegram"][0], st.OPTIONAL)

    def test_quote_chaser_names_the_missing_migration(self):
        got = self.run_with({"PROSPECTS_API_SECRET": "x" * 40}, {"/activity": (200, {}), "/quotes": (200, {"quotes": [], "warning": "Run migration 057"})})
        self.assertEqual(got["Quote chaser"], (st.BAD, "Run migration 057 (Supabase -> SQL Editor)"))
        got = self.run_with({"PROSPECTS_API_SECRET": "x" * 40}, {"/activity": (200, {}), "/quotes": (500, {"error": "column quotes.view_count does not exist"})})
        self.assertIn("column quotes.view_count does not exist", got["Quote chaser"][1])


if __name__ == "__main__":
    unittest.main()
