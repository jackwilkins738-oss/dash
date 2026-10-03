"""insights: joins every send with what happened, finds real differences, and never names anyone."""

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

import openpyxl

import insights


def write(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


class Insights(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        sent, mm, replies, views = [], [], [], {}
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Outreach"
        ws.append(["Business", "Website", "Email", "Company type", "Incorporated", "Google reviews", "Source"])
        for i in range(120):
            trade = "Roofing" if i < 60 else "Landscaping"
            name, email, slug = f"Firm{i} Roofing", f"owner{i}@firm{i}.co.uk", f"firm{i}-abc{i:03d}"
            sent.append({"email": email, "business": name, "preview_url": f"https://x/for/{slug}?src=email", "batch": "b",
                         "sent": "2026-09-21", "followup_sent": "2026-09-26" if i % 2 else "", "message_id": "", "subject": f"{name} - quick look at your website",
                         "variant": "A", "sent_from": "jack@scalarhq.digital", "sent_at": "07:30" if i % 3 else "14:00"})
            mm.append({"business": name, "email": email, "greeting_name": "John" if i % 4 else "there", "mobile_score": str(20 + i % 60),
                       "lcp_s": "6.1", "preview_url": f"https://x/for/{slug}", "trade": trade, "area": "Guildford" if i % 2 else "Woking",
                       "top_issue": "no enquiry form", "first_line": "Saw you fit flat roofs." if i % 2 else ""})
            ws.append([name, f"firm{i}.co.uk", email, "Ltd", "2015-01-01", 120 if i < 60 else 5, "Google Maps"])
            # Roofers reply far more: 18 of 60 vs 1 of 60 - a real difference.
            if (i < 60 and i % 10 < 3) or i == 100:
                replies.append({"message_id": f"m{i}", "date": "2026-09-23T09:00+00:00", "from": email, "business": name, "website": "",
                                "kind": "interested", "subject": "", "snippet": "", "handled": "", "intent": "price", "message": "", "objection": ""})
            views[slug] = {"slug": slug, "view_count": 2 if i % 2 else 0, "first_viewed_at": "2026-09-21T10:00:00Z" if i % 2 else None,
                           "engaged_seconds": 45 if i % 4 == 1 else 3, "max_scroll": 80, "reached": ["pricing"] if i % 4 == 1 else [], "choice": None}
        wb.save(self.d / "list.xlsx")
        write(self.d / "emails-sent.csv", sent)
        write(self.d / "mailmeteor-list.csv", mm)
        write(self.d / "replies.csv", replies)
        write(self.d / "calls.csv", [{"key": "k", "sheet": "list.xlsx", "business": "Firm1 Roofing", "outcome": "Interested", "note": "", "at": "2026-09-24"}])
        self.views = views

    def test_report(self):
        rows = insights.build(self.d, self.views, date(2026, 10, 3))
        self.assertEqual(len(rows), 120)
        text = "\n".join(insights.report(rows, date(2026, 10, 3)))
        self.assertIn("120 sent", text)
        self.assertIn("Roofing", text)
        self.assertRegex(text, r"Roofing\s+60 sent .*BETTER than average")
        self.assertRegex(text, r"Landscaping\s+60 sent .*WORSE than average")
        self.assertIn("+ Trade = Roofing", text)
        self.assertEqual(insights.subject_pattern("Firm1 Roofing - quick look at your website", "firm1 roofing"),
                         "<firm> - quick look at your website")
        self.assertEqual(insights.subject_pattern("Firm1 - 41/100 on Google's speed test", "firm1"), "<firm> - N/N on Google's speed test")
        self.assertIn("Reply intents: price 19", text)
        self.assertIn("Sections reached: pricing", text)
        # Nothing that names or reaches anyone.
        for bad in ("Firm1", "firm1", "@", "co.uk", "owner"):
            self.assertNotIn(bad, text, bad)

    def test_nothing_sent(self):
        self.assertEqual(insights.report([]), ["No emails sent yet - nothing to analyse."])

    def test_wilson(self):
        lo, hi = insights.wilson(18, 60)
        self.assertTrue(0.19 < lo < 0.21 and 0.42 < hi < 0.44)


if __name__ == "__main__":
    unittest.main()


class ZeroAverage(unittest.TestCase):
    def test_nothing_is_better_than_a_zero_average_by_rounding(self):
        rows = [{"replied": False, "viewed": False, "engaged": False, "keen": False, "won": False, "dims": {"Trade": t}}
                for t in ["Roofing"] * 40 + ["Building"] * 40]
        text = "\n".join(insights.compare("Replies", rows, "Trade"))
        self.assertNotIn("BETTER", text)
        self.assertNotIn("WORSE", text)
