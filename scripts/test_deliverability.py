"""Offline tests: every batch is address-checked before it can bounce, and a bad domain shows on Today."""

import csv
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

import email_batches as eb

TODAY = date(2026, 10, 1)


def write(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


class BatchChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        write(self.d / "mailmeteor-list.csv", [
            {"business": "Good Roofing", "email": "info@good.co.uk", "preview_url": "https://s/for/good-1"},
            {"business": "Dead Roofing", "email": "info@dead-domain.co.uk", "preview_url": "https://s/for/dead-1"},
            {"business": "Typo Roofing", "email": "bob@gmial.com", "preview_url": "https://s/for/typo-1"},
        ])
        self.calls = []

        def verify(email, cache):
            self.calls.append(email)
            return {"info@good.co.uk": "ok", "info@dead-domain.co.uk": "no-mail-server", "bob@gmial.com": "typo"}[email]

        self.verify = verify

    def tearDown(self):
        self.tmp.cleanup()

    def batch(self, verify=None):
        path, notes = eb.make_batch(self.d, 20, check=lambda u: None, today=TODAY, verify=verify or self.verify)
        with path.open(encoding="utf-8") as f:
            return [r["business"] for r in csv.DictReader(f)], notes

    def test_only_addresses_that_can_take_mail(self):
        names, notes = self.batch()
        self.assertEqual(names, ["Good Roofing"])
        self.assertTrue(any("can't take mail (no-mail-server)" in n for n in notes))
        self.assertTrue(any("typo" in n for n in notes))

    def test_results_are_saved_so_the_rest_of_the_pipeline_sends_a_letter(self):
        self.batch()
        with (self.d / "email-checks.csv").open(encoding="utf-8") as f:
            saved = {r["email"]: r["result"] for r in csv.DictReader(f)}
        self.assertEqual(saved["info@dead-domain.co.uk"], "no-mail-server")
        self.assertEqual(saved["info@good.co.uk"], "ok")

    def test_a_recent_check_isnt_repeated_but_an_old_one_is(self):
        recent = datetime.now(timezone.utc).isoformat()
        old = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
        write(self.d / "email-checks.csv", [{"email": "info@good.co.uk", "result": "ok", "checked_at": recent},
                                            {"email": "bob@gmial.com", "result": "ok", "checked_at": old}])
        eb.make_batch(self.d, 20, check=lambda u: None, today=date.today(), verify=self.verify)
        self.assertNotIn("info@good.co.uk", self.calls)
        self.assertIn("bob@gmial.com", self.calls)

    def test_a_dns_hiccup_doesnt_condemn_an_address(self):
        names, _ = self.batch(verify=lambda e, c: "unknown")
        self.assertEqual(len(names), 3)  # "unknown" isn't bad - and isn't saved, so it's checked again next time
        self.assertFalse((self.d / "email-checks.csv").exists())


class TodayWarnings(unittest.TestCase):
    def test_only_real_warnings_reach_today(self):
        import control_panel as cp

        lines = ["By sending domain:", "  a.co.uk: 100 sent · 6% bounced (6) · 5% replied (5) - STOP sending from it: clean the list",
                 "  b.co.uk: 100 sent · 0% bounced (0) · 5% replied (5)"]
        with mock.patch("scorecard.domains", return_value=lines), mock.patch("scorecard.gather", return_value=[]), \
                mock.patch.object(cp, "OUTREACH", Path(tempfile.gettempdir())):
            self.assertEqual(cp._domain_warnings(), [lines[1].strip()])

    def test_a_broken_file_never_breaks_today(self):
        import control_panel as cp

        with mock.patch("scorecard.gather", side_effect=ValueError("bad csv")), mock.patch.object(cp, "OUTREACH", Path(tempfile.gettempdir())):
            self.assertEqual(cp._domain_warnings(), [])


if __name__ == "__main__":
    unittest.main()
