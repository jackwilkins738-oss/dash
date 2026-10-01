"""Offline tests for the cloud reply watch: the right replies texted, once, and nothing personal printed."""

import contextlib
import io
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path
from unittest import mock

import cloud_reply_watch as cw

ME = "jack@getscalar.co.uk"


def mail(sender, body, minutes_ago=5, reply=True, mid=None):
    m = EmailMessage()
    m["From"] = sender
    m["To"] = ME
    m["Subject"] = "Re: A quick look at your website"
    m["Date"] = format_datetime(datetime.now(timezone.utc) - timedelta(minutes=minutes_ago))
    m["Message-ID"] = mid or f"<{abs(hash((sender, body)))}@mail>"
    if reply:
        m["In-Reply-To"] = "<first@getscalar.co.uk>"
    m.set_content(body)
    return m.as_bytes()


class FakeImap:
    def __init__(self, messages):
        self.messages = messages

    def login(self, *a):
        return "OK", []

    def select(self, *a, **k):
        return "OK", []

    def search(self, *a):
        return "OK", [" ".join(str(i + 1) for i in range(len(self.messages))).encode()]

    def fetch(self, num, what):
        raw = self.messages[int(num) - 1]
        if "HEADER" in what:
            raw = raw.split(b"\n\n", 1)[0] + b"\n\n"
        return "OK", [(b"1", raw)]

    def logout(self):
        pass


class CloudWatch(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.state = Path(self.tmp.name) / "seen.txt"
        self.env = mock.patch.dict(os.environ, {"REPLY_WATCH_INBOXES": f"{ME} abcd efgh ijkl mnop", "TELEGRAM_BOT_TOKEN": "t",
                                                "TELEGRAM_CHAT_ID": "c"})
        self.env.start()
        self.seen = mock.patch.object(cw, "SEEN_FILE", self.state)
        self.seen.start()

    def tearDown(self):
        self.env.stop()
        self.seen.stop()
        self.tmp.cleanup()

    def run_with(self, messages):
        sent = []
        out = io.StringIO()
        with mock.patch.object(cw.imaplib, "IMAP4_SSL", return_value=FakeImap(messages)), \
                mock.patch.object(cw, "send", lambda t, c, text: sent.append(text)), contextlib.redirect_stdout(out):
            code = cw.main()
        return code, sent, out.getvalue()

    def test_texts_the_replies_worth_answering_and_only_those(self):
        msgs = [
            mail("Bill Kerr <bill@kerr.co.uk>", "How much would it cost for us?"),
            mail("amy@slate.co.uk", "Not interested, thanks."),
            mail("newsletter@shop.com", "Big sale today!", reply=False),
            mail("tom@peak.co.uk", "Not right now, maybe in the spring."),
        ]
        code, sent, printed = self.run_with(msgs)
        self.assertEqual(code, 0)
        self.assertEqual(len(sent), 1)
        self.assertIn('Bill Kerr <bill@kerr.co.uk> replied to jack@getscalar.co.uk - asks the price:\n"How much would it cost for us?"', sent[0])
        self.assertNotIn("slate", sent[0])
        self.assertNotIn("peak", sent[0])

    def test_never_texted_twice(self):
        msgs = [mail("bill@kerr.co.uk", "Sounds good, give me a call", mid="<a1@x>")]
        self.assertEqual(len(self.run_with(msgs)[1]), 1)
        self.assertEqual(self.run_with(msgs)[1], [])

    def test_first_run_doesnt_dredge_up_old_replies(self):
        self.assertEqual(self.run_with([mail("bill@kerr.co.uk", "How much?", minutes_ago=600)])[1], [])

    def test_the_public_log_never_shows_who_or_what(self):
        _, _, printed = self.run_with([mail("Bill Kerr <bill@kerr.co.uk>", "How much would it cost?")])
        for secret in ("bill", "kerr", "How much", ME, "abcd"):
            self.assertNotIn(secret, printed)
        self.assertIn("1 texted", printed)

    def test_a_failed_text_is_retried_next_run(self):
        msgs = [mail("bill@kerr.co.uk", "How much?", mid="<b2@x>")]

        def fail(*a):
            raise OSError("down")

        with mock.patch.object(cw.imaplib, "IMAP4_SSL", return_value=FakeImap(msgs)), mock.patch.object(cw, "send", fail), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cw.main(), 1)
        self.assertEqual(len(self.run_with(msgs)[1]), 1)

    def test_not_set_up_is_quiet(self):
        with mock.patch.dict(os.environ, {"REPLY_WATCH_INBOXES": ""}), contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cw.main(), 0)
        self.assertIn("Not set up yet", out.getvalue())

    def test_inbox_lines(self):
        self.assertEqual(cw.inboxes("a@x.co.uk abcd efgh\n\nnot an inbox\nb@y.co.uk pass"),
                         [("a@x.co.uk", "abcdefgh"), ("b@y.co.uk", "pass")])


class LocalTextsStepAside(unittest.TestCase):
    def test_no_second_text_when_the_cloud_watch_is_on(self):
        import reply_scanner as rs

        hot = [{"kind": "interested", "business": "Kerr", "from": "b@k.co.uk", "snippet": "how much"}]
        with mock.patch.dict(os.environ, {"CLOUD_REPLY_ALERTS": "yes", "TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "c"}), \
                mock.patch.object(rs.urllib.request, "urlopen") as sent:
            rs.alert(hot)
        sent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
