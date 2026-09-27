"""Offline tests for do-not-contact, cross-list duplicates, findings and the Mailmeteor columns.

Run: python -m unittest scripts/test_pipeline_rules.py
"""

import csv
import io
import os
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import openpyxl

from contact_rules import Claims, add_to_blocklist, load_blocklist
from findings import all_issues, top_issue


def domain_of(w):
    from push_prospects import domain_of as d

    return d(w)


def make_sheet(path: Path, rows: list[dict], tab: str = "Outreach") -> None:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = tab
    header = ["Business", "Website", "Status", "Email", "Company type", "Trade", "Area", "Contact name"]
    ws.append(header)
    for r in rows:
        ws.append([r.get(h, "") for h in header])
    wb.save(path)


class Findings(unittest.TestCase):
    def test_order_matches_the_preview_page(self):
        t = {"checks": {"whatsapp": False, "contactForm": False, "tapToCall": False}, "copyrightYear": 2019}
        issues = all_issues(t, 2026)
        self.assertEqual(issues[0], "your phone number isn't tap-to-call on a mobile")
        self.assertEqual(issues[1], "there's no enquiry form on your homepage")
        self.assertIn("your website footer still says © 2019", issues)
        self.assertEqual(issues[-1], "there's no WhatsApp link on your site")

    def test_nothing_found(self):
        self.assertEqual(top_issue({"checks": {"tapToCall": True}}, 2026), "")
        self.assertEqual(top_issue(None, 2026), "")

    def test_small_image_savings_and_recent_years_are_not_issues(self):
        self.assertEqual(all_issues({"checks": {}, "imageSavingsKb": 200, "copyrightYear": 2025}, 2026), [])


