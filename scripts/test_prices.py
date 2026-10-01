"""The prices on the website, the quotes, the terms and the panel's defaults must never drift apart."""

import re
import unittest
from pathlib import Path

import control_panel as cp
import quotes
import terms

SITE = (Path(__file__).resolve().parent.parent / "lib" / "site.ts").read_text(encoding="utf-8")


def site_price(key: str) -> int:
    m = re.search(r"PRICES\s*=\s*\{([^}]*)\}", SITE)
    return int(re.search(rf"\b{key}:\s*(\d+)", m.group(1)).group(1))


class Prices(unittest.TestCase):
    def test_quotes_default_to_the_website_prices(self):
        self.assertEqual(quotes.PACKAGES["build"][1], site_price("build"))
        self.assertEqual(quotes.PACKAGES["landing"][1], site_price("landing"))

    def test_terms_quote_the_websites_dashboard_fee(self):
        self.assertEqual(terms.DASHBOARD_MONTHLY, site_price("dashboardMonthly"))

    def test_saved_replies_default_to_the_website_prices(self):
        values = cp.reply_values({}, {})
        self.assertEqual(values["price_build"], f"{site_price('build'):,}")
        self.assertEqual(values["price_landing"], f"{site_price('landing'):,}")

    def test_panel_placeholders_and_quote_buttons_match(self):
        self.assertIn(f'placeholder="{site_price("build")} if blank"', cp.PAGE)
        self.assertIn(f'placeholder="{site_price("landing")} if blank"', cp.PAGE)
        self.assertIn(f'build: s.settings.QUOTE_PRICE_BUILD || "{site_price("build")}"', cp.PAGE)


if __name__ == "__main__":
    unittest.main()
