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

    def test_minutes_apart_spreads_the_run(self):
        self.assertEqual(self.send(FakeSMTP(), gap_minutes=5), 3)
        self.assertEqual(len(self.sleeps), 2)
        self.assertTrue(all(240 <= s <= 360 for s in self.sleeps), self.sleeps)

    def test_sends_each_once_records_each_and_clears_the_batch(self):
        smtp = FakeSMTP()
        self.assertEqual(self.send(smtp), 3)
        self.assertEqual([m["To"] for m in smtp.sent], [f["email"] for f in FIRMS])
        first = smtp.sent[0]
        self.assertEqual(first["Subject"], "Kerr Roofing - quick look at your website")
        self.assertEqual(first["From"], "Jack Wilkins <jack@scalar.co.uk>")
        self.assertIn("mailto:jack@scalar.co.uk?subject=unsubscribe", first["List-Unsubscribe"])
        body = first.get_content()
        self.assertIn("Hi Bill,", body)
        self.assertIn("on my phone too. It scored 41 out of 100.\n", body)  # empty issue/why lines leave no stray space
        self.assertIn("https://s.co/for/kerr-1", body)
        self.assertIn("Worth a 10-minute chat?\n\nJack Wilkins", body)
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
        self.assertEqual(msg["Subject"], "Re: Kerr Roofing - quick look at your website")
        self.assertEqual(msg["In-Reply-To"], first_id)
        self.assertIn("Just following up", msg.get_content())
        self.assertEqual(read(self.out / eb.SENT)[0]["followup_sent"], "2026-10-05")

    def test_the_closing_email_goes_once_in_the_same_thread(self):
        self.send(FakeSMTP())
        rows = read(self.out / eb.SENT)
        rows[0]["followup_sent"] = "2026-10-05"
        write(self.out / eb.SENT, eb.SENT_FIELDS, rows)
        write(self.out / "mailmeteor-followup-2026-10-14.csv", list(FIRMS[0]), FIRMS[:1])
        write(self.out / eb.FOLLOWUP_PENDING, ["email", "batch", "stage"],
              [{"email": "bill@kerr.co.uk", "batch": "mailmeteor-followup-2026-10-14.csv", "stage": "final"}])
        preview = se.preview_batch(self.out, followups=True, env={"MAIL_FROM_NAME": "Jack"})
        self.assertIn("won't chase again", preview["emails"][0]["body"])
        smtp = FakeSMTP()
        send = lambda: se.send_batch(self.out, followups=True, smtp=smtp, sleep=self.sleeps.append,  # noqa: E731
                                     today=date(2026, 10, 14), out=lambda s: None)
        self.assertEqual(send(), 1)
        msg = smtp.sent[0]
        self.assertEqual(msg["Subject"], "Re: Kerr Roofing - quick look at your website")
        self.assertIn("I won't chase again", msg.get_content())
        self.assertEqual(read(self.out / eb.SENT)[0]["final_sent"], "2026-10-14")
        write(self.out / eb.FOLLOWUP_PENDING, ["email", "batch", "stage"],
              [{"email": "bill@kerr.co.uk", "batch": "mailmeteor-followup-2026-10-14.csv", "stage": "final"}])
        self.assertEqual(send(), 0)  # already sent: never twice
        self.assertEqual(len(smtp.sent), 1)

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