class Rules(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_a_no_in_one_sheet_blocks_the_firm_everywhere(self):
        make_sheet(self.dir / "old.xlsx", [{"Business": "Smith Roofing Ltd", "Website": "www.smithroofing.co.uk", "Status": "Lost / not interested", "Email": "info@smithroofing.co.uk"}])
        block = load_blocklist(self.dir, domain_of)
        self.assertTrue(block.why("smithroofing.co.uk", "", ""))
        self.assertTrue(block.why("", "INFO@smithroofing.co.uk", ""))
        self.assertTrue(block.why("", "", "SMITH ROOFING"))  # spelled differently in a new list
        self.assertIsNone(block.why("jones.co.uk", "a@jones.co.uk", "Jones"))

    def test_hand_added_entries(self):
        add_to_blocklist(self.dir, [("website", "acme.co.uk"), ("email", "bob@acme.co.uk")], "asked by phone")
        self.assertEqual(add_to_blocklist(self.dir, [("website", "ACME.co.uk")], "again"), 0)  # no duplicates
        block = load_blocklist(self.dir, domain_of)
        self.assertEqual(block.why("acme.co.uk", "", ""), "asked by phone")

    def test_claims_belong_to_the_first_list_and_lapse(self):
        make_sheet(self.dir / "a.xlsx", [{"Business": "X", "Website": "x.co.uk"}])
        listed = {}
        load_blocklist(self.dir, domain_of, listed)
        claims = Claims(self.dir, listed)
        claims.claim(["x.co.uk"], "a.xlsx")
        self.assertEqual(Claims(self.dir, listed).other_owner("x.co.uk", "b.xlsx"), "a.xlsx")
        self.assertIsNone(Claims(self.dir, listed).other_owner("x.co.uk", "a.xlsx"))
        # Removed from a.xlsx: no longer a's.
        make_sheet(self.dir / "a.xlsx", [])
        listed = {}
        load_blocklist(self.dir, domain_of, listed)
        self.assertIsNone(Claims(self.dir, listed).other_owner("x.co.uk", "b.xlsx"))


class PushRun(unittest.TestCase):
    """push_prospects end to end (dry run) with the rules in place."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        make_sheet(self.dir / "master.xlsx", [
            {"Business": "Said No Roofing", "Website": "saidno.co.uk", "Status": "Lost / not interested", "Email": "a@saidno.co.uk", "Company type": "Ltd"},
            {"Business": "Shared Roofing", "Website": "shared.co.uk", "Status": "New", "Email": "a@shared.co.uk", "Company type": "Ltd"},
        ])
        make_sheet(self.dir / "new-list.xlsx", [
            {"Business": "SAID NO ROOFING LTD", "Website": "saidno-roofing.co.uk", "Status": "New", "Email": "x@saidno-roofing.co.uk", "Company type": "Ltd"},
            {"Business": "Shared Roofing", "Website": "https://www.shared.co.uk/", "Status": "New", "Email": "a@shared.co.uk", "Company type": "Ltd"},
            {"Business": "Fresh Roofing", "Website": "fresh.co.uk", "Status": "New", "Email": "info@fresh.co.uk", "Company type": "Ltd", "Trade": "Roofing", "Area": "Woking", "Contact name": "Ann Lee"},
        ])
        with (self.dir / "teardown-log.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["website", "checked_at", "result", "mobile_score", "lcp_s", "top_issue", "issue_count"])
            w.writerow(["fresh.co.uk", "2026-09-01", "ok", "41", "6.2", "your phone number isn't tap-to-call on a mobile", "3"])

    def tearDown(self):
        self.tmp.cleanup()

    def run_push(self, sheet):
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"PROSPECTS_API_SECRET": "x" * 40}), redirect_stdout(buf), \
                mock.patch.object(sys, "argv", ["p", "--sheet", str(self.dir / sheet), "--dry-run"]):
            import push_prospects

            push_prospects.main()
        return buf.getvalue()

    def test_blocked_and_duplicate_firms_are_left_out_of_the_new_list(self):
        self.run_push("master.xlsx")  # the master lists (and so owns) Shared Roofing first
        out = self.run_push("new-list.xlsx")
        self.assertIn("1 prospects", out)
        self.assertIn("they said no", out)
        self.assertIn("SAID NO ROOFING LTD", out)
        self.assertIn("already in master.xlsx", out)
        with (self.dir / "mailmeteor-new-list.csv").open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual([r["business"] for r in rows], ["Fresh Roofing"])
        r = rows[0]
        self.assertEqual((r["trade"], r["area"], r["greeting_name"]), ("roofing", "Woking", "Ann"))
        self.assertEqual(r["top_issue"], "your phone number isn't tap-to-call on a mobile")
        self.assertEqual(r["mobile_score"], "41")
    def test_parallel_speed_checks_record_findings(self):
        import threading

        running, peak = [0], [0]
        lock = threading.Lock()

        def fake_teardown(domain, key):
            with lock:
                running[0] += 1
                peak[0] = max(peak[0], running[0])
            time.sleep(0.05)
            with lock:
                running[0] -= 1
            if domain == "broken.co.uk":
                raise RuntimeError("boom")
            return {"v": 1, "checks": {"contactForm": False}, "_mobile_score": 55, "_lcp_s": 4.1}

        rows = [{"Business": f"Firm {i}", "Website": f"firm{i}.co.uk", "Status": "New", "Company type": "Ltd"} for i in range(7)]
        rows.append({"Business": "Broken", "Website": "broken.co.uk", "Status": "New", "Company type": "Ltd"})
        make_sheet(self.dir / "batch.xlsx", rows)
        buf = io.StringIO()
        env = {"PROSPECTS_API_SECRET": "x" * 40, "PAGESPEED_API_KEY": "k"}
        with mock.patch.dict(os.environ, env), redirect_stdout(buf), mock.patch("site_teardown.teardown", fake_teardown), \
                mock.patch.object(sys, "argv", ["p", "--sheet", str(self.dir / "batch.xlsx"), "--teardown", "--yes-all", "--dry-run"]):
            import push_prospects

            push_prospects.main()
        out = buf.getvalue()
        self.assertEqual(peak[0], 4, out)  # four at a time, never more
        self.assertIn("55/100, 1 issue - worst: there's no enquiry form on your homepage", out)
        self.assertIn("broken.co.uk: check failed (RuntimeError)", out)
    def test_find_contacts_fills_blanks_and_never_overrides_the_sheet(self):
        make_sheet(self.dir / "c.xlsx", [
            {"Business": "Blank Roofing", "Website": "blank.co.uk", "Status": "New", "Company type": "Ltd"},
            {"Business": "Has Email Roofing", "Website": "hasemail.co.uk", "Status": "New", "Email": "mine@hasemail.co.uk", "Company type": "Ltd", "Contact name": "Sue Bell"},
        ])
        with (self.dir / "company-lookups.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["website", "result", "number", "company_type"])
            w.writerow(["blank.co.uk", "company", "01234567", "Ltd"])
        pages = {
            "https://blank.co.uk/": ('<a href="tel:01483 222333">x</a><a href="/contact">c</a>', "https://blank.co.uk/"),
            "https://blank.co.uk/contact": ("<p>office@blank.co.uk</p>", "https://blank.co.uk/contact"),
            "https://hasemail.co.uk/": ("<p>other@hasemail.co.uk 01483 999000</p>", "https://hasemail.co.uk/"),
        }
        officers = {"items": [{"name": "BLANK, Tom", "officer_role": "director", "appointed_on": "2010-01-01"}]}
        buf = io.StringIO()
        env = {"PROSPECTS_API_SECRET": "x" * 40, "COMPANIES_HOUSE_API_KEY": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"}
        with mock.patch.dict(os.environ, env), redirect_stdout(buf), \
                mock.patch("site_teardown.fetch_html", lambda url, timeout=20: pages.get(url, (None, None))), \
                mock.patch("company_lookup._get", lambda path, key: officers), \
                mock.patch.object(sys, "argv", ["p", "--sheet", str(self.dir / "c.xlsx"), "--find-contacts", "--dry-run"]):
            import push_prospects

            push_prospects.main()
        out = buf.getvalue()
        self.assertIn("Blank Roofing: office@blank.co.uk · 01483 222333 · Tom Blank", out)
        with (self.dir / "mailmeteor-c.csv").open(encoding="utf-8") as f:
            rows = {r["business"]: r for r in csv.DictReader(f)}
        self.assertEqual((rows["Blank Roofing"]["email"], rows["Blank Roofing"]["greeting_name"]), ("office@blank.co.uk", "Tom"))
        # The sheet's own email and contact win over anything found.
        self.assertEqual((rows["Has Email Roofing"]["email"], rows["Has Email Roofing"]["greeting_name"]), ("mine@hasemail.co.uk", "Sue"))


class Letters(unittest.TestCase):
    def test_fill_leaves_out_unknown_facts(self):
        import letters

        body = letters.fill("Dear {greeting},\n\nA. {score_sentence} {issue_sentence} B. {unknown}", {"greeting": "Tom"})
        self.assertEqual(body, "Dear Tom,\n\nA. B. {unknown}")
        self.assertEqual(letters.score_sentence(38), "It scored 38 out of 100 on mobile, which Google itself counts as poor.")
        self.assertEqual(letters.score_sentence(None), "")

    def test_letters_run(self):
        import openpyxl

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Outreach"
            head = ["Business", "Website", "Status", "Email", "Company type", "Contact name", "Address", "Trade", "Company number"]
            ws.append(head)
            ws.append(["Sole Roofer", "soleroofer.co.uk", "New", "", "Sole trader", "Bill Kerr", "4 Mill Lane, Woking, GU21 1AA", "Roofing", ""])
            ws.append(["No Address Ltd", "noaddress.co.uk", "New", "", "Ltd", "", "", "Roofing", "07654321"])
            ws.append(["Posted Already", "posted.co.uk", "New", "", "Sole trader", "", "1 Road, Town, GU1 1AA", "", ""])
            ws.append(["Email Firm", "emailfirm.co.uk", "New", "info@emailfirm.co.uk", "Ltd", "", "2 Road, Town", "", ""])
            nw = wb.create_sheet("No website")
            nw.append(["Business", "Status", "Company type", "Contact name", "Registered address", "Trade", "Company number"])
            nw.append(["Siteless Builders", "New", "Ltd", "Ann Hale", "9 High St, Guildford, GU1 2BB", "Building & extensions", "01111111"])
            wb.save(d / "letters.xlsx")
            with (d / "company-lookups.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["website", "result", "number", "company_type"])
                w.writerow(["noaddress.co.uk", "company", "07654321", "Ltd"])
            with (d / "teardown-log.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["website", "checked_at", "result", "mobile_score", "lcp_s", "top_issue", "issue_count"])
                w.writerow(["soleroofer.co.uk", "2026-09-01", "ok", "34", "7.1", "your phone number isn't tap-to-call on a mobile", "2"])
            import overrides

            with (d / "letters-sent.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["key", "business", "sheet", "posted"])
                w.writerow([overrides.row_key({"Business": "Posted Already"}), "Posted Already", "letters.xlsx", "2026-09-01"])
            office = {"registered_office_address": {"address_line_1": "Unit 3", "locality": "Leeds", "postal_code": "LS1 1AA"}}
            buf = io.StringIO()
            env = {"PROSPECTS_API_SECRET": "x" * 40, "COMPANIES_HOUSE_API_KEY": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d"}
            with mock.patch.dict(os.environ, env), redirect_stdout(buf), mock.patch("company_lookup._get", lambda path, key: office), \
                    mock.patch.object(sys, "argv", ["p", "--sheet", str(d / "letters.xlsx"), "--letters", "--dry-run"]):
                import push_prospects

                push_prospects.main()
            out = buf.getvalue()
            self.assertIn("Wrote letters-letters.html: 3 letters ready", out)
            self.assertIn("1 left out - already posted", out)
            page = (d / "letters-letters.html").read_text(encoding="utf-8")
            self.assertIn("Dear Bill,", page)
            self.assertIn("It scored 34 out of 100 on mobile, which Google itself counts as poor.", page)
            self.assertIn("I also noticed your phone number isn&#x27;t tap-to-call on a mobile.", page)
            self.assertIn("Unit 3<br>Leeds<br>LS1 1AA", page)  # registered office from Companies House
            self.assertIn("Dear Ann,", page)
            self.assertIn("I couldn&#x27;t find a website for Siteless Builders", page)
            self.assertIn("builders", page)
            self.assertNotIn("Email Firm", page)  # goes by email, not letter
            self.assertNotIn("Posted Already", page)
            self.assertEqual(page.count("data:image/svg+xml"), 3)
            with (d / "letters-batch-letters.csv").open(encoding="utf-8") as f:
                self.assertEqual(len(list(csv.DictReader(f))), 3)


class CallList(unittest.TestCase):
    def test_joins_views_with_local_phones_and_letter_dates(self):
        import calls
        import overrides
        from datetime import datetime, timezone
        from push_prospects import make_slug

        secret = "x" * 40
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Outreach"
            ws.append(["Business", "Website", "Status", "Phone", "Contact name"])
            ws.append(["Hot Roofing", "hot.co.uk", "New", "01483 111111", "Amy Hot"])
            ws.append(["Warm Roofing", "warm.co.uk", "New", "01483 222222", ""])
            ws.append(["Quiet Roofing", "quiet.co.uk", "New", "", ""])
            ws.append(["Called Roofing", "called.co.uk", "New", "01483 444444", ""])
            ws.append(["No Roofing", "no.co.uk", "New", "01483 555555", ""])
            wb.save(d / "s.xlsx")
            with (d / "contacts-found.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["website", "email", "phone", "contact", "address", "checked_at"])
                w.writerow(["quiet.co.uk", "", "07700 900000", "", "", ""])
            with (d / "letters-sent.csv").open("w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(["key", "business", "sheet", "posted"])
                w.writerow([overrides.row_key({"Business": "Quiet Roofing"}), "Quiet Roofing", "s.xlsx", "2026-09-10"])
            calls.log_call(d, "s.xlsx", overrides.row_key({"Business": "No Roofing"}), "No Roofing", "Not interested")
            now = datetime(2026, 9, 27, 12, tzinfo=timezone.utc)
            act = {
                make_slug("Hot Roofing", "hot.co.uk", secret): {"view_count": 3, "last_viewed_at": "2026-09-27T11:00:00Z"},
                make_slug("Warm Roofing", "warm.co.uk", secret): {"view_count": 1, "last_viewed_at": "2026-09-20T11:00:00Z"},
                make_slug("No Roofing", "no.co.uk", secret): {"view_count": 5, "last_viewed_at": "2026-09-27T11:00:00Z"},
            }
            out = calls.call_list(d, "s.xlsx", secret, "https://site", act, now)
            self.assertEqual([i["business"] for i in out["viewing"]], ["Hot Roofing", "Warm Roofing"])
            hot = out["viewing"][0]
            self.assertEqual((hot["phone"], hot["contact"], hot["views"]), ("01483 111111", "Amy Hot", 3))
            self.assertTrue(hot["preview"].endswith("?src=dashboard"))  # your own look isn't counted as theirs
            self.assertEqual([(i["business"], i["phone"], i["waited"]) for i in out["letters"]], [("Quiet Roofing", "07700 900000", 17)])
            # Called after their last visit: off the list until they look again.
            with (d / "calls.csv").open("a", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow([overrides.row_key({"Business": "Hot Roofing"}), "s.xlsx", "Hot Roofing", "No answer", "", "2026-09-27T12:30:00+00:00"])
            later = datetime(2026, 9, 27, 13, tzinfo=timezone.utc)
            self.assertEqual([i["business"] for i in calls.call_list(d, "s.xlsx", secret, "https://site", act, later)["viewing"]], ["Warm Roofing"])

    def test_dashboard_without_the_endpoint(self):
        import calls
        import urllib.error

        err = urllib.error.HTTPError("u", 404, "nf", {}, io.BytesIO(b""))
        with mock.patch.object(calls.urllib.request, "urlopen", side_effect=err):
            with self.assertRaisesRegex(calls.DashboardMissing, "activity update"):
                calls.fetch_activity("https://x", "s", "t")


class Review(unittest.TestCase):
    def setUp(self):
        import openpyxl

        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Outreach"
        head = ["Business", "Website", "Status", "Email", "Company type", "Company number"]
        ws.append(head)
        ws.append(["Unsure Roofing", "unsure.co.uk", "New", "a@unsure.co.uk", "", ""])
        ws.append(["Bad Email Roofing", "bademail.co.uk", "New", "bob@gmial.com", "Ltd", ""])
        ws.append(["Down Roofing", "down.co.uk", "New", "", "Ltd", ""])
        ws.append(["Gone Roofing", "gone.co.uk", "New", "", "", ""])
        chk = wb.create_sheet("Check website")
        chk.append(["Business", "Website", "Possible website", "Status", "Email", "Company type", "Company number", "Website found"])
        chk.append(["Maybe Roofing", "", "mayberoofing.co.uk", "New", "info@mayberoofing.co.uk", "Ltd", "01234567", "name only"])
        wb.save(self.dir / "list.xlsx")
        with (self.dir / "company-lookups.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["website", "result", "how", "status", "registered_name", "number"])
            w.writerow(["unsure.co.uk", "unsure", "unsure (1 same-name company, not confirmed)", "", "", ""])
            w.writerow(["gone.co.uk", "closed", "number on their site", "dissolved", "GONE ROOFING LTD", "07777777"])
        with (self.dir / "email-checks.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["email", "result", "checked_at"])
            w.writerow(["bob@gmial.com", "typo (did they mean gmail.com?)", "2026-09-01"])
        with (self.dir / "teardown-log.csv").open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["website", "checked_at", "result", "mobile_score", "lcp_s"])
            w.writerow(["down.co.uk", "2026-09-01", "failed", "", ""])

    def tearDown(self):
        self.tmp.cleanup()

    def push(self):
        buf = io.StringIO()
        with mock.patch.dict(os.environ, {"PROSPECTS_API_SECRET": "x" * 40}), redirect_stdout(buf), \
                mock.patch.object(sys, "argv", ["p", "--sheet", str(self.dir / "list.xlsx"), "--dry-run"]):
            import push_prospects

            push_prospects.main()
        with (self.dir / "preview-links-list.csv").open(encoding="utf-8") as f:
            return buf.getvalue(), {r["Business"]: r for r in csv.DictReader(f)}

    def test_finds_every_kind(self):
        import review

        kinds = {(i["kind"], i["business"]) for i in review.items(self.dir, "list.xlsx")}
        self.assertEqual(kinds, {
            ("website", "Maybe Roofing"), ("company", "Unsure Roofing"), ("email", "Bad Email Roofing"),
            ("failed", "Down Roofing"), ("closed", "Gone Roofing"),
        })

    def test_decisions_change_the_next_run_and_leave_the_review(self):
        import review

        items = {i["business"]: i for i in review.items(self.dir, "list.xlsx")}
        _, before = self.push()
        self.assertEqual(before["Unsure Roofing"]["Channel"], "letter")
        self.assertNotIn("Maybe Roofing", before)

        review.decide(self.dir, "list.xlsx", items["Unsure Roofing"]["key"], "set_type", "Ltd")
        review.decide(self.dir, "list.xlsx", items["Maybe Roofing"]["key"], "website_yes", "mayberoofing.co.uk")
        review.decide(self.dir, "list.xlsx", items["Bad Email Roofing"]["key"], "set_email", "bob@gmail.com")
        review.decide(self.dir, "list.xlsx", items["Down Roofing"]["key"], "skip")
        out, after = self.push()
        self.assertEqual(after["Unsure Roofing"]["Channel"], "email")
        self.assertEqual(after["Maybe Roofing"]["Channel"], "email")
        self.assertEqual(after["Bad Email Roofing"]["Email"], "bob@gmail.com")
        self.assertNotIn("Down Roofing", after)
        self.assertIn("1 left out in Review", out)
        left = {i["business"] for i in review.items(self.dir, "list.xlsx")}
        self.assertEqual(left, {"Gone Roofing"})

        review.decide(self.dir, "list.xlsx", items["Down Roofing"]["key"], "undo")
        self.assertIn("Down Roofing", self.push()[1])

    def test_do_not_contact_from_review(self):
        import review

        review.block(self.dir, "Unsure Roofing", "unsure.co.uk", "a@unsure.co.uk")
        out, rows = self.push()
        self.assertNotIn("Unsure Roofing", rows)
        self.assertIn("do not contact (Review)", out)


class Panel(unittest.TestCase):
    def test_phone_alert_carries_counts_never_names(self):
        import control_panel

        sent = {}

        def fake_urlopen(req, timeout=0):
            import json

            sent.update(json.loads(req.data))
            return mock.MagicMock()

        lines = [
            "[3/10] smithroofing.co.uk: 41/100, 3 issues - worst: your phone number ...",
            "    Smith Roofing: info@smithroofing.co.uk",
            "Pushed 10 (rejected: [])",
            "List done: 120 speed checked, 4 couldn't be checked.",
        ]
        with mock.patch.object(control_panel.urllib.request, "urlopen", fake_urlopen):
            control_panel.phone_alert("Run the whole list", 0, False, 3900, lines, {"TELEGRAM_BOT_TOKEN": "t", "TELEGRAM_CHAT_ID": "1"})
        self.assertIn("Done: Run the whole list (1h 5m)", sent["text"])
        self.assertIn("List done: 120", sent["text"])
        self.assertNotIn("smith", sent["text"].lower())

    def test_progress_uses_the_same_rules(self):
        import control_panel

        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            make_sheet(d / "master.xlsx", [{"Business": "No", "Website": "no.co.uk", "Status": "Lost / not interested"}])
            make_sheet(d / "new.xlsx", [
                {"Business": "No", "Website": "no.co.uk", "Status": "New"},
                {"Business": "Yes", "Website": "yes.co.uk", "Status": "New"},
            ])
            with mock.patch.object(control_panel, "OUTREACH", d):
                self.assertEqual(control_panel.progress("new.xlsx")["total"], 1)

    def test_no_alert_without_telegram(self):
        import control_panel

        with mock.patch.object(control_panel.urllib.request, "urlopen") as u:
            control_panel.phone_alert("x", 0, False, 999, ["Pushed 1"], {})
        u.assert_not_called()


if __name__ == "__main__":
    unittest.main()
