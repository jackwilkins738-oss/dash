"""Offline tests for ticking off Mailmeteor batches from the Sent folder (a fake inbox, no network)."""

import csv
import os
import tempfile
import time
import unittest
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import email_batches as eb
import mailmeteor_sync as mm


def write(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def header(to: str, day: date) -> bytes:
    return f"To: {to}\r\nDate: {day.strftime('%a, %d %b %Y')} 10:00:00 +0000\r\n\r\n".encode()


class FakeImap:
    """Just enough IMAP: a Sent folder holding the given (to, day) messages. Records if anything wrote."""

    def __init__(self, messages, folder="[Gmail]/Sent Mail"):
        self.messages, self.folder, self.readonly = messages, folder, None

    def login(self, *_):
        return "OK", []

    def list(self):
        return "OK", [b'(\\HasNoChildren) "/" "INBOX"', f'(\\HasNoChildren \\Sent) "/" "{self.folder}"'.encode()]

    def select(self, name, readonly=False):
        self.readonly = readonly
        return ("OK", [b"1"]) if name.strip('"') == self.folder else ("NO", [])

    def search(self, *_):
        return "OK", [" ".join(str(i + 1) for i in range(len(self.messages))).encode()]

    def fetch(self, nums, what):
        assert "PEEK" in what  # headers only, never marks anything read
        return "OK", [(b"x", header(to, day)) for to, day in self.messages]

    def logout(self):
        pass


class MailmeteorSync(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.today = date.today()
        self.inbox = SimpleNamespace(address="me@scalar.co.uk", password="x")

    def tearDown(self):
        self.tmp.cleanup()

    def pending(self, emails, name=eb.PENDING):
        write(self.out / name, ["email", "business", "batch"],
              [{"email": e, "business": e.split("@")[0], "batch": "mailmeteor-batch-x.csv"} for e in emails])

    def sent_log(self):
        return {r["email"]: r for r in eb._rows(self.out / eb.SENT)[1]}

    def run_sync(self, messages):
        fake = FakeImap(messages)
        result = mm.sync(self.out, [self.inbox], connect=lambda: fake)
        return result, fake

    def test_records_what_is_in_sent_and_leaves_the_rest_waiting(self):
        self.pending(["a@x.co.uk", "b@x.co.uk", "c@x.co.uk"])
        (firsts, follows), fake = self.run_sync([("A <a@x.co.uk>", self.today), ("b@x.co.uk", self.today)])
        self.assertEqual((firsts, follows), (2, 0))
        self.assertTrue(fake.readonly)
        log = self.sent_log()
        self.assertEqual(log["a@x.co.uk"]["sent"], self.today.isoformat())
        self.assertEqual(log["a@x.co.uk"]["sent_from"], "me@scalar.co.uk")
        self.assertNotIn("c@x.co.uk", log)
        self.assertEqual([r["email"] for r in eb._rows(self.out / eb.PENDING)[1]], ["c@x.co.uk"])

    def test_whole_batch_found_removes_the_pending_file(self):
        self.pending(["a@x.co.uk"])
        self.run_sync([("a@x.co.uk", self.today)])
        self.assertFalse((self.out / eb.PENDING).exists())

    def test_an_email_from_before_the_batch_is_not_counted(self):
        self.pending(["a@x.co.uk"])
        (firsts, _), _ = self.run_sync([("a@x.co.uk", self.today - timedelta(days=30))])
        self.assertEqual(firsts, 0)
        self.assertTrue((self.out / eb.PENDING).exists())

    def test_followup_needs_a_later_email_than_the_first(self):
        first = self.today - timedelta(days=6)
        write(self.out / eb.SENT, eb.SENT_FIELDS, [{"email": "a@x.co.uk", "sent": first.isoformat()},
                                                   {"email": "b@x.co.uk", "sent": first.isoformat()}])
        self.pending(["a@x.co.uk", "b@x.co.uk"], eb.FOLLOWUP_PENDING)
        # a: only the original first email is in Sent. b: the follow-up went today.
        (firsts, follows), _ = self.run_sync([("a@x.co.uk", first), ("b@x.co.uk", first), ("b@x.co.uk", self.today)])
        self.assertEqual((firsts, follows), (0, 1))
        log = self.sent_log()
        self.assertEqual(log["b@x.co.uk"]["followup_sent"], self.today.isoformat())
        self.assertEqual(log["a@x.co.uk"]["followup_sent"], "")

    def test_already_recorded_is_not_recorded_twice(self):
        write(self.out / eb.SENT, eb.SENT_FIELDS, [{"email": "a@x.co.uk", "sent": self.today.isoformat()}])
        self.pending(["a@x.co.uk"])
        (firsts, _), _ = self.run_sync([("a@x.co.uk", self.today)])
        self.assertEqual(firsts, 0)
        self.assertEqual(len(eb._rows(self.out / eb.SENT)[1]), 1)

    def test_nothing_waiting_means_no_login(self):
        def boom():
            raise AssertionError("should not connect")

        self.assertEqual(mm.sync(self.out, [self.inbox], connect=boom), (0, 0))

    def test_an_untouched_batch_keeps_its_date(self):
        self.pending(["a@x.co.uk"])
        old = time.time() - 3 * 86400
        os.utime(self.out / eb.PENDING, (old, old))
        self.run_sync([])
        self.assertAlmostEqual((self.out / eb.PENDING).stat().st_mtime, old, delta=1)

    def test_a_failed_login_just_waits(self):
        self.pending(["a@x.co.uk"])

        class Refuses(FakeImap):
            def login(self, *_):
                raise OSError("no")

        self.assertEqual(mm.sync(self.out, [self.inbox], connect=lambda: Refuses([])), (0, 0))
        self.assertTrue((self.out / eb.PENDING).exists())

    def test_sent_folder_found_in_another_language(self):
        fake = FakeImap([], folder="[Gmail]/Gesendet")
        self.assertEqual(mm.sent_folder(fake), "[Gmail]/Gesendet")


if __name__ == "__main__":
    unittest.main()
