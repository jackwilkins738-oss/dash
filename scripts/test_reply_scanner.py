"""Offline tests for reply_scanner - a pretend inbox, no network. Run: python -m unittest scripts/test_reply_scanner.py"""

import csv
import tempfile
import unittest
from datetime import date
from email.message import EmailMessage
from pathlib import Path

import openpyxl

import reply_scanner as rs


def msg(frm, subject, body, **headers):
    m = EmailMessage()
    m["From"] = frm
    m["To"] = "me@scalar.test"
    m["Subject"] = subject
    m["Date"] = "Mon, 28 Sep 2026 10:00:00 +0100"
    m["Message-ID"] = f"<{abs(hash(frm + subject))}@test>"
    for k, v in headers.items():
        m[k.replace("_", "-")] = v
    m.set_content(body)
    return m.as_bytes()


def bounce_for(addr):
    m = EmailMessage()
    m["From"] = "Mail Delivery Subsystem <mailer-daemon@googlemail.com>"
    m["Subject"] = "Delivery Status Notification (Failure)"
    m["Date"] = "Mon, 28 Sep 2026 09:00:00 +0100"
    m["Message-ID"] = "<bounce-1@test>"
    m.set_content(f"Address not found\n\nYour message wasn't delivered to {addr} because the address couldn't be found.")
    return m.as_bytes()


class FakeImap:
    def __init__(self, messages):
        self.messages = messages
        self.readonly = None

    def select(self, box, readonly=False):
        self.readonly = readonly
        return "OK", [b"1"]

    def search(self, charset, *criteria):
        return "OK", [" ".join(str(i + 1) for i in range(len(self.messages))).encode()]

    def fetch(self, num, what):
        assert "PEEK" in what  # never marks anything read
        return "OK", [(b"1 (BODY[] {1})", self.messages[int(num) - 1])]


