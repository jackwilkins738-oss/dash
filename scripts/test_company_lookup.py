"""Offline tests for company_lookup - no network. Run: python -m unittest scripts/test_company_lookup.py"""

import io
import unittest
import urllib.error
from unittest import mock

import company_lookup
from company_lookup import LookupFailed, clean_key, company_number_on_site, key_problem, normalise, pick_by_name, result_for


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



class Errors(unittest.TestCase):
    def fail_with(self, code, body=b""):
        err = urllib.error.HTTPError("https://x", code, "err", {}, io.BytesIO(body))
        return mock.patch.object(company_lookup.urllib.request, "urlopen", side_effect=err)

    def setUp(self):
        patcher = mock.patch.object(company_lookup.time, "sleep")
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_not_found_is_empty(self):
        with self.fail_with(404):
            self.assertEqual(company_lookup._get("/company/01234567", "k"), {})

    def test_bad_keys_say_what_to_fix(self):
        with self.fail_with(401), self.assertRaisesRegex(PermissionError, "REST key"):
            company_lookup._get("/x", "k")
        with self.fail_with(403, b"IP not allowed"), self.assertRaisesRegex(PermissionError, "IP not allowed"):
            company_lookup._get("/x", "k")

    def test_invalid_authorization_header_is_a_key_problem(self):
        with self.fail_with(400, b'{"error":"Invalid Authorization header"}'):
            with self.assertRaisesRegex(PermissionError, "36"):
                company_lookup._get("/x", "my-application-id")

    def test_other_errors_carry_the_reason(self):
        with self.fail_with(400, b"bad query"), self.assertRaisesRegex(LookupFailed, "HTTP 400 bad query"):
            company_lookup._get("/x", "k")
        err = urllib.error.URLError("CERTIFICATE_VERIFY_FAILED")
        with mock.patch.object(company_lookup.urllib.request, "urlopen", side_effect=err):
            with self.assertRaisesRegex(LookupFailed, "CERTIFICATE_VERIFY_FAILED"):
                company_lookup._get("/x", "k")



class Key(unittest.TestCase):
    KEY = "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"

    def test_cleans_what_copying_brings_along(self):
        for pasted in (f" {self.KEY}\n", f'"{self.KEY}"', f"\u200b{self.KEY}", f"COMPANIES_HOUSE_API_KEY={self.KEY}", f"\u2018{self.KEY}\u2019"):
            self.assertEqual(clean_key(pasted), self.KEY, repr(pasted))
            self.assertIsNone(key_problem(pasted))

    def test_wrong_shape_is_explained_without_the_key(self):
        problem = key_problem("abc123secretvalue")
        self.assertIn("17 characters", problem)
        self.assertNotIn("abc123secretvalue", problem)


if __name__ == "__main__":
    unittest.main()
