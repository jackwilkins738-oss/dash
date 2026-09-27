"""Offline tests for company_lookup - no network. Run: python -m unittest scripts/test_company_lookup.py"""

import unittest

from company_lookup import company_number_on_site, normalise, pick_by_name, result_for


class NumberOnSite(unittest.TestCase):
    def test_finds_the_usual_footer_wordings(self):
        self.assertEqual(company_number_on_site("<footer>Company No. 01234567</footer>"), "01234567")
        self.assertEqual(company_number_on_site("<p>Registered in England &amp; Wales No: 1234567</p>"), "01234567")
        self.assertEqual(company_number_on_site("<p>Registered in England and Wales. Company number 9876543.</p>"), "09876543")
        self.assertEqual(company_number_on_site("<p>Company Registration Number: SC123456</p>"), "SC123456")

    def test_ignores_phone_numbers_and_vat(self):
        self.assertIsNone(company_number_on_site("<p>Call 01483 123456 or 07700 900123</p>"))
        self.assertIsNone(company_number_on_site("<p>VAT No. 123456789</p>"))

    def test_two_different_numbers_is_no_answer(self):
        html = "<p>Company No. 01234567</p><p>Company No. 07654321</p>"
        self.assertIsNone(company_number_on_site(html))


class ByName(unittest.TestCase):
    def item(self, title, snippet="1 High St, Guildford, Surrey, GU1 1AA", status="active"):
        return {"title": title, "company_number": "01234567", "company_type": "ltd", "company_status": status, "address_snippet": snippet}

    def test_normalise_ignores_ltd_and_ampersands(self):
        self.assertEqual(normalise("Smith & Sons Roofing Ltd."), normalise("SMITH AND SONS ROOFING LIMITED"))

    def test_a_firm_that_calls_itself_ltd_matches_on_name_alone(self):
        entry, how = pick_by_name("Elite Roofing Ltd", "", [self.item("ELITE ROOFING LIMITED", "Leeds")])
        self.assertIsNotNone(entry)

    def test_a_plain_name_needs_the_area_to_match(self):
        # Could be a sole trader sharing a name with a company elsewhere.
        entry, how = pick_by_name("Elite Roofing", "Surrey", [self.item("ELITE ROOFING LIMITED", "Leeds, LS1 1AA")])
        self.assertIsNone(entry)
        self.assertTrue(how.startswith("unsure"))
        entry, _ = pick_by_name("Elite Roofing", "Surrey", [self.item("ELITE ROOFING LIMITED")])
        self.assertIsNotNone(entry)

    def test_no_same_name_company_is_no_record(self):
        entry, how = pick_by_name("Bob the Roofer", "Surrey", [self.item("BOB SMITH HOLDINGS LIMITED")])
        self.assertIsNone(entry)
        self.assertEqual(how, "no record")

    def test_two_live_companies_with_the_name_is_unsure(self):
        items = [self.item("ACE BUILDERS LTD"), self.item("ACE BUILDERS LIMITED")]
        entry, how = pick_by_name("Ace Builders Ltd", "Surrey", items)
        self.assertIsNone(entry)
        self.assertTrue(how.startswith("unsure"))

    def test_a_dissolved_namesake_does_not_block_the_live_one(self):
        items = [self.item("ACE BUILDERS LTD", status="dissolved"), self.item("ACE BUILDERS LIMITED")]
        entry, _ = pick_by_name("Ace Builders Ltd", "", items)
        self.assertEqual(entry["company_status"], "active")


class Result(unittest.TestCase):
    def test_types_and_statuses(self):
        self.assertEqual(result_for({"type": "ltd", "company_status": "active"}, "x")["company_type"], "Ltd")
        self.assertEqual(result_for({"type": "llp", "company_status": "active"}, "x")["company_type"], "LLP")
        self.assertEqual(result_for({"type": "ltd", "company_status": "dissolved"}, "x")["result"], "closed")
        self.assertEqual(result_for({"type": "limited-partnership", "company_status": "active"}, "x")["result"], "unsure")


if __name__ == "__main__":
    unittest.main()
