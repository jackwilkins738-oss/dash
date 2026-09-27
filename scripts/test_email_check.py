"""Offline tests for email_check - no network. Run: python -m unittest scripts/test_email_check.py"""

import unittest
from unittest import mock

import email_check
from email_check import check, check_format, is_bad


class Format(unittest.TestCase):
    def test_bad_format(self):
        for email in ("bob", "bob@", "bob@roofing", "bob smith@x.com", "bob@@x.com", "bob..x@x.com"):
            self.assertEqual(check_format(email), "bad-format", email)

    def test_typo_domains(self):
        self.assertTrue(check_format("bob@gmial.com").startswith("typo"))
        self.assertTrue(is_bad(check_format("bob@hotmail.co")))

    def test_good_format_needs_a_lookup(self):
        self.assertIsNone(check_format("bob.smith+quotes@smith-roofing.co.uk"))


class Domain(unittest.TestCase):
    def dns(self, answers):
        return lambda name, rtype: answers[rtype]

    def test_mx_records(self):
        with mock.patch.object(email_check, "_dns", self.dns({"MX": {"Status": 0, "Answer": [{"type": 15, "data": "10 mx.example.com."}]}})):
            self.assertEqual(check("a@example.com"), "ok")

    def test_null_mx_means_no_mail(self):
        with mock.patch.object(email_check, "_dns", self.dns({"MX": {"Status": 0, "Answer": [{"type": 15, "data": "0 ."}]}})):
            self.assertEqual(check("a@example.com"), "no-mail-server")

    def test_no_mx_falls_back_to_the_domain_address(self):
        a = {"Status": 0, "Answer": [{"type": 1, "data": "192.0.2.1"}]}
        with mock.patch.object(email_check, "_dns", self.dns({"MX": {"Status": 0}, "A": a})):
            self.assertEqual(check("a@example.com"), "ok")
        with mock.patch.object(email_check, "_dns", self.dns({"MX": {"Status": 0}, "A": {"Status": 0}})):
            self.assertEqual(check("a@example.com"), "no-mail-server")

    def test_dead_domain_and_lookup_failures(self):
        with mock.patch.object(email_check, "_dns", self.dns({"MX": {"Status": 3}})):
            self.assertEqual(check("a@example.com"), "no-domain")
        with mock.patch.object(email_check, "_dns", self.dns({"MX": None})):
            result = check("a@example.com")
            self.assertEqual(result, "unknown")
            self.assertFalse(is_bad(result))

    def test_domain_results_are_cached(self):
        cache = {}
        calls = []

        def dns(name, rtype):
            calls.append(name)
            return {"Status": 0, "Answer": [{"type": 15, "data": "10 mx.example.com."}]}

        with mock.patch.object(email_check, "_dns", dns):
            check("a@example.com", cache)
            check("b@example.com", cache)
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
