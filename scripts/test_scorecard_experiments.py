"""scorecard: the weekly funnel and the experiment board - no winner called on small numbers."""

import tempfile
import unittest
from datetime import date
from pathlib import Path

import email_batches as eb
import scorecard


def row(sent, replied=False, hour=None, score=None, opened=False, **kw):
    return {"email": "x", "business": "x", "sent": sent, "trade": "Roofing", "variant": "-", "inbox": "", "bounced": False,
            "opened": opened, "replied": replied, "keen": kw.get("keen", False), "quoted": kw.get("quoted", False),
            "won": False, "hour": hour, "score": score}


class Funnel(unittest.TestCase):
    def test_each_week_followed_through(self):
        today = date(2026, 10, 3)  # a Saturday; the week starts Monday 28 Sep
        rows = [row(date(2026, 9, 29), opened=True, replied=True, keen=True), row(date(2026, 9, 30), opened=True),
                row(date(2026, 9, 22)), row(date(2026, 8, 1))]
        out = scorecard.funnel(rows, today)
        self.assertEqual(out[1], "  w/c 28 Sep: 2 sent -> 2 opened -> 1 replied -> 1 keen -> 0 quoted -> 0 won")
        self.assertEqual(out[2].split(":")[0], "  w/c 21 Sep")
        self.assertEqual(len(out), 3)  # August is outside the 4 weeks


class Experiments(unittest.TestCase):
    def test_too_few_sends_never_calls_a_winner(self):
        rows = [row(None, hour=7, replied=i < 5) for i in range(20)] + [row(None, hour=14) for _ in range(20)]
        out = scorecard.experiments(rows)
        self.assertIn("Not enough data yet", out[-1])

    def test_a_real_difference_is_called(self):
        rows = [row(None, hour=7, replied=i < 10) for i in range(60)] + [row(None, hour=14, replied=i < 2) for i in range(60)]
        out = scorecard.experiments(rows)
        self.assertIn("  Before 9am is clearly getting more replies.", out)

    def test_close_numbers_are_chance(self):
        rows = [row(None, score=20, replied=i < 6) for i in range(60)] + [row(None, score=80, replied=i < 5) for i in range(60)]
        out = scorecard.experiments(rows)
        self.assertIn("  No clear difference yet - within normal chance.", out)

    def test_one_group_shows_nothing(self):
        self.assertEqual(scorecard.experiments([row(None, hour=7)]), [])


class SentTime(unittest.TestCase):
    def test_send_time_is_recorded(self):
        d = Path(tempfile.mkdtemp())
        eb.record_sent(d, {"email": "a@b.co.uk", "business": "A"}, "batch.csv", date(2026, 10, 3), sent_at="07:42")
        self.assertEqual(eb._rows(d / eb.SENT)[1][0]["sent_at"], "07:42")


if __name__ == "__main__":
    unittest.main()
