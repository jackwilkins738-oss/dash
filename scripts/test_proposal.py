"""Offline tests for Scalar's terms of business (terms.py) and the printable proposal (proposal.py)."""

import csv
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import proposal
import terms

URL = "https://admin.scalardigital.co.uk/quote/q1/tok"


def facts(**over) -> dict:
    f = {"business": "Kerr & Sons <Roofing>", "contact": "Bill Kerr", "website": "kerr.co.uk", "trade": "Roofing",
         "area": "Guildford", "before": {"mobile_score": "34", "lcp_s": "7.9", "top_issue": "No way to call you in one tap"},
         "package": "build", "founding": False, "quote_number": "SD-0007", "total_pence": 250000, "vat_rate": 0,
         "deposit_percent": 50, "quote_url": URL, "expires": "30 October 2026", "from_name": "Jack",
         "from_email": "hello@scalardigital.co.uk", "from_phone": ""}
    f.update(over)
    return f


class Terms(unittest.TestCase):
    def test_fit_what_the_dashboard_stores(self):
        for package in ("build", "landing"):
            for deposit in (0, 50, 100):
                self.assertLess(len(terms.terms(package, deposit, 20, True)), 10_000)
                self.assertLess(len(terms.payment_terms(deposit)), 500)
        self.assertLess(len(terms.EXCLUSIONS), 2000)

    def test_keep_the_websites_promises(self):
        build, landing = terms.terms("build", 50), terms.terms("landing", 50)
        self.assertIn("For 30 days after launch", build)
        self.assertIn("For 14 days after launch", landing)
        self.assertIn("free for your first 12 months", build)
        self.assertIn(f"£{terms.DASHBOARD_MONTHLY} a month", build)
        self.assertNotIn("dashboard", landing.lower())  # a landing page comes with no dashboard to promise
        for t in (build, landing):
            self.assertIn("The price is fixed", t)
            self.assertIn("your domain is registered in your name", t)

    def test_payment_follows_the_deposit_setting(self):
        self.assertIn("A 50% deposit is due when you accept", terms.terms("build", 50))
        self.assertIn("Nothing is due until your site is ready", terms.terms("build", 0))
        self.assertIn("full price on acceptance", terms.terms("build", 100))
        self.assertIn("Includes VAT at 20%".lower(), terms.terms("build", 0, 20).lower())

    def test_founding_is_the_build_only_and_says_what_its_for(self):
        founding = terms.terms("build", 50, founding=True)
        self.assertIn("free for your first 24 months", founding)
        self.assertIn("the balance isn't due", founding)
        self.assertIn("case study", founding)
        self.assertNotIn("case study", terms.terms("landing", 50, founding=True))
        self.assertEqual(terms.included("landing", True), terms.INCLUDED["landing"])

    def test_the_included_lists_match_the_pricing_section(self):
        pricing = (Path(__file__).resolve().parent.parent / "components" / "pricing.tsx").read_text(encoding="utf-8")
        for line in ("You own the code and the domain outright", "30 days of support after launch", "14 days of support after launch",
                     "Five hand-coded pages, including a gallery and a service-areas page", "WhatsApp, call and enquiry routing built in"):
            self.assertIn(line, pricing)


class Render(unittest.TestCase):
    def test_everything_typed_is_escaped(self):
        page = proposal.render(facts(quote_url='https://x/"><script>alert(1)</script>'))
        self.assertNotIn("<Roofing>", page)
        self.assertIn("Kerr &amp; Sons &lt;Roofing&gt;", page)
        self.assertNotIn("<script>alert(1)", page)

    def test_the_numbers_add_up(self):
        page = proposal.render(facts())
        self.assertIn("£2,500", page)
        self.assertIn("Deposit on acceptance (50%)</td><td>£1,250", page)
        self.assertIn("Balance when your site is ready to go live</td><td>£1,250", page)
        self.assertIn(URL, page)

    def test_says_only_what_was_measured(self):
        page = proposal.render(facts())
        self.assertIn("kerr.co.uk scores 34/100", page)
        self.assertIn("7.9 seconds", page)
        self.assertIn("no way to call you in one tap", page)
        quiet = proposal.render(facts(before={}))
        self.assertNotIn("Where you are now", quiet)
        self.assertNotIn("/100", quiet)
        none = proposal.render(facts(website="", before={}))
        self.assertIn("You don&#x27;t have a website yet, so people searching for roofing in Guildford", none)

    def test_carries_the_same_terms_as_the_quote(self):
        page = proposal.render(facts(founding=True))
        self.assertIn("founding client", page)
        self.assertIn("free for your first 24 months", page)
        self.assertIn("terms of business (" + terms.VERSION, page)


class Panel(unittest.TestCase):
    def setUp(self):
        import control_panel as cp

        self.cp = cp
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        (self.d / "panel.env").write_text("PROSPECTS_API_SECRET=" + "x" * 40 + "\nQUOTE_DEPOSIT_PERCENT=50\n", encoding="utf-8")
        with (self.d / "teardown-log.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["website", "mobile_score", "lcp_s", "top_issue"])
            w.writerow(["kerr.co.uk", "41", "6.2", "the phone number isn't tappable"])

    def tearDown(self):
        self.tmp.cleanup()

    def quote(self, **body):
        import quotes

        made = {}

        def fake(settings, business, email, phone, package, slug=None, note="", founding=False):
            made["founding"] = founding
            return {"quote_number": "SD-0009", "total_pence": 250000, "quote_url": URL}

        with mock.patch.object(self.cp, "OUTREACH", self.d), mock.patch.object(self.cp, "SETTINGS_FILE", self.d / "panel.env"), \
                mock.patch.object(quotes, "create_quote", fake), mock.patch.object(self.cp, "open_folder") as opened:
            out, code = self.cp.quote_action({"sheet": "s.xlsx", "key": "name:kerr roofing", "business": "Kerr Roofing",
                                              "website": "kerr.co.uk", "contact": "Bill Kerr", "package": "build", **body})
            opened_out = self.cp.proposal_open_action({"key": "name:kerr roofing", "quote_number": "SD-0009"})
        return out, code, made, opened_out, opened

    def test_a_quote_comes_with_its_proposal(self):
        (self.d / "s.xlsx").touch()
        with mock.patch.object(self.cp, "sheet_path", lambda s: self.d / s):
            out, code, made, (opened, open_code), opener = self.quote(founding=True)
        self.assertEqual((code, out["proposal"], made["founding"]), (200, True, True))
        page = (self.d / "sites" / "kerr-roofing" / "proposal-sd-0009.html").read_text(encoding="utf-8")
        self.assertIn("scores 41/100", page)
        self.assertIn("Prepared for Bill Kerr", page)
        self.assertIn("Deposit on acceptance (50%)", page)
        self.assertEqual(open_code, 200)
        opener.assert_called_once()

    def test_founding_is_ignored_on_a_landing_page(self):
        (self.d / "s.xlsx").touch()
        with mock.patch.object(self.cp, "sheet_path", lambda s: self.d / s):
            _, code, made, _, _ = self.quote(package="landing", founding=True)
        self.assertEqual((code, made["founding"]), (200, False))

    def test_open_needs_a_quote_that_was_made(self):
        with mock.patch.object(self.cp, "OUTREACH", self.d):
            self.assertEqual(self.cp.proposal_open_action({"key": "name:nobody", "quote_number": "SD-1"})[1], 404)
            self.assertEqual(self.cp.proposal_open_action({"key": "../x", "quote_number": "SD-1"})[1], 404)


if __name__ == "__main__":
    unittest.main()
