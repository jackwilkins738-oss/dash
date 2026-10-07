"""email_batches: neediest firms first - slow sites, then busy firms on Google.

Run: python -m unittest scripts/test_batch_order.py
"""

import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import email_batches as eb


class Order(unittest.TestCase):
    def test_slow_and_busy_go_first(self):
        d = Path(tempfile.mkdtemp())
        with (d / "mailmeteor-old.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["business", "email", "mobile_score", "preview_url"])  # an older list: no website column
            w.writerow(["Fast", "a@fast.co.uk", "92", "https://s/for/fast-1"])
            w.writerow(["Unknown", "a@unknown.co.uk", "", "https://s/for/unknown-1"])
        with (d / "mailmeteor-new.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["business", "email", "mobile_score", "preview_url", "website"])
            w.writerow(["Slow Quiet", "a@quiet.co.uk", "30", "https://s/for/quiet-1", "quiet.co.uk"])
            w.writerow(["Slow Busy", "a@busy.co.uk", "35", "https://s/for/busy-1", "busy.co.uk"])
        (d / "google-ratings.json").write_text(json.dumps({"busy.co.uk": {"google": {"rating": 4.8, "reviews": 60}}}))
        path, _ = eb.make_batch(d, 3, check=lambda u: None, today=date(2026, 10, 7))
        with path.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([r["business"] for r in rows], ["Slow Busy", "Slow Quiet", "Unknown"])
        self.assertIn("website", rows[0])


if __name__ == "__main__":
    unittest.main()
