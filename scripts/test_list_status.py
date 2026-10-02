"""email_batches.list_status: the Send card says what a list's Mailmeteor file holds, and why anyone isn't in it."""

import csv
import tempfile
import unittest
from pathlib import Path

import email_batches


def write(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


class ListStatus(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())

    def test_not_made_yet(self):
        s = email_batches.list_status(self.d, "lofts-Edinburgh 2026.xlsx")
        self.assertEqual(s["file"], "mailmeteor-lofts-Edinburgh 2026.csv")
        self.assertFalse(s["exists"])

    def test_counts_letters_not_live_and_already_sent(self):
        write(self.d / "preview-links-lofts.csv", ["Business", "Email", "Channel", "Status", "preview_url"], [
            {"Business": "A", "Email": "a@a.co.uk", "Channel": "email"},
            {"Business": "B", "Email": "b@b.co.uk", "Channel": "email"},
            {"Business": "C", "Email": "c@c.co.uk", "Channel": "email"},
            {"Business": "D", "Email": "", "Channel": "letter"},
        ])
        write(self.d / "mailmeteor-lofts.csv", ["business", "email"], [
            {"business": "A", "email": "a@a.co.uk"}, {"business": "B", "email": "B@b.co.uk"}])
        write(self.d / email_batches.SENT, ["email", "sent"], [{"email": "a@a.co.uk", "sent": "2026-10-01"}])
        s = email_batches.list_status(self.d, "lofts.xlsx")
        self.assertEqual((s["in_file"], s["waiting"], s["done"], s["letters"], s["not_live"]), (2, 1, 1, 1, 1))

    def test_master_list_has_no_suffix(self):
        self.assertEqual(email_batches.list_status(self.d, "outreach-master.xlsx")["file"], "mailmeteor.csv")


if __name__ == "__main__":
    unittest.main()
