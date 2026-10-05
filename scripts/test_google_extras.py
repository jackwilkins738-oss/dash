"""Offline tests for google_extras - fake Places and PageSpeed, no network.

Run: python -m unittest scripts/test_google_extras.py
"""

import tempfile
import unittest
from pathlib import Path

import google_extras as g


def place(name, site, rating=None, reviews=None, types="roofing_contractor"):
    p = {"displayName": {"text": name}, "websiteUri": site, "businessStatus": "OPERATIONAL", "primaryType": types}
    if rating is not None:
        p.update(rating=rating, userRatingCount=reviews)
    return p


class Fake:
    def __init__(self, results):
        self.results, self.queries = results, []

    def __call__(self, body, key):
        self.queries.append(body["textQuery"])
        return {"places": self.results.get(body["textQuery"], [])}


SEARCH = [
    place("Top Roofing", "https://toproofing.co.uk/"),
    place("B&Q Guildford", "https://diy.com/", types="home_improvement_store"),  # a merchant, never a rival
    place("No Site Roofers", ""),
    place("Kerr Roofing", "https://www.kerr.co.uk/"),
    place("Second Roofing", "https://second.co.uk"),
    place("Third Roofs <b>", "https://third.co.uk"),
    place("Fourth Roofing", "https://fourth.co.uk"),
]
SCORES = {"toproofing.co.uk": 88, "second.co.uk": 71, "third.co.uk": None, "fourth.co.uk": 64}


class Words(unittest.TestCase):
    def test_search_words_by_trade(self):
        self.assertEqual(g.search_words("Roofing"), "roofer")
        self.assertEqual(g.search_words("Loft conversions"), "loft conversion company")
        self.assertEqual(g.search_words("Paving & driveways"), "driveway contractor")
        self.assertEqual(g.search_words("Plumbing"), "plumbing")

    def test_rating_from_sheet(self):
        self.assertEqual(g.rating_from_sheet("4.83", "63"), {"rating": 4.8, "reviews": 63})
        self.assertIsNone(g.rating_from_sheet("", ""))
        self.assertIsNone(g.rating_from_sheet(4.5, 0))


class Ratings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_a_result_with_their_own_website_counts(self):
        fake = Fake({"Kerr Roofing Guildford": [place("Kerr Roofing Ltd", "https://other.co.uk", 3.1, 9),
                                                place("Kerr Roofing", "http://www.kerr.co.uk/contact", 4.8, 63)],
                     "Ghost Roofing Woking": [place("Ghost Roofing", "https://elsewhere.co.uk", 5.0, 200)]})
        self.assertEqual(g.rating("Kerr Roofing", "Guildford", "kerr.co.uk", "k", self.dir, fake), {"rating": 4.8, "reviews": 63})
        self.assertIsNone(g.rating("Ghost Roofing", "Woking", "ghost.co.uk", "k", self.dir, fake))
        # Cached - a second ask doesn't search again.
        g.rating("Kerr Roofing", "Guildford", "kerr.co.uk", "k", self.dir, fake)
        self.assertEqual(len(fake.queries), 2)


class Rivals(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.fake = Fake({"roofer in Guildford": SEARCH})
        self.scored = []

    def tearDown(self):
        self.tmp.cleanup()

    def score(self, domain, key):
        self.scored.append(domain)
        return SCORES.get(domain)

    def test_top_firms_with_scores_and_where_they_came(self):
        r = g.rivals("Roofing", "guildford", "kerr.co.uk", "k", "p", self.dir, self.fake, self.score)
        self.assertEqual(r["query"], "roofer in Guildford")
        self.assertEqual(r["position"], 3)  # Top, No Site, Kerr - the merchant isn't counted
        self.assertEqual(r["items"], [{"name": "Top Roofing", "score": 88}, {"name": "Second Roofing", "score": 71},
                                      {"name": "Fourth Roofing", "score": 64}])  # Third couldn't be measured
        self.assertEqual(r["checkedAt"][:2], "20")

    def test_one_search_per_trade_and_town(self):
        g.rivals("Roofing", "Guildford", "kerr.co.uk", "k", "p", self.dir, self.fake, self.score)
        g.rivals("roofers", "Guildford", "toproofing.co.uk", "k", "p", self.dir, self.fake, self.score)
        self.assertEqual(self.fake.queries, ["roofer in Guildford"])
        self.assertEqual(sorted(set(self.scored)), sorted(["toproofing.co.uk", "kerr.co.uk", "second.co.uk", "third.co.uk", "fourth.co.uk"]))

    def test_nothing_without_a_town_or_two_scores(self):
        self.assertIsNone(g.rivals("Roofing", "", "kerr.co.uk", "k", "p", self.dir, self.fake, self.score))
        thin = Fake({"roofer in Woking": [place("Only One", "https://one.co.uk")]})
        self.assertIsNone(g.rivals("Roofing", "Woking", "kerr.co.uk", "k", "p", self.dir, thin, lambda d, k: 50))


class AddTo(unittest.TestCase):
    def test_fills_the_teardown_and_never_fails_the_run(self):
        from places_finder import PlacesError

        with tempfile.TemporaryDirectory() as d:
            prospects = [{"business_name": "Kerr Roofing", "area": "Guildford", "trade": "Roofing", "website": "kerr.co.uk",
                          "teardown": {"checks": {}}, "_google": {"rating": 4.8, "reviews": 63}},
                         {"business_name": "Unchecked", "website": "u.co.uk"}]
            logs = []
            g.add_to(prospects, Path(d), "k", "p", Fake({"roofer in Guildford": SEARCH}), lambda dom, k: SCORES.get(dom), logs.append)
            self.assertEqual(prospects[0]["teardown"]["google"], {"rating": 4.8, "reviews": 63})
            self.assertEqual(len(prospects[0]["teardown"]["rivals"]["items"]), 3)
            self.assertIn("1 rating(s) and 1 competitor comparison(s)", logs[-1])

            def refused(body, key):
                raise PlacesError("Google refused the key for Places.")

            logs.clear()
            g.add_to([{**prospects[0], "_google": None, "teardown": {"checks": {}}, "area": "Woking"}], Path(d), "k", "p", refused,
                     lambda dom, k: 50, logs.append)
            self.assertIn("stopped: Google refused", logs[-1])

    def test_no_key_says_how_to_get_it(self):
        logs = []
        g.add_to([{"teardown": {"checks": {}}, "website": "x.co.uk", "business_name": "X"}], Path("."), "", "p", log=logs.append)
        self.assertIn("GOOGLE_PLACES_API_KEY", logs[0])


if __name__ == "__main__":
    unittest.main()
