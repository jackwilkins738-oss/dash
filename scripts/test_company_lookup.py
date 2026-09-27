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


class SiteSignals(unittest.TestCase):
    def test_owner_names_from_footers(self):
        from company_lookup import owner_names, site_text

        text = site_text("<footer><p>&copy; 2024 J Smith Building Services Ltd. All rights reserved.</p></footer>")
        self.assertEqual(owner_names(text), ["J Smith Building Services"])
        text = site_text("<p>Big Mick Roofing is a trading name of Michael Jones Contractors Limited</p>")
        self.assertEqual(owner_names(text), ["Michael Jones Contractors"])

    def test_web_designer_credits_are_not_the_owner(self):
        from company_lookup import owner_names, site_text

        text = site_text("<p>© 2024 Smith Roofing | Website designed by Pixel Web Design Ltd</p>")
        self.assertEqual(owner_names(text), [])

    def test_scripts_are_not_page_text(self):
        from company_lookup import names_called_ltd, site_text

        text = site_text('<script>var c = "Tracking Co Ltd";</script><p>Smith Roofing Ltd</p>')
        self.assertEqual(names_called_ltd(text), {"smith roofing"})

    def test_postcode_on_site_confirms_and_picks_between_namesakes(self):
        from company_lookup import postcodes

        items = [
            {"title": "ACE BUILDERS LTD", "company_status": "active", "address": {"postal_code": "LS1 1AA"}},
            {"title": "ACE BUILDERS LIMITED", "company_status": "active", "address": {"postal_code": "GU1 4RR"}},
        ]
        entry, how = pick_by_name("Ace Builders", "", items, site_postcodes=postcodes("Visit us at Guildford GU1 4RR"))
        self.assertEqual(entry["address"]["postal_code"], "GU1 4RR")
        self.assertIn("postcode", how)

    def test_site_saying_ltd_confirms_a_single_match(self):
        items = [{"title": "ELITE ROOFING LIMITED", "company_status": "active", "address_snippet": "Leeds"}]
        self.assertIsNone(pick_by_name("Elite Roofing", "Surrey", items)[0])
        self.assertIsNotNone(pick_by_name("Elite Roofing", "Surrey", items, says_ltd=True)[0])


class LookupFlow(unittest.TestCase):
    def test_a_trading_name_is_found_through_the_company_on_its_site(self):
        page = "<footer>© 2025 Mick Jones Contractors Ltd, Guildford</footer>"
        answers = {
            "Big Mick": {"items": []},
            "Mick Jones Contractors": {"items": [{"title": "MICK JONES CONTRACTORS LTD", "company_number": "07654321",
                                                   "company_type": "ltd", "company_status": "active"}]},
        }

        def fake_get(path, key):
            from urllib.parse import parse_qs, urlparse

            return answers[parse_qs(urlparse(path).query)["q"][0]]

        with mock.patch.object(company_lookup, "_get", fake_get):
            found = company_lookup.lookup("Big Mick", "Surrey", page, "k")
        self.assertEqual(found["result"], "company")
        self.assertEqual(found["number"], "07654321")
        self.assertIn("Mick Jones Contractors", found["how"])


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
