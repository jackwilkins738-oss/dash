"""Offline tests for trade_guess. Run: python -m unittest scripts/test_trade_guess.py"""

import unittest

from trade_guess import guess_trade, page_text_for_guess


class GuessTrade(unittest.TestCase):
    def test_a_builder_is_not_mistaken_for_driveways(self):
        # The real case this was written for (Burhill Properties' own title).
        title = "Burhill Properties Ltd | Extensions | Conversions | New Builds | Land and New Homes | Hersham Walton on Thames Surrey"
        self.assertEqual(guess_trade(title), "Building & extensions")

    def test_each_trade(self):
        self.assertEqual(guess_trade("Surrey roofing specialists - slate, tiles, flat roofs"), "Roofing")
        self.assertEqual(guess_trade("Loft conversions and dormers across Kent"), "Loft conversions")
        self.assertEqual(guess_trade("Resin driveways and block paving in Guildford"), "Driveways & patios")
        self.assertEqual(guess_trade("Garden design and landscaping"), "Landscaping")

    def test_the_strongest_match_wins(self):
        # "Loft conversions" also contains "conversion" (building), but loft wins on its own words.
        self.assertEqual(guess_trade("Loft conversions, dormer lofts and mansard lofts"), "Loft conversions")

    def test_no_match_means_no_guess(self):
        self.assertIsNone(guess_trade("Welcome to our website"))
        self.assertIsNone(guess_trade(""))


class PageText(unittest.TestCase):
    def test_reads_title_description_and_headings_only(self):
        page = (
            "<html><head><title>Smith &amp; Co | Roofing</title>"
            '<meta name="description" content="Flat roofs and repairs"></head>'
            "<body><h1>Roofers in <b>Surrey</b></h1><p>We also mention driveways once in the body.</p></body></html>"
        )
        text = page_text_for_guess(page)
        self.assertIn("Smith & Co | Roofing", text)
        self.assertIn("Flat roofs and repairs", text)
        self.assertIn("Roofers in Surrey", text)
        self.assertNotIn("driveways", text)


if __name__ == "__main__":
    unittest.main()
