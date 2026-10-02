"""Offline tests for sending_health - fake DNS only.

Run: python -m unittest scripts/test_sending_health.py
"""

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import sending_health as sh

GOOD = {
    ("scalar.co.uk", "MX"): ["1 smtp.google.com"],
    ("scalar.co.uk", "TXT"): ["v=spf1 include:_spf.google.com ~all", "google-site-verification=x"],
    ("google._domainkey.scalar.co.uk", "TXT"): ["v=DKIM1; k=rsa; p=MIIBIj"],
    ("_dmarc.scalar.co.uk", "TXT"): ["v=DMARC1; p=none; rua=mailto:a@scalar.co.uk"],
}


def fake(records):
    def ask(name, rtype):
        return records.get((name, rtype), [])
    return ask


def levels(items):
    return [lvl for lvl, _ in items]


class MailDomain(unittest.TestCase):
    def test_a_well_set_up_domain_is_all_ok(self):
        out = sh.check_mail_domain("scalar.co.uk", fake(GOOD))
        self.assertEqual(levels(out), ["ok", "ok", "ok", "ok"])
        self.assertIn("p=none", out[3][1])

    def test_each_missing_or_broken_record_is_named(self):
        broken = {("scalar.co.uk", "MX"): ["1 smtp.google.com"],
                  ("scalar.co.uk", "TXT"): ["v=spf1 include:x ~all", "v=spf1 +all"]}
        out = dict((t.split(" ")[0], lvl) for lvl, t in sh.check_mail_domain("scalar.co.uk", fake(broken)))
        texts = " ".join(t for _, t in sh.check_mail_domain("scalar.co.uk", fake(broken)))
        self.assertIn("2 SPF records", texts)
        self.assertIn("No DKIM", texts)
        self.assertIn("No DMARC", texts)
        self.assertIn("bad", out.values())
        plus = {**GOOD, ("scalar.co.uk", "TXT"): ["v=spf1 +all"]}
        self.assertIn("+all", sh.check_mail_domain("scalar.co.uk", fake(plus))[1][1])
        no_google = {**GOOD, ("scalar.co.uk", "TXT"): ["v=spf1 include:mailgun.org ~all"]}
        self.assertEqual(sh.check_mail_domain("scalar.co.uk", fake(no_google))[1][0], "warn")
        self.assertEqual(sh.check_mail_domain("scalar.co.uk", fake({}))[0][0], "bad")  # no MX at all

    def test_a_dns_failure_is_never_reported_as_a_broken_domain(self):
        def down(name, rtype):
            raise OSError("no internet")
        out = sh.check_mail_domain("scalar.co.uk", down)
        self.assertEqual(levels(out), ["unknown"])

        calls = []

        def flaky(name, rtype):
            calls.append(name)
            if len(calls) > 2:
                raise OSError("dropped")
            return GOOD.get((name, rtype), [])
        self.assertEqual(levels(sh.check_mail_domain("scalar.co.uk", flaky)), ["unknown"])


class Blocklists(unittest.TestCase):
    def resolver(self, listed=(), refuse=()):
        tests = {"dbltest.com.dbl.spamhaus.org": ["127.0.1.2"], "test.surbl.org.multi.surbl.org": ["127.0.0.2"],
                 "test.uribl.com.multi.uribl.com": ["127.0.0.2"]}

        def resolve(name):
            if any(z in name for z in refuse):
                return ["127.255.255.254"] if "spamhaus" in name else ["127.0.0.1"]
            if name in tests:
                return tests[name]
            return ["127.0.1.2"] if any(name.startswith(d + ".") for d in listed) else []
        return resolve

    def test_clean_domain(self):
        out = sh.check_blocklists("scalar.co.uk", self.resolver())
        self.assertEqual(out, [("ok", "scalar.co.uk: not on Spamhaus, SURBL, URIBL")])

    def test_a_listing_is_bad(self):
        out = sh.check_blocklists("scalar.co.uk", self.resolver(listed=["scalar.co.uk"]))
        self.assertEqual(levels(out), ["bad", "bad", "bad"])
        self.assertIn("Spamhaus blocklist", out[0][1])

    def test_a_list_that_refuses_us_is_not_a_clean_bill(self):
        out = sh.check_blocklists("scalar.co.uk", self.resolver(refuse=["spamhaus"]))
        self.assertEqual(out, [("ok", "scalar.co.uk: not on SURBL, URIBL")])
        silent = sh.check_blocklists("scalar.co.uk", lambda name: [])  # test entries didn't answer either
        self.assertIn("didn't answer", silent[0][1])


class RunAndStop(unittest.TestCase):
    ENV = {"MAIL_ADDRESS": "ash@scalar.co.uk", "MAIL_APP_PASSWORD": "x",
           "MAIL_EXTRA_1_ADDRESS": "me@gmail.com", "MAIL_EXTRA_1_PASSWORD": "y", "SITE_URL": "https://www.scalardigital.co.uk"}

    def test_checks_own_domains_fully_and_the_website_for_blocklists(self):
        self.assertEqual(sh.domains_to_check(self.ENV), (["scalar.co.uk"], ["scalardigital.co.uk"]))
        out = sh.run(self.ENV, fake(GOOD), resolve=lambda name: [])
        self.assertEqual(set(out["domains"]), {"scalar.co.uk", "scalardigital.co.uk"})
        self.assertEqual(out["problems"], [])

    def test_only_a_recent_blocklisting_stops_sending(self):
        d = Path(tempfile.mkdtemp())
        self.assertEqual(sh.stop_sending(d), "")
        now = datetime(2026, 10, 2, 9, 0)
        state = {"checked_at": (now - timedelta(hours=3)).isoformat(timespec="minutes"),
                 "problems": ["scalar.co.uk: no DMARC"], "warnings": [], "blocked": []}
        (d / sh.FILE).write_text(json.dumps(state))
        self.assertEqual(sh.stop_sending(d, now), "")  # a missing record warns, it doesn't stop you
        state["blocked"] = ["scalar.co.uk: scalar.co.uk is on the Spamhaus blocklist"]
        (d / sh.FILE).write_text(json.dumps(state))
        self.assertIn("Sending is paused", sh.stop_sending(d, now))
        self.assertEqual(sh.stop_sending(d, now + timedelta(days=3)), "")  # stale: check again instead

    def test_only_new_problems_are_texted(self):
        before = {"problems": ["a"], "warnings": ["b"]}
        self.assertEqual(sh.new_problems(before, {"problems": ["a", "c"], "warnings": ["b"]}), ["c"])
        self.assertEqual(sh.new_problems(before, before), [])


if __name__ == "__main__":
    unittest.main()


class SlowDns(unittest.TestCase):
    def test_a_hanging_resolver_counts_as_no_answer_not_a_stuck_run(self):
        import time
        from unittest import mock

        with mock.patch.object(sh, "DNS_TIMEOUT_S", 0.2), mock.patch("socket.gethostbyname_ex", lambda n: time.sleep(2)):
            started = time.monotonic()
            self.assertIsNone(sh.listed("scalar.co.uk", "dbl.spamhaus.org", "dbltest.com"))
            self.assertLess(time.monotonic() - started, 1.5)
