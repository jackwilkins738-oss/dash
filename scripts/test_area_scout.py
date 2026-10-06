"""Offline tests for area_scout - fake Places and PageSpeed, no network.

Run: python -m unittest scripts/test_area_scout.py
"""

import tempfile
import unittest
from pathlib import Path

import openpyxl

import area_scout as a


def place(i, name, site, reviews, types="roofing_contractor"):
    return {"id": f"p{i}", "displayName": {"text": name}, "websiteUri": site, "businessStatus": "OPERATIONAL",
            "primaryType": types, "userRatingCount": reviews}


SEARCHES = {
    "roofer in Guildford": [place(1, "Busy Slow Roofing", "https://slow1.co.uk", 80), place(2, "Busy Slow Two", "https://slow2.co.uk", 40),
                            place(3, "Busy Fast", "https://fast.co.uk", 30), place(4, "No Site Roofers", "", 25),
                            place(5, "Tiny Roofing", "https://tiny.co.uk", 2), place(6, "Wickes", "https://wickes.co.uk", 900, "home_improvement_store")],
    "landscaper in Guildford": [place(1, "Busy Slow Roofing", "https://slow1.co.uk", 80), place(7, "Green Gardens", "https://green.co.uk", 15)],
    "roofer in Woking": [place(8, "Fast One", "https://fast1.co.uk", 50), place(9, "Fast Two", "https://fast2.co.uk", 12)],
    "landscaper in Woking": [],
}
SCORES = {"slow1.co.uk": 22, "slow2.co.uk": 41, "fast.co.uk": 91, "green.co.uk": 30, "fast1.co.uk": 88, "fast2.co.uk": 77}


class Fake:
    def __init__(self):
        self.queries = []

    def __call__(self, body, key):
        self.queries.append(body["textQuery"])
        return {"places": SEARCHES.get(body["textQuery"], [])}


class Scout(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Outreach"
        ws.append(["Business", "Website"])
        ws.append(["Green Gardens", "green.co.uk"])  # already in a list
        wb.save(self.dir / "mine.xlsx")
        self.scored = []

    def tearDown(self):
        self.tmp.cleanup()

    def score(self, domain, key):
        self.scored.append(domain)
        return SCORES.get(domain)

    def run_scout(self, fake):
        logs = []
        rows = a.run(["Woking", "Guildford"], ["roofing", "landscaping"], self.dir, "k", "p", fake, self.score, logs.append)
        return rows, logs

    def test_ranks_towns_by_busy_firms_with_slow_sites(self):
        rows, logs = self.run_scout(Fake())
        g, w = rows
        self.assertEqual((g["Rank"], g["Town"], w["Town"]), (1, "Guildford", "Woking"))
        # Guildford: 5 established (Busy Slow x1 deduped, Two, Fast, No Site, Green); 4 with a site, 1 already yours
        # -> 3 new with a site x 3/4 slow + 0.5 for the one with no site = 2.75 -> 2.8
        self.assertEqual(g["Established (10+ reviews)"], 5)
        self.assertEqual(g["With a website"], 4)
        self.assertEqual(g["Under 50"], "75%")
        self.assertEqual(g["Median score"], 36)
        self.assertEqual(g["Established, no website"], 1)
        self.assertEqual(g["Already in your lists"], 1)
        self.assertEqual(g["Opportunity"], 2.8)
        self.assertEqual((w["Opportunity"], w["Under 50"]), (0.0, "0%"))
        self.assertNotIn("tiny.co.uk", self.scored)  # 2 reviews - not established, not measured
        self.assertNotIn("wickes.co.uk", self.scored)
        self.assertIn("Next: Find new prospects -> Google Maps, the same trades, Areas: Guildford, Woking.", logs)
        book = openpyxl.load_workbook(self.dir / "area-scout.xlsx")
        self.assertEqual([c.value for c in book["Areas"][2]][:3], [1, "Guildford", 2.8])

    def test_second_scout_uses_the_cache(self):
        fake = Fake()
        self.run_scout(fake)
        n_queries, n_scored = len(fake.queries), len(self.scored)
        self.run_scout(fake)
        self.assertEqual((len(fake.queries), len(self.scored)), (n_queries, n_scored))

    def test_without_a_speed_key_it_still_counts(self):
        logs = []
        rows = a.run(["Guildford"], ["roofing"], self.dir, "k", "", Fake(), self.score, logs.append)
        self.assertEqual(self.scored, [])
        self.assertEqual(rows[0]["Under 50"], "-")
        self.assertIn("ranked on firm counts only", logs[0])


class Panel(unittest.TestCase):
    def test_scout_button_runs_the_script_with_checked_values(self):
        import control_panel as cp

        make, err = cp.build_steps({"action": "scout", "trades": ["roofing", "nope"], "areas": "Guildford, Woking"},
                                   {"GOOGLE_PLACES_API_KEY": "k"})
        self.assertEqual(err, "")
        self.assertEqual(list(make(None)), [(cp.SCOUT, ["--trades", "roofing", "--areas", "Guildford, Woking"])])
        self.assertEqual(cp.build_steps({"action": "scout", "trades": ["roofing"], "areas": "<b>"}, {"PAGESPEED_API_KEY": "k"})[1],
                         "Areas can only have letters, numbers, spaces and commas.")
        self.assertIn("GOOGLE_PLACES_API_KEY", cp.build_steps({"action": "scout", "trades": ["roofing"]}, {})[1])


if __name__ == "__main__":
    unittest.main()
