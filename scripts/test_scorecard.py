"""Offline tests for the outreach scorecard: every win counted once, the money, and letters."""

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

import scorecard as sc


def write(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


class Scorecard(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        sent = [{"email": f"a{i}@x.co.uk", "business": f"Firm {i}", "preview_url": f"https://x/for/firm-{i}", "sent": "2026-09-20",
                 "variant": "A"} for i in range(10)]
        write(self.d / "emails-sent.csv", sent)
        write(self.d / "quotes-sent.csv", [
            {"business": "Firm 1", "total": "750.00"}, {"business": "Firm 1", "total": "2500.00"},  # re-quoted: latest counts
            {"business": "Firm 2", "total": "2500.00"}])
        write(self.d / "calls.csv", [{"key": "k", "business": "Firm 2", "outcome": "Won", "at": "2026-09-25T10:00"}])
        self.views = {"firm-1": {"status": "won", "view_count": 3, "channel": "email"},
                      "firm-2": {"status": "won", "view_count": 1, "channel": "email"},  # won both ways: counted once
                      "letter-a": {"status": "new", "view_count": 1, "channel": "letter"},
                      "letter-b": {"status": "won", "view_count": 2, "channel": "letter"},
                      "letter-c": {"status": "new", "view_count": 0, "channel": "letter"}}

    def tearDown(self):
        self.tmp.cleanup()

    def card(self, views="default"):
        return "\n".join(sc.scorecard(self.d, self.views if views == "default" else views, date(2026, 9, 30)))

    def test_an_online_acceptance_is_a_win_without_a_call(self):
        rows = sc.gather(self.d, self.views)
        self.assertEqual(sorted(r["business"] for r in rows if r["won"]), ["firm 1", "firm 2"])
        self.assertIn("2 won", self.card())

    def test_the_money_and_emails_per_win(self):
        text = self.card()
        self.assertIn("Money: £5,000 quoted to 2 firms, £5,000 won from 2", text)
        self.assertIn("One job won for every 5 emails sent", text)

    def test_letters_are_scored_by_scans(self):
        self.assertIn("Letters: 3 sent · 67% scanned the code (2) · 1 won", self.card())

    def test_without_the_dashboard_only_logged_wins_count(self):
        text = self.card(views=None)
        self.assertIn("1 won", text)
        self.assertIn("£2,500 won from 1", text)
        self.assertNotIn("Letters", text)

    def test_nothing_won_says_so(self):
        write(self.d / "calls.csv", [{"key": "k", "business": "x", "outcome": "Call back", "at": "2026-09-25T10:00"}])
        text = self.card(views={})
        self.assertIn("none won yet", text)
        self.assertNotIn("One job won", text)


class Domains(unittest.TestCase):
    def rows(self, dom, n, replies=0, bounces=0):
        return [{"inbox": f"me@{dom}", "replied": i < replies, "bounced": i < bounces} for i in range(n)]

    def test_each_domain_on_its_own_line(self):
        out = sc.domains(self.rows("scalardigital.co.uk", 120, 6) + self.rows("getscalar.co.uk", 110, 5))
        self.assertEqual(out[0], "By sending domain:")
        self.assertIn("scalardigital.co.uk: 120 sent · 0% bounced (0) · 5% replied (6)", out[1])
        self.assertEqual(len(out), 3)  # nothing to warn about

    def test_bouncing_domain_is_called_out(self):
        out = "\n".join(sc.domains(self.rows("a.co.uk", 100, 5, bounces=6) + self.rows("b.co.uk", 100, 5, bounces=3)))
        self.assertIn("a.co.uk: 100 sent · 6% bounced (6) · 5% replied (5) - STOP sending from it", out)
        self.assertIn("b.co.uk: 100 sent · 3% bounced (3) · 5% replied (5) - bounces are high", out)

    def test_a_domain_far_behind_on_replies_may_be_in_spam(self):
        out = "\n".join(sc.domains(self.rows("good.co.uk", 150, 9) + self.rows("spam.co.uk", 150, 2)))
        self.assertIn("spam.co.uk gets under half the replies of your best domain", out)
        self.assertNotIn("good.co.uk gets under", out)

    def test_too_few_sends_to_judge(self):
        out = "\n".join(sc.domains(self.rows("good.co.uk", 150, 9) + self.rows("new.co.uk", 30, 0)))
        self.assertNotIn("under half", out)

    def test_one_domain_and_no_bounces_says_nothing(self):
        self.assertEqual(sc.domains(self.rows("a.co.uk", 50, 3)), [])


if __name__ == "__main__":
    unittest.main()