class Scanner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Outreach"
        ws.append(["Business", "Website", "Email", "Phone"])
        ws.append(["Kerr Roofing", "kerrroofing.co.uk", "info@kerrroofing.co.uk", "01483 111222"])
        ws.append(["Surrey Slate", "surreyslate.co.uk", "hello@surreyslate.co.uk", ""])
        ws.append(["Peak Roofing", "peakroofing.co.uk", "peak@gmail.com", ""])
        ws.append(["Away Builders", "awaybuild.co.uk", "office@awaybuild.co.uk", ""])
        ws.append(["Chatty Roofing", "chatty.co.uk", "info@chatty.co.uk", ""])
        wb.save(self.d / "list.xlsx")

    def tearDown(self):
        self.tmp.cleanup()

    def run_scan(self, messages):
        imap = FakeImap(messages)
        replies = rs.scan(self.d, imap, date(2026, 9, 1), "me@scalar.test")
        self.assertTrue(imap.readonly)
        rs.act(self.d, replies)
        return {r["business"]: r["kind"] for r in replies}

    def test_sorts_every_kind_and_acts(self):
        kinds = self.run_scan([
            msg("Bill <bill@kerrroofing.co.uk>", "Re: A quick look", "Sounds good - give me a call tomorrow.\n\nOn Mon, Scalar wrote:\n> not interested"),
            msg("Amy <hello@surreyslate.co.uk>", "Re: A quick look", "Thanks but we're not interested. Please remove us."),
            bounce_for("peak@gmail.com"),
            msg("office@awaybuild.co.uk", "Automatic reply: A quick look", "I am out of the office until Monday.", Auto_Submitted="auto-replied"),
            msg("Dan <dan@chatty.co.uk>", "Re: A quick look", "Who is this?"),
            msg("Random <someone@unrelated.co.uk>", "Hello", "Not one of yours - interested?"),
        ])
        self.assertEqual(kinds, {
            "Kerr Roofing": "interested",  # the quoted "not interested" below the reply is ignored
            "Surrey Slate": "not interested",
            "Peak Roofing": "bounce",
            "Away Builders": "out of office",
            "Chatty Roofing": "read it",
        })  # the unrelated sender is ignored entirely
        rows = list(csv.DictReader((self.d / "replies.csv").open(encoding="utf-8")))
        self.assertNotIn("unrelated", "".join(r["from"] for r in rows))
        block = list(csv.DictReader((self.d / "do-not-contact.csv").open(encoding="utf-8")))
        self.assertIn(("email", "hello@surreyslate.co.uk"), [(b["kind"], b["value"]) for b in block])
        self.assertIn(("website", "surreyslate.co.uk"), [(b["kind"], b["value"]) for b in block])
        checks = {r["email"]: r["result"] for r in csv.DictReader((self.d / "email-checks.csv").open(encoding="utf-8"))}
        self.assertEqual(checks["peak@gmail.com"], "bounced")

    def test_a_reply_from_a_personal_address_is_matched_by_the_subject(self):
        kinds = self.run_scan([
            msg("Bill <bill.kerr1970@gmail.com>", "Re: A quick look at Kerr Roofing's website", "Ring me on Friday"),
            msg("Someone <x@gmail.com>", "Kerr Roofing newsletter", "Not a reply - ignored"),
        ])
        self.assertEqual(kinds, {"Kerr Roofing": "interested"})

    def test_no_wins_over_yes_and_nothing_is_read_twice(self):
        first = self.run_scan([msg("hello@surreyslate.co.uk", "Re: site", "How much? Actually no thanks, not interested.")])
        self.assertEqual(first, {"Surrey Slate": "not interested"})
        again = self.run_scan([msg("hello@surreyslate.co.uk", "Re: site", "How much? Actually no thanks, not interested.")])
        self.assertEqual(again, {})

    def test_batches_and_calls_follow_the_replies(self):
        import calls
        import email_batches as eb

        self.run_scan([
            msg("Bill <bill@kerrroofing.co.uk>", "Re: A quick look", "How much would it cost?"),
            msg("Amy <hello@surreyslate.co.uk>", "Re: A quick look", "Unsubscribe"),
            bounce_for("peak@gmail.com"),
        ])
        with (self.d / "mailmeteor-list.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["business", "email", "preview_url"])
            for b, e in (("Surrey Slate", "hello@surreyslate.co.uk"), ("Peak Roofing", "peak@gmail.com"), ("Chatty Roofing", "info@chatty.co.uk")):
                w.writerow([b, e, "https://s/for/x"])
        path, notes = eb.make_batch(self.d, 20, check=lambda u: None)
        self.assertEqual([r["business"] for r in csv.DictReader(path.open(encoding="utf-8"))], ["Chatty Roofing"])
        self.assertTrue(any("Surrey Slate" in n for n in notes) and any("bounced" in n for n in notes))

        out = calls.call_list(self.d, "list.xlsx", "x" * 40, "https://site", {})
        self.assertEqual([(r["business"], r["phone"], r["kind"]) for r in out["replied"]], [("Kerr Roofing", "01483 111222", "interested")])
        calls.mark_reply_handled(self.d, "Kerr Roofing")
        self.assertEqual(calls.call_list(self.d, "list.xlsx", "x" * 40, "https://site", {})["replied"], [])


if __name__ == "__main__":
    unittest.main()


class Objections(unittest.TestCase):
    def test_tags_the_common_push_backs(self):
        from reply_scanner import objection

        cases = {
            "Is this a scam? How did you get my email": "suspicious",
            "Sorry, that's too expensive for us at the moment": "price",
            "We already have someone who does our website": "has someone",
            "My son built our site, thanks": "has someone",
            "We get all our work from word of mouth": "enough work",
            "We're fully booked till spring": "enough work",
            "Happy with our current website thanks": "happy with site",
            "Not right now, maybe next year": "not now",
        }
        for text, tag in cases.items():
            self.assertEqual(objection(text), tag, text)

    def test_ordinary_replies_have_none(self):
        from reply_scanner import objection

        for text in ["How much would it be?", "I have a question about the preview", "I fully understand, call me Tuesday",
                     "Sounds good, what's included?", ""]:
            self.assertEqual(objection(text), "", text)