class MultipleInboxes(SendEmail):
    """Extra sending inboxes: sends spread evenly, follow-ups from the first email's inbox, a cap per inbox."""

    def setUp(self):
        super().setUp()
        self.extra = mock.patch.dict(os.environ, {"MAIL_EXTRA_1_ADDRESS": "jack@getscalar.co.uk", "MAIL_EXTRA_1_PASSWORD": "wxyz"})
        self.extra.start()
        self.by_inbox = {}

        def fake_connect(env=None):
            smtp = self.by_inbox.setdefault(env["MAIL_ADDRESS"], FakeSMTP())
            return smtp

        self.connect = mock.patch.object(se, "connect", fake_connect)
        self.connect.start()

    def tearDown(self):
        self.connect.stop()
        self.extra.stop()
        super().tearDown()

    def test_send_from_one_inbox_only(self):
        n = se.send_batch(self.out, sleep=self.sleeps.append, today=TODAY, out=lambda s: None, only_from="Jack@GetScalar.co.uk")
        self.assertEqual(n, 3)
        self.assertEqual(list(self.by_inbox), ["jack@getscalar.co.uk"])
        self.assertTrue(all(r["sent_from"] == "jack@getscalar.co.uk" for r in read(self.out / eb.SENT)))

    def test_gap_per_inbox_inboxes_take_turns_each_keeping_its_own_gap(self):
        clock = [0.0]
        sleeps = []

        def sleep(seconds):
            sleeps.append(seconds)
            clock[0] += seconds

        with mock.patch.object(se.random, "uniform", lambda lo, hi: lo):  # every gap its shortest: a fixed order to check
            n = se.send_batch(self.out, sleep=sleep, today=TODAY, out=lambda s: None, gap_minutes=6, per_inbox=True,
                              clock=lambda: clock[0])
        self.assertEqual(n, 3)
        rows = read(self.out / eb.SENT)
        inboxes = [r["sent_from"] for r in rows]
        self.assertEqual(inboxes[0], inboxes[2])  # the third email goes back to the first inbox...
        self.assertNotEqual(inboxes[0], inboxes[1])  # ...after the other one took its turn
        # 2nd email: only the few seconds kept between any two; 3rd: the first inbox's own gap (6 min, shortest 4.8)
        self.assertEqual(sleeps, [5, 4.8 * 60 - 5])

    def test_send_from_an_unknown_inbox_stops_before_sending(self):
        with self.assertRaises(se.SendStopped):
            se.send_batch(self.out, sleep=self.sleeps.append, today=TODAY, out=lambda s: None, only_from="nobody@example.com")
        self.assertEqual(self.by_inbox, {})

    def test_spread_evenly_recorded_and_followed_up_from_the_same_inbox(self):
        self.assertEqual(se.send_batch(self.out, sleep=self.sleeps.append, today=TODAY, out=lambda s: None), 3)
        froms = {a: [m["To"] for m in smtp.sent] for a, smtp in self.by_inbox.items()}
        self.assertEqual(froms, {"jack@scalar.co.uk": ["bill@kerr.co.uk", "sue@oak.co.uk"], "jack@getscalar.co.uk": ["info@acme.co.uk"]})
        self.assertIn("jack@getscalar.co.uk", self.by_inbox["jack@getscalar.co.uk"].sent[0]["From"])
        rows = {r["email"]: r for r in read(self.out / eb.SENT)}
        self.assertEqual(rows["info@acme.co.uk"]["sent_from"], "jack@getscalar.co.uk")

        # The follow-up to Acme goes from the same extra inbox, in the same thread.
        write(self.out / "mailmeteor-followup-2026-10-05.csv", list(FIRMS[0]), [FIRMS[1]])
        write(self.out / eb.FOLLOWUP_PENDING, ["email", "batch"], [{"email": "info@acme.co.uk", "batch": "mailmeteor-followup-2026-10-05.csv"}])
        before = len(self.by_inbox["jack@getscalar.co.uk"].sent)
        se.send_batch(self.out, followups=True, sleep=self.sleeps.append, today=date(2026, 10, 5), out=lambda s: None)
        follow = self.by_inbox["jack@getscalar.co.uk"].sent[before]
        self.assertEqual(follow["To"], "info@acme.co.uk")
        self.assertEqual(follow["In-Reply-To"], rows["info@acme.co.uk"]["message_id"])

    def test_follow_ups_for_one_inbox_leave_the_others_waiting(self):
        se.send_batch(self.out, sleep=self.sleeps.append, today=TODAY, out=lambda s: None)  # Acme from the extra inbox
        write(self.out / "mailmeteor-followup-2026-10-05.csv", list(FIRMS[0]), FIRMS)
        write(self.out / eb.FOLLOWUP_PENDING, ["email", "batch"],
              [{"email": f["email"], "batch": "mailmeteor-followup-2026-10-05.csv"} for f in FIRMS])
        before = {a: len(c.sent) for a, c in self.by_inbox.items()}
        n = se.send_batch(self.out, followups=True, sleep=self.sleeps.append, today=date(2026, 10, 5), out=lambda s: None,
                          only_from="jack@getscalar.co.uk")
        self.assertEqual(n, 1)
        self.assertEqual(self.by_inbox["jack@getscalar.co.uk"].sent[-1]["To"], "info@acme.co.uk")
        self.assertEqual(len(self.by_inbox["jack@scalar.co.uk"].sent), before["jack@scalar.co.uk"])  # Kerr and Oak wait
        self.assertTrue((self.out / eb.FOLLOWUP_PENDING).exists())

    def test_daily_cap(self):
        # The cap is per inbox: the main inbox has one slot left, the extra one is empty.
        write(self.out / eb.SENT, eb.SENT_FIELDS, [{"email": f"x{i}@y.co.uk", "sent": "2026-09-28"} for i in range(se.DAILY_CAP - 1)])
        self.assertEqual(se.send_batch(self.out, sleep=self.sleeps.append, today=TODAY, out=lambda s: None), 3)
        # Least-used first: the empty extra inbox takes all three, the main one keeps its last slot.
        self.assertEqual(list(self.by_inbox), ["jack@getscalar.co.uk"])
        self.assertEqual(len(self.by_inbox["jack@getscalar.co.uk"].sent), 3)

    def test_a_full_inbox_hands_over_to_the_others(self):
        write(self.out / eb.SENT, eb.SENT_FIELDS, [{"email": f"x{i}@y.co.uk", "sent": "2026-09-28", "sent_from": ""} for i in range(se.DAILY_CAP)])
        self.assertEqual(se.send_batch(self.out, sleep=self.sleeps.append, today=TODAY, out=lambda s: None), 3)
        self.assertEqual(list(self.by_inbox), ["jack@getscalar.co.uk"])  # the main inbox is full today


