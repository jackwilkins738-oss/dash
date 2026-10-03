"""research: the card you read before you dial - only confident facts, never a guessed director."""

import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

import research

PAGE = """<html><head><title>Kerr Roofing | Roofers in Guildford</title></head><body>
<h1>Kerr Roofing</h1><p>Family-run roofers, established 2009. Fully insured, 10-year guarantee on all work.</p>
<h2>Flat roofs</h2><h2>Slate roofing</h2><p>NFRC members.</p></body></html>"""


def fetch(url):
    return PAGE, url


def write(path, fields, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


class Research(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp())
        write(self.d / "teardown-log.csv", ["website", "result", "mobile_score", "lcp_s", "top_issue"],
              [{"website": "kerrroofing.co.uk", "result": "ok", "mobile_score": "38", "lcp_s": "6.1", "top_issue": "no enquiry form"}])

    def get(self, path, key):
        if path.endswith("/officers?items_per_page=20"):
            return {"items": [{"name": "KERR, John Andrew", "officer_role": "director"},
                              {"name": "SMITH, Ann", "officer_role": "director", "resigned_on": "2020-01-01"},
                              {"name": "ACME SECRETARIES LTD", "officer_role": "secretary"}]}
        return {"company_name": "KERR ROOFING LIMITED", "company_status": "active", "date_of_creation": "2009-03-14"}

    def test_full_card(self):
        write(self.d / "company-lookups.csv", ["website", "result", "number", "registered_name"],
              [{"website": "kerrroofing.co.uk", "result": "company", "number": "06812345", "registered_name": "KERR ROOFING LIMITED"}])
        out = research.research(self.d, "Kerr Roofing", "kerrroofing.co.uk", "Guildford", {"COMPANIES_HOUSE_API_KEY": "k"},
                                fetch=fetch, get=self.get, today=date(2026, 10, 3))
        text = "\n".join(out["lines"])
        self.assertIn("KERR ROOFING LIMITED (06812345), active, 17 years old", text)
        self.assertIn("Directors: John Andrew Kerr", text)
        self.assertNotIn("Smith", text)
        self.assertIn("family-run", text)
        self.assertIn("says they're insured", text)
        self.assertIn("10-year guarantee", text)
        self.assertIn("Speed check: 38/100 on mobile, 6.1s to load - worst: no enquiry form", text)
        self.assertIn("Kerr+Roofing+Guildford+reviews", out["google"])
        # Cached: a second look doesn't fetch again.
        again = research.research(self.d, "Kerr Roofing", "kerrroofing.co.uk", "Guildford", {}, fetch=None, get=None)
        self.assertEqual(again["lines"], out["lines"])

    def test_an_unsure_match_is_never_shown(self):
        write(self.d / "company-lookups.csv", ["website", "result", "number"], [{"website": "kerrroofing.co.uk", "result": "unsure", "number": "999"}])
        lines = research.company(self.d, "Kerr Roofing", "kerrroofing.co.uk", "Guildford", None, "", get=self.get)
        self.assertIn("not found - probably a sole trader", lines[0])

    def test_dissolved_is_flagged(self):
        write(self.d / "company-lookups.csv", ["website", "result", "number"], [{"website": "kerrroofing.co.uk", "result": "closed", "number": "1"}])
        lines = research.company(self.d, "Kerr Roofing", "kerrroofing.co.uk", "", None, "k",
                                 get=lambda p, k: {"company_status": "dissolved"} if "officers" not in p else {})
        self.assertTrue(any("check they're still trading" in ln for ln in lines))

    def test_site_down(self):
        lines, html = research.homepage("kerrroofing.co.uk", fetch=lambda url: (None, None))
        self.assertIsNone(html)
        self.assertIn("couldn't load", lines[0])


if __name__ == "__main__":
    unittest.main()
