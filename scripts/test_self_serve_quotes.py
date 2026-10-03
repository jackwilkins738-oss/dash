"""quotes.publish_self_serve: "See my quote" on a preview gets exactly the quote the panel would send."""

import json
import unittest
from unittest import mock

import quotes

SETTINGS = {"PROSPECTS_API_SECRET": "x" * 40, "QUOTE_PRICE_BUILD": "2400", "QUOTE_DEPOSIT_PERCENT": "50", "QUOTE_VAT_RATE": "0"}


class Publish(unittest.TestCase):
    def test_both_packages_with_terms_and_no_client(self):
        sent = []
        lines = quotes.publish_self_serve(SETTINGS, post=lambda url, body, secret: sent.append((url, body, secret)))
        self.assertEqual(lines, ["build: £2,400 published", "landing: £750 published"])
        url, body, secret = sent[0]
        self.assertTrue(url.endswith("/api/prospects/quote-template"))
        self.assertEqual((body["package"], secret), ("build", "x" * 40))
        quote = body["quote"]
        self.assertEqual(quote["line_items"][0]["unit_price_pence"], 240000)
        self.assertEqual(quote["deposit_percent"], 50)
        self.assertGreater(len(quote["terms"]), 200)
        self.assertNotIn("client_name", quote)
        self.assertNotIn("founding", json.dumps(quote).lower())

    def test_same_quote_as_the_panel_sends(self):
        captured = {}

        class Res:
            def read(self):
                return b'{"quote_url": "https://x/quote/1/t"}'

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        def urlopen(req, timeout=0):
            captured["body"] = json.loads(req.data)
            return Res()

        with mock.patch.object(quotes.urllib.request, "urlopen", urlopen):
            quotes.create_quote(SETTINGS, "Kerr Roofing", "", "", "build")
        sent = captured["body"]
        self.assertEqual({k: sent[k] for k in quotes.quote_body(SETTINGS, "build")}, quotes.quote_body(SETTINGS, "build"))


if __name__ == "__main__":
    unittest.main()
