"""Offline tests for seo_guides - no Anthropic, no network.

Run: python -m unittest scripts/test_seo_guides.py
"""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import seo_guides
import seo_loop

TODAY = date(2026, 11, 1)
SITE_TEXT = "A landing page is £750 and a five-page site is £2,500. You own it outright. Fixed price before we start."
LINKS = {"/work": "prices", "/guides/how-much-does-a-tradesman-website-cost": "cost guide", "/websites-for/roofers": "roofers"}
PARA = ("Take photos at the end of every job while the light is good, from where the customer would stand, and "
        "keep the van and the skip out of the shot. A tidy finished driveway or roof says more than any paragraph "
        "about your work, and a few honest before and after pairs show the size of what you took on. ")


def good_guide(**over):
    g = {
        "topic": "Photos that win trade jobs",
        "slug": "photos-that-win-trade-jobs",
        "title": "Photos that win trade jobs",
        "metaTitle": "Photos That Win Trade Jobs",
        "description": "What to photograph on site, how to take it on a phone, and where to use it on your website so the pictures do the selling for you.",
        "card": "What to photograph on site and how to use it on your website.",
        "summary": "Good photos of finished work are the strongest thing a trade website has. Take them at the end of each job, "
                   "from the customer's point of view, and put the best few on the pages people actually visit.",
        "sections": [
            {"heading": f"Section {i}", "paragraphs": [PARA * 2, PARA + "See [our prices](/work#pricing)."],
             **({"bullets": [{"lead": "Light.", "text": "Shoot in daylight."}]} if i == 1 else {})}
            for i in range(1, 6)
        ],
        "faqs": [
            {"q": "How many photos should I put on my website?", "a": "A handful of your best finished jobs beats a long gallery of everything."},
            {"q": "Can I use photos from my phone?", "a": "Yes. A modern phone in good light is plenty, as long as the shot is level and tidy."},
            {"q": "Should I show before and after photos?", "a": "Yes, a few honest pairs show the size of the job you took on and how it turned out."},
        ],
    }
    g.update(over)
    return g


def check(g, taken=frozenset()):
    return seo_guides.check(g, SITE_TEXT, LINKS, set(taken), TODAY, seo_loop.TITLE_MAX, (seo_loop.DESC_MIN, seo_loop.DESC_MAX), seo_loop.HYPE)


class Gaps(unittest.TestCase):
    def test_phrases_with_no_good_page(self):
        pages = {"/a": {"queries": [{"query": "roof website", "impressions": 5, "position": 30.0},
                                    {"query": "builder website", "impressions": 9, "position": 4.0}]},
                 "/b": {"queries": [{"query": "roof website", "impressions": 4, "position": 15.0},
                                    {"query": "rare", "impressions": 1, "position": 40.0}]}}
        self.assertEqual(seo_guides.gaps(pages), [{"query": "roof website", "impressions": 9, "position": 15.0}])

    def test_next_idea_skips_covered_ones(self):
        done = {"how-to-get-more-google-reviews": "how to get more google reviews"}
        ideas = ["How to get more Google reviews fast", "Should a trade website show prices?"]
        self.assertEqual(seo_guides.next_idea(ideas, done), "Should a trade website show prices?")
        self.assertEqual(seo_guides.next_idea(ideas[:1], done), "")

    def test_existing_reads_both_kinds(self):
        with tempfile.TemporaryDirectory() as d:
            app, guides = Path(d) / "app", Path(d) / "guides"
            (app / "written-one").mkdir(parents=True)
            (app / "written-one" / "page.tsx").write_text("x")
            (app / "[slug]").mkdir()
            guides.mkdir()
            (guides / "drafted.json").write_text(json.dumps({"topic": "Drafted topic"}))
            self.assertEqual(seo_guides.existing(guides, app), {"written-one": "written one", "drafted": "Drafted topic"})