class PreviewEmails(SendEmail):
    SETTINGS = {"MAIL_ADDRESS": "jack@scalar.co.uk", "MAIL_APP_PASSWORD": "x", "MAIL_FROM_NAME": "Jack Wilkins",
                "MAIL_EXTRA_1_ADDRESS": "ash@scalar2.co.uk", "MAIL_EXTRA_1_PASSWORD": "y"}

    def test_shows_every_email_as_it_will_go_and_sends_nothing(self):
        smtp = FakeSMTP()
        out = se.preview_batch(self.out, env=self.SETTINGS)
        self.assertTrue(out["ok"])
        self.assertEqual([e["business"] for e in out["emails"]], ["Kerr Roofing", "Acme Drives", "Oak Lofts"])
        kerr = out["emails"][0]
        self.assertEqual(kerr["subject"], "Kerr Roofing - quick look at your website")
        self.assertIn("Hi Bill,", kerr["body"])
        self.assertIn("It scored 41 out of 100.", kerr["body"])
        self.assertIn("Jack Wilkins", kerr["body"])
        self.assertEqual(kerr["preview_url"], "https://s.co/for/kerr-1")
        self.assertEqual({e["from"] for e in out["emails"]}, {"jack@scalar.co.uk", "ash@scalar2.co.uk"})  # spread
        self.assertEqual(smtp.sent, [])
        self.assertFalse((self.out / eb.SENT).exists())

    def test_marks_who_would_be_skipped(self):
        write(self.out / "replies.csv", ["from", "business", "kind"], [{"from": "sue@oak.co.uk", "business": "Oak Lofts", "kind": "read it"}])
        out = se.preview_batch(self.out, env=self.SETTINGS)
        self.assertEqual(out["emails"][2]["skip"], "they've replied")
        self.assertEqual(out["emails"][0]["skip"], "")

    def test_first_line_edits_count_without_remaking_the_batch(self):
        import first_line

        first_line.save(self.out, {"kerr.co.uk": {"website": "kerr.co.uk", "business": "Kerr Roofing",
                                                  "first_line": "Saw you fit flat roofs around Leeds.", "made_on": ""}})
        out = se.preview_batch(self.out, env=self.SETTINGS)
        self.assertIn("Hi Bill,\n\nSaw you fit flat roofs around Leeds. I put together", out["emails"][0]["body"])
        smtp = FakeSMTP()
        self.send(smtp, test=True)
        self.assertIn("Saw you fit flat roofs around Leeds.", smtp.sent[0].get_content())

    def test_nothing_waiting_says_so(self):
        (self.out / eb.PENDING).unlink()
        self.assertIn("No batch waiting", se.preview_batch(self.out, env=self.SETTINGS)["error"])


