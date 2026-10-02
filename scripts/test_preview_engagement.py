"""calls.py: preview engagement ranks the call list, and one-tap answers become replies."""

import csv
import tempfile
import unittest
from pathlib import Path

import calls
import send_email


class Interest(unittest.TestCase):
    def test_real_attention_beats_repeat_glances(self):
        glances = {"views": 3, "seconds": 6, "scroll": 10, "reached": []}
        reader = {"views": 1, "seconds": 160, "scroll": 90, "reached": ["rebuilt", "pricing"]}
        self.assertGreater(calls.interest(reader), calls.interest(glances))

    def test_without_engagement_it_is_visits_as_before(self):
        self.assertEqual(calls.interest({"views": 2}), 20)


class SyncChoices(unittest.TestCase):
    def setUp(self):
        self.out = Path(tempfile.mkdtemp())

    def rows(self):
        with (self.out / "replies.csv").open(encoding="utf-8") as f:
            return list(csv.DictReader(f))

    def test_each_answer_becomes_one_reply_and_stops_the_follow_up(self):
        ring = ({"slug": "kerr-1", "choice": "call", "choice_at": "2026-10-02T10:15:00Z"}, "Kerr Roofing", "kerr.co.uk", "Bill@Kerr.co.uk")
        later = ({"slug": "oak-2", "choice": "not_now", "choice_at": "2026-10-02T11:00:00Z"}, "Oak Lofts", "oak.co.uk", "sue@oak.co.uk")
        self.assertEqual(calls.sync_choices(self.out, [ring, later]), 2)
        self.assertEqual(calls.sync_choices(self.out, [ring, later]), 0)  # never twice
        rows = self.rows()
        self.assertEqual([(r["business"], r["kind"], r["intent"]) for r in rows],
                         [("Kerr Roofing", "interested", "call"), ("Oak Lofts", "read it", "later")])
        self.assertEqual(rows[0]["from"], "bill@kerr.co.uk")
        self.assertIn("give me a ring", rows[0]["snippet"])
        self.assertEqual(rows[1]["objection"], "not now")
        # The send check now treats both as having replied - no follow-up email.
        self.assertEqual(send_email._still_ok(self.out, "bill@kerr.co.uk", "Kerr Roofing"), "they've replied")
        self.assertEqual(send_email._still_ok(self.out, "sue@oak.co.uk", "Oak Lofts"), "they've replied")

    def test_keeps_existing_replies(self):
        with (self.out / "replies.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["message_id", "business", "kind"])
            w.writeheader()
            w.writerow({"message_id": "<a@b>", "business": "Earlier Ltd", "kind": "interested"})
        calls.sync_choices(self.out, [({"slug": "x-1", "choice": "whatsapp", "choice_at": ""}, "X Ltd", "x.co.uk", "")])
        self.assertEqual([r["business"] for r in self.rows()], ["Earlier Ltd", "X Ltd"])


if __name__ == "__main__":
    unittest.main()