class Checking(unittest.TestCase):
    def test_a_good_guide_passes_and_is_dated_today(self):
        guide, why = check(good_guide())
        self.assertEqual(why, [])
        self.assertEqual(guide["published"], "2026-11-01")
        self.assertEqual(guide["sections"][0]["bullets"], [{"lead": "Light.", "text": "Shoot in daylight."}])

    def test_catches_what_must_never_go_live(self):
        bad = good_guide(
            slug="Photos!", metaTitle="x" * 60, description="short",
            summary="Studies show 9 in 10 customers look at photos. Our £399 package is the leading one. See https://example.com",
            faqs=[{"q": "No question mark", "a": "short"}],
        )
        bad["sections"][0]["paragraphs"].append("Read [this](/not-a-page) and [that](/websites-for/roofers). TODO")
        guide, why = check(bad, taken={"photos-that-win-trade-jobs"})
        self.assertIsNone(guide)
        text = " | ".join(why)
        for reason in ("slug must be", "metaTitle is 60", "description is 5", "summary is", "FAQs (3-6)", "short question",
                       "/not-a-page", "says £399", "cites research", "says 'leading'", "web address", "placeholder"):
            self.assertIn(reason, text)
        self.assertNotIn("/websites-for/roofers", text)

    def test_taken_slug_and_word_count(self):
        _, why = check(good_guide(), taken={"photos-that-win-trade-jobs"})
        self.assertIn("already exists", " ".join(why))
        short = good_guide(sections=[{"heading": f"H{i}", "paragraphs": ["Too short."]} for i in range(5)])
        _, why = check(short)
        self.assertTrue(any("words (900-2400)" in w for w in why))

    def test_wrong_shape(self):
        self.assertEqual(check({"slug": "x"}), (None, ["the JSON is missing fields or has the wrong shape"]))


class Making(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.dirs = {"guides_dir": d / "guides", "written_dir": d / "app", "ideas_file": d / "ideas.json"}
        self.dirs["ideas_file"].write_text(json.dumps(["Photos that win trade jobs"]))

    def tearDown(self):
        self.tmp.cleanup()

    def make(self, ask, pages=None):
        return seo_guides.make(pages or {}, LINKS, SITE_TEXT, ask, TODAY, seo_loop.TITLE_MAX,
                               (seo_loop.DESC_MIN, seo_loop.DESC_MAX), seo_loop.HYPE, log=lambda *_: None, **self.dirs)

    def test_a_rejected_draft_goes_back_once_with_the_reasons(self):
        asks = []

        def ask(system, user):
            asks.append(user)
            return good_guide(description="short") if len(asks) == 1 else good_guide()

        guide, why = self.make(ask)
        self.assertEqual((guide["slug"], why), ("photos-that-win-trade-jobs", []))
        self.assertIn("Write this topic: Photos that win trade jobs", asks[0])
        self.assertIn("description is 5 characters", asks[1])
        self.assertTrue((self.dirs["guides_dir"] / "photos-that-win-trade-jobs.json").exists())

    def test_two_failures_mean_no_guide(self):
        guide, why = self.make(lambda s, u: good_guide(summary="x"))
        self.assertIsNone(guide)
        self.assertIn("summary is 1 characters", " ".join(why))
        self.assertFalse(self.dirs["guides_dir"].exists())

    def test_search_gaps_are_offered_first(self):
        seen = []
        pages = {"/a": {"queries": [{"query": "trade website photos", "impressions": 6, "position": 25.0}]}}
        self.make(lambda s, u: seen.append(u) or good_guide(), pages)
        self.assertIn("\"trade website photos\": 6 views", seen[0])
        self.assertIn("Otherwise write this topic", seen[0])

    def test_nothing_to_write(self):
        self.dirs["ideas_file"].write_text("[]")
        guide, why = self.make(lambda s, u: good_guide())
        self.assertIsNone(guide)
        self.assertIn("add more ideas", why[0])


class Helpers(unittest.TestCase):
    def test_link_targets_and_change(self):
        self.assertEqual(seo_loop.link_targets({"/", "/work", "/websites-for/roofers"}),
                         {"/": "home page", "/work": "prices and what's included", "/websites-for/roofers": "roofers"})
        self.assertEqual([seo_loop.change(15, 10), seo_loop.change(5, 10), seo_loop.change(3, 0), seo_loop.change(0, 0)],
                         ["+50%", "-50%", "new", "no change"])


if __name__ == "__main__":
    unittest.main()
