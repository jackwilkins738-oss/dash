"""Pay monthly: nothing upfront, 12 payments from launch, then the site is theirs.

Run: python -m unittest scripts/test_pay_monthly.py
"""

import os
import unittest
from unittest import mock

import ai_reply
import quotes
import saved_replies
import send_email as se
import terms
import workspace


class Amounts(unittest.TestCase):
    def test_never_more_than_paying_at_once(self):
        for price, each in ((2500, 208), (750, 62), (4500, 375), (1500, 125)):
            self.assertEqual(workspace.monthly(price), each)
            self.assertLessEqual(each * workspace.MONTHS, price)
        self.assertEqual(workspace.MONTHS, terms.PAY_MONTHLY_MONTHS)


class Terms(unittest.TestCase):
    def test_monthly_terms_say_how_it_works(self):
        t = terms.terms("build", 50, monthly=208)
        for words in ("nothing to pay upfront", "£208 a month for 12 months", "£2,496 in total", "no interest",
                      "under my account", "take the site offline", "Your domain is registered in your name from the start",
                      "pay off what's left"):
            self.assertIn(words.lower(), t.lower())
        self.assertNotIn("deposit is due", t)
        self.assertIn("£208", terms.payment_terms(0, 208))

    def test_one_off_terms_unchanged(self):
        t = terms.terms("build", 50)
        self.assertIn("A 50% deposit is due when you accept", t)
        self.assertNotIn("monthly payment", t)
        self.assertIn("free account in your name", t)


class Quote(unittest.TestCase):
    def test_monthly_quote_totals_the_payments_with_no_deposit(self):
        b = quotes.quote_body({"QUOTE_DEPOSIT_PERCENT": "50"}, "build", founding=True, monthly=True)
        self.assertEqual(b["deposit_percent"], 0)
        self.assertEqual(b["line_items"][0]["unit_price_pence"], 208 * 12 * 100)
        self.assertEqual(b["payment_plan"], {"instalments": 12, "instalment_pence": 20800, "first_due": "at launch"})
        self.assertNotIn("founding", b["line_items"][0]["description"])
        self.assertIn("Nothing upfront", b["payment_terms"])

    def test_one_off_quote_has_no_plan(self):
        b = quotes.quote_body({}, "landing")
        self.assertNotIn("payment_plan", b)
        self.assertEqual(b["line_items"][0]["unit_price_pence"], 75000)


class Proposal(unittest.TestCase):
    def test_monthly_proposal_shows_the_payments_and_no_founding_extras(self):
        import proposal

        html = proposal.render({"business": "Kerr Roofing", "package": "build", "founding": True, "monthly": 208,
                                "quote_number": "Q-1", "total_pence": 249600, "vat_rate": 0, "deposit_percent": 50,
                                "quote_url": "https://example.com/q", "expires": "1 January 2027"})
        self.assertIn("£208", html)
        self.assertNotIn("Deposit on acceptance", html)
        self.assertNotIn("case study", html)


class Outreach(unittest.TestCase):
    def test_first_emails_offer_it(self):
        self.assertIn("12 monthly payments", se.DEFAULT_TEMPLATES["first_body"])
        self.assertIn("12 monthly payments", se.US_DEFAULT_TEMPLATES["first_body"])
        self.assertEqual(se.template_problem(se.DEFAULT_TEMPLATES), "")
        self.assertEqual(se.template_problem(se.US_DEFAULT_TEMPLATES, "us"), "")

    def test_price_reply_and_ai_brief_quote_the_monthly_amounts(self):
        with mock.patch.dict(os.environ, {"OUTREACH_DIR": ""}):
            values = ai_reply.env_values({})
            text = saved_replies.default_for()
        self.assertEqual((values["price_build_monthly"], values["price_landing_monthly"]), ("208", "62"))
        self.assertIn("£{{price_build_monthly}} a month", text)
        self.assertEqual(saved_replies.problem(text), "")
        self.assertIn("£208 (five-page site)", ai_reply.brief({"message": "can I pay monthly?"}, values, ""))
        with mock.patch.dict(os.environ, {"OUTREACH_DIR": "outreach-us"}):
            us_values = ai_reply.env_values({})
            us_text = saved_replies.default_for()
        self.assertEqual(us_values["price_build_monthly"], "375")
        self.assertIn("${{price_build_monthly}} a month", us_text)
        self.assertNotIn("£", us_text)


if __name__ == "__main__":
    unittest.main()
