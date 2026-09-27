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
