import csv
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import email_batches as eb
import saved_replies
import send_email


def write(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


class SavedReplies(unittest.TestCase):
    def test_the_originals_parse_and_are_valid(self):
        replies = saved_replies.parse(saved_replies.DEFAULT)
        self.assertEqual(list(replies), ["How much?", "How does it work?", "Call me / tell me more", "Not right now", "Already sorted"])
        self.assertEqual(saved_replies.problem(saved_replies.DEFAULT), "")

    def test_bad_blocks_are_refused(self):
        self.assertIn("===", saved_replies.problem("just some text"))
        self.assertIn("{{phone}}", saved_replies.problem("=== A ===\nCall {{phone}}"))

    def test_fills_in_and_drops_the_booking_line_without_a_link(self):
        body = "Hi {{greeting_name}},\n\nPick a time: {{booking_link}}\nOr reply.\n\n\n{{your_name}}"
        values = {"greeting_name": "Sam", "your_name": "Jack", "booking_link": ""}
        self.assertEqual(saved_replies.render(body, values), "Hi Sam,\n\nOr reply.\n\nJack\n")
        values["booking_link"] = "https://cal.com/jack/10min"
        self.assertIn("Pick a time: https://cal.com/jack/10min", saved_replies.render(body, values))

    def test_greets_by_first_name_only_when_there_is_one(self):
        self.assertEqual(saved_replies.first_name("SAM KERR"), "Sam")
        self.assertEqual(saved_replies.first_name("Mr J Smith"), "there")
        self.assertEqual(saved_replies.first_name(""), "there")
        self.assertEqual(saved_replies.first_name("McKenzie Ross"), "McKenzie")

    def test_save_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.assertEqual(saved_replies.load(d), saved_replies.DEFAULT)
            self.assertEqual(saved_replies.save(d, "=== Short ===\nThanks, {{greeting_name}}."), "")
            self.assertEqual(saved_replies.parse(saved_replies.load(d)), {"Short": "Thanks, {{greeting_name}}."})


class BookingLinkInEmails(unittest.TestCase):
    def test_booking_line_only_appears_with_a_link(self):
        text = "Hi {{greeting_name}},\nBook here: {{booking_link}}\nThanks"
        with mock.patch.dict(os.environ, {"BOOKING_LINK": ""}):
            self.assertEqual(send_email.render(text, {"greeting_name": "Sam"}, "Jack"), "Hi Sam,\nThanks\n")
        with mock.patch.dict(os.environ, {"BOOKING_LINK": "https://cal.com/jack"}):
            self.assertIn("Book here: https://cal.com/jack", send_email.render(text, {"greeting_name": "Sam"}, "Jack"))
        self.assertIn("booking_link", send_email.FIELDS)


class BounceGuard(unittest.TestCase):
    def setup(self, d: Path, sent: int, bounced: int, when: str = "2026-09-25") -> None:
        write(d / eb.SENT, eb.SENT_FIELDS, [[f"f{i}@x.co.uk", f"F{i}", "", "b", when, ""] for i in range(sent)])
        write(d / "email-checks.csv", ["email", "result", "checked_at"], [[f"f{i}@x.co.uk", "bounced", ""] for i in range(bounced)])

    def test_pauses_over_three_percent(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.setup(d, 100, 3)
            self.assertEqual(send_email.bounce_problem(d, date(2026, 9, 29)), "")
            self.setup(d, 100, 4)
            self.assertIn("4 of the 100", send_email.bounce_problem(d, date(2026, 9, 29)))

    def test_ignores_small_numbers_and_old_sends(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.setup(d, 10, 3)  # too few to judge
            self.assertEqual(send_email.bounce_problem(d, date(2026, 9, 29)), "")
            self.setup(d, 100, 20, when="2026-08-01")  # aged out of the 14 days
            self.assertEqual(send_email.bounce_problem(d, date(2026, 9, 29)), "")

    def test_refuses_to_send_a_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self.setup(d, 50, 10)
            with mock.patch.dict(os.environ, {"MAIL_FROM_NAME": "Jack"}):
                with self.assertRaises(send_email.SendStopped) as stop:
                    send_email.send_batch(d, today=date(2026, 9, 29), out=lambda *_: None)
            self.assertIn("Sending paused", str(stop.exception))


class ViewerFollowUps(unittest.TestCase):
    def test_a_called_viewer_never_gets_the_email(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            write(d / eb.SENT, eb.SENT_FIELDS, [["a@x.co.uk", "Alpha", "https://s/for/alpha-1?src=email", "b", "2026-09-01", ""],
                                                ["b@x.co.uk", "Beta", "https://s/for/beta-1?src=email", "b", "2026-09-01", ""]])
            write(d / "calls.csv", ["key", "sheet", "business", "outcome", "note", "at"], [["k", "s", "Alpha", "No answer", "", ""]])
            views = {"alpha-1": {"view_count": 2}, "beta-1": {"view_count": 1}}
            rows, skipped = eb.followup_candidates(d, 5, date(2026, 9, 29), views)
            self.assertEqual([r["email"] for r in rows], ["b@x.co.uk"])
            self.assertEqual(skipped["viewed"], 1)


if __name__ == "__main__":
    unittest.main()
