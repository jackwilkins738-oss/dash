"""send_email.py: sends the waiting batch once, records as it goes, and never emails someone who said no."""

import csv
import os
import smtplib
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import email_batches as eb
import send_email as se

TODAY = date(2026, 9, 28)


def write(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def read(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


class FakeSMTP:
    def __init__(self, fail_on: int | None = None, refuse: set[str] = frozenset()):
        self.sent, self.fail_on, self.refuse = [], fail_on, refuse

    def send_message(self, msg):
        if msg["To"] in self.refuse:
            raise smtplib.SMTPRecipientsRefused({msg["To"]: (550, b"no such user")})
        if self.fail_on is not None and len(self.sent) == self.fail_on:
            raise KeyboardInterrupt  # the panel's Stop button, mid-batch
        self.sent.append(msg)

    def quit(self):
        pass


FIRMS = [
    {"business": "Kerr Roofing", "greeting_name": "Bill", "email": "bill@kerr.co.uk", "preview_url": "https://s.co/for/kerr-1",
     "score_line": "It scored 41 out of 100.", "issue_line": ""},
    {"business": "Acme Drives", "greeting_name": "there", "email": "info@acme.co.uk", "preview_url": "https://s.co/for/acme-2",
     "score_line": "", "issue_line": "There's no tap-to-call button."},
    {"business": "Oak Lofts", "greeting_name": "Sue", "email": "sue@oak.co.uk", "preview_url": "https://s.co/for/oak-3",
     "score_line": "", "issue_line": ""},
]


class SendEmail(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        write(self.out / "mailmeteor-batch-2026-09-28.csv", list(FIRMS[0]), FIRMS)
        write(self.out / eb.PENDING, ["email", "business", "preview_url", "batch"],
              [{"email": f["email"], "business": f["business"], "preview_url": f["preview_url"], "batch": "mailmeteor-batch-2026-09-28.csv"}
               for f in FIRMS])
        self.env = mock.patch.dict(os.environ, {"MAIL_ADDRESS": "jack@scalar.co.uk", "MAIL_APP_PASSWORD": "abcd efgh",
                                                "MAIL_FROM_NAME": "Jack Wilkins"})
        self.env.start()
        self.sleeps = []

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def send(self, smtp, **kw):
        return se.send_batch(self.out, smtp=smtp, sleep=self.sleeps.append, today=TODAY, out=lambda s: None, **kw)

    def test_sends_each_once_records_each_and_clears_the_batch(self):
        smtp = FakeSMTP()
        self.assertEqual(self.send(smtp), 3)
        self.assertEqual([m["To"] for m in smtp.sent], [f["email"] for f in FIRMS])
        first = smtp.sent[0]
        self.assertEqual(first["Subject"], "A quick look at Kerr Roofing's website")
        self.assertEqual(first["From"], "Jack Wilkins <jack@scalar.co.uk>")
        self.assertIn("mailto:jack@scalar.co.uk?subject=unsubscribe", first["List-Unsubscribe"])
        body = first.get_content()
        self.assertIn("Hi Bill,", body)
        self.assertIn("speed test. It scored 41 out of 100.\n", body)  # empty issue_line leaves no stray space
        self.assertIn("https://s.co/for/kerr-1", body)
        self.assertIn("Kind regards,\nJack Wilkins", body)
        self.assertNotIn("{{", body)
        self.assertEqual(len(self.sleeps), 2)
        self.assertTrue(all(40 <= s <= 90 for s in self.sleeps))
        rows = read(self.out / eb.SENT)
        self.assertEqual([r["sent"] for r in rows], ["2026-09-28"] * 3)
        self.assertEqual(rows[0]["message_id"], first["Message-ID"])
        self.assertFalse((self.out / eb.PENDING).exists())
        with self.assertRaises(se.SendStopped):  # nothing waiting now
            self.send(FakeSMTP())

    def test_stopping_half_way_then_pressing_send_again_never_repeats_anyone(self):
        with self.assertRaises(KeyboardInterrupt):
            self.send(FakeSMTP(fail_on=1))
        self.assertEqual([r["email"] for r in read(self.out / eb.SENT)], ["bill@kerr.co.uk"])
        smtp = FakeSMTP()
        self.assertEqual(self.send(smtp), 2)
        self.assertEqual([m["To"] for m in smtp.sent], ["info@acme.co.uk", "sue@oak.co.uk"])

    def test_someone_who_said_no_or_replied_since_the_batch_was_made_is_left_out(self):
        write(self.out / "do-not-contact.csv", ["kind", "value", "reason"], [{"kind": "email", "value": "info@acme.co.uk", "reason": "not interested"}])
        write(self.out / "replies.csv", ["from", "business", "kind"], [{"from": "sue@gmail.com", "business": "Oak Lofts", "kind": "interested"}])
        smtp = FakeSMTP()
        self.assertEqual(self.send(smtp), 1)
        self.assertEqual([m["To"] for m in smtp.sent], ["bill@kerr.co.uk"])
        self.assertFalse((self.out / eb.PENDING).exists())  # nobody left waiting

    def test_a_test_goes_only_to_you_and_records_nothing(self):
        smtp = FakeSMTP()
        self.assertEqual(self.send(smtp, test=True), 1)
        self.assertEqual(smtp.sent[0]["To"], "jack@scalar.co.uk")
        self.assertIn("would go to bill@kerr.co.uk", smtp.sent[0]["Subject"])
        self.assertFalse((self.out / eb.SENT).exists())
        self.assertTrue((self.out / eb.PENDING).exists())

    def test_followup_replies_in_the_same_thread(self):
        self.send(FakeSMTP())
        first_id = read(self.out / eb.SENT)[0]["message_id"]
        write(self.out / "mailmeteor-followup-2026-10-05.csv", list(FIRMS[0]), FIRMS[:1])
        write(self.out / eb.FOLLOWUP_PENDING, ["email", "batch"], [{"email": "bill@kerr.co.uk", "batch": "mailmeteor-followup-2026-10-05.csv"}])
        smtp = FakeSMTP()
        self.assertEqual(se.send_batch(self.out, followups=True, smtp=smtp, sleep=self.sleeps.append, today=date(2026, 10, 5), out=lambda s: None), 1)
        msg = smtp.sent[0]
        self.assertEqual(msg["Subject"], "Re: A quick look at Kerr Roofing's website")
        self.assertEqual(msg["In-Reply-To"], first_id)
        self.assertIn("Just following up", msg.get_content())
        self.assertEqual(read(self.out / eb.SENT)[0]["followup_sent"], "2026-10-05")

    def test_a_refused_address_is_marked_bounced_and_the_rest_still_go(self):
        smtp = FakeSMTP(refuse={"info@acme.co.uk"})
        self.assertEqual(self.send(smtp), 2)
        self.assertEqual(eb.do_not_email(self.out)["info@acme.co.uk"], "bounced")

    def test_daily_cap(self):
        write(self.out / eb.SENT, eb.SENT_FIELDS, [{"email": f"x{i}@y.co.uk", "sent": "2026-09-28"} for i in range(se.DAILY_CAP - 1)])
        smtp = FakeSMTP()
        self.assertEqual(self.send(smtp), 1)
        with self.assertRaises(se.SendStopped):
            self.send(FakeSMTP())

    def test_needs_your_name_and_sound_templates(self):
        with mock.patch.dict(os.environ, {"MAIL_FROM_NAME": ""}):
            with self.assertRaises(se.SendStopped):
                self.send(FakeSMTP())
        t = dict(se.DEFAULT_TEMPLATES)
        self.assertEqual(se.template_problem(t), "")
        self.assertIn("isn't a field", se.save_templates(self.out, {**t, "first_subject": "Hi {{firstname}}"}))
        self.assertIn("[your name]", se.save_templates(self.out, {**t, "first_body": t["first_body"] + "\n[your name]"}))
        self.assertIn("preview_url", se.save_templates(self.out, {**t, "followup_body": "Hello {{business}}"}))
        self.assertEqual(se.save_templates(self.out, {**t, "first_subject": "Your site, {{business}}"}), "")
        self.assertEqual(se.load_templates(self.out)["first_subject"], "Your site, {{business}}")


if __name__ == "__main__":
    unittest.main()