class TodaySummary(unittest.TestCase):
    """What the panel shows under the batch: sent today, left today, and the same per inbox."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)
        self.today = date(2026, 9, 30)

    def tearDown(self):
        self.tmp.cleanup()

    def log(self, rows):
        write(self.out / eb.SENT, eb.SENT_FIELDS, rows)

    def test_counts_first_emails_and_followups_per_inbox(self):
        self.log([
            {"email": "a@x.co.uk", "sent": "2026-09-30", "sent_from": "me@scalar.co.uk"},
            {"email": "b@x.co.uk", "sent": "2026-09-25", "followup_sent": "2026-09-30", "sent_from": "me@scalar.co.uk"},
            {"email": "c@x.co.uk", "sent": "2026-09-30", "sent_from": "two@scalar.co.uk"},
            {"email": "d@x.co.uk", "sent": "2026-09-29", "sent_from": "two@scalar.co.uk"},
        ])
        s = se.today_summary(self.out, self.today, ["me@scalar.co.uk", "two@scalar.co.uk"])
        self.assertEqual(s["sent"], 3)
        self.assertEqual(s["cap"], 2 * se.DAILY_CAP)
        self.assertEqual(s["left"], 2 * se.DAILY_CAP - 3)
        self.assertEqual([(r["inbox"], r["sent"]) for r in s["by_inbox"]], [("me@scalar.co.uk", 2), ("two@scalar.co.uk", 1)])

    def test_mailmeteor_rows_count_to_the_main_inbox(self):
        self.log([{"email": "a@x.co.uk", "sent": "2026-09-30"}, {"email": "b@x.co.uk", "sent": "2026-09-30"}])
        s = se.today_summary(self.out, self.today, ["me@scalar.co.uk"])
        self.assertEqual(s["by_inbox"], [{"inbox": "me@scalar.co.uk", "sent": 2, "left": se.DAILY_CAP - 2}])

    def test_no_inboxes_set_up_still_counts(self):
        self.log([{"email": "a@x.co.uk", "sent": "2026-09-30"}])
        s = se.today_summary(self.out, self.today, [])
        self.assertEqual((s["sent"], s["left"], s["by_inbox"][0]["inbox"]), (1, se.DAILY_CAP - 1, "main inbox"))

    def test_a_removed_inbox_still_shows_with_nothing_left(self):
        self.log([{"email": "a@x.co.uk", "sent": "2026-09-30", "sent_from": "old@scalar.co.uk"}])
        s = se.today_summary(self.out, self.today, ["me@scalar.co.uk"])
        self.assertEqual(s["sent"], 1)
        self.assertIn({"inbox": "old@scalar.co.uk", "sent": 1, "left": 0}, s["by_inbox"])
        self.assertEqual(s["left"], se.DAILY_CAP)

    def test_never_over_the_cap(self):
        self.log([{"email": f"x{i}@y.co.uk", "sent": "2026-09-30", "sent_from": "me@scalar.co.uk"} for i in range(se.DAILY_CAP + 5)])
        self.assertEqual(se.today_summary(self.out, self.today, ["me@scalar.co.uk"])["left"], 0)


class WhyLine(unittest.TestCase):
    def test_only_said_when_the_site_really_is_slow(self):
        from push_prospects import why_line

        self.assertIn("press back before it loads", why_line(34))
        self.assertIn("press back before it loads", why_line(89))
        self.assertEqual(why_line(90), "")
        self.assertEqual(why_line(None), "")


class SendGap(unittest.TestCase):
    def test_minutes_apart_varies_around_the_choice(self):
        self.assertEqual(se.gap_range(0), se.GAP_SECONDS)
        self.assertEqual(se.gap_range(None), se.GAP_SECONDS)
        self.assertEqual(se.gap_range(5), (240.0, 360.0))
        self.assertEqual(se.gap_range(0.25), (30.0, 30.0))  # never under 30 seconds
        self.assertEqual(se.gap_range(500), (2880.0, 4320.0))  # capped at an hour

    def test_panel_passes_minutes_apart_and_refuses_nonsense(self):
        import control_panel as cp

        ok = {"MAIL_ADDRESS": "a@b.c", "MAIL_APP_PASSWORD": "x", "MAIL_FROM_NAME": "Ash"}
        steps = lambda gap: cp.build_steps({"action": "send_followups", "send_gap": gap}, ok)  # noqa: E731
        self.assertIn((cp.SEND, ["--followups", "--gap-minutes", "5"]), steps("5")[0](None))
        self.assertIn((cp.SEND, ["--followups"]), steps("")[0](None))
        self.assertIsNone(steps("61")[0])
        self.assertIsNone(steps("soon")[0])
        self.assertIn("--from", cp.build_steps({"action": "send_batch", "send_from": "jack@getscalar.co.uk"}, ok)[0](None)[-2][1])
        self.assertIsNone(cp.build_steps({"action": "send_batch", "send_from": "not an inbox"}, ok)[0])

    def test_says_how_long_the_run_takes(self):
        self.assertEqual(se.describe_gap(5, 20), "about 5 minutes apart - roughly 1h35 for 20")
        self.assertEqual(se.describe_gap(0, 20), "40-90 seconds apart - roughly 20 min for 20")


if __name__ == "__main__":
    unittest.main()
