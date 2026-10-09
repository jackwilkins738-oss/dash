"""findings.py: the worst problem first, in plain words, and nothing claimed that wasn't checked."""

import unittest

from findings import all_issues, top_issue

YEAR = 2026


class Issues(unittest.TestCase):
    def test_worst_first(self):
        t = {"checks": {"indexable": False, "mobileViewport": False, "tapToCall": False, "phoneShown": False, "contactForm": False}}
        self.assertEqual(all_issues(t, YEAR)[:4], [
            "your homepage is set to tell Google not to list it",
            "your site isn't set up for phones - it shows the desktop page shrunk down",
            "there's no phone number on your homepage",
            "there's no enquiry form on your homepage",
        ])

    def test_no_number_at_all_replaces_not_tappable(self):
        self.assertEqual(top_issue({"checks": {"tapToCall": False, "phoneShown": True}}, YEAR), "your phone number isn't tap-to-call on a mobile")
        issues = all_issues({"checks": {"tapToCall": False, "phoneShown": False}}, YEAR)
        self.assertEqual(issues, ["there's no phone number on your homepage"])

    def test_numbers_only_past_their_thresholds(self):
        heavy = all_issues({"checks": {}, "pageWeightKb": 6200, "imageSavingsKb": 3000, "serverResponseMs": 2412, "layoutShift100": 31}, YEAR)
        self.assertEqual(heavy, [
            "your homepage is 6.2 MB to download on a phone",
            "your web server takes 2.4s before the page even starts to load",
            "the page jumps about while it loads, so it's easy to tap the wrong thing",
        ])
        fine = all_issues({"checks": {}, "pageWeightKb": 1800, "serverResponseMs": 400, "layoutShift100": 5}, YEAR)
        self.assertEqual(fine, [])
        self.assertIn("lighter", all_issues({"checks": {}, "pageWeightKb": 2500, "imageSavingsKb": 900}, YEAR)[0])

    def test_new_plain_word_findings(self):
        issues = all_issues({"checks": {"imageAlt": False, "businessEmail": False, "showsReviews": False, "localSchema": False}}, YEAR)
        self.assertEqual(issues, [
            "your homepage doesn't show any customer reviews",
            "your photos have no descriptions, so Google can't tell what work they show",
            "your site gives a Gmail/Hotmail-style email rather than one at your own web address",
            "your site doesn't tell Google your trade and area the way it reads them for local searches",
        ])

    def test_unchecked_is_never_a_problem(self):
        self.assertEqual(all_issues({"checks": {}}, YEAR), [])
        self.assertEqual(all_issues(None, YEAR), [])
