"""client_speed.py: only live client sites are checked, the middle of three runs is kept, slips are flagged."""

import csv
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock

import client_speed as cs


def client(outreach: Path, folder: str, domain: str, published: bool = True) -> None:
    d = outreach / "sites" / folder
    d.mkdir(parents=True)
    (d / "site.json").write_text(json.dumps({"domain": domain}), encoding="utf-8")
    if published:
        (d / "publish.json").write_text("{}", encoding="utf-8")


def psi(scores: dict[str, list[int]]):
    """A fake Google: each call for a domain returns its next score."""
    left = {k: list(v) for k, v in scores.items()}

    def run(url, key):
        domain = url.split("//")[1].strip("/")
        return {"_mobile_score": left[domain].pop(0), "_lcp_s": 1.2} if left.get(domain) else {}
    return run


class ClientSpeed(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_only_published_sites_with_a_real_domain(self):
        client(self.out, "kerr-roofing", "kerrroofing.co.uk")
        client(self.out, "draft-only", "draft.co.uk", published=False)
        client(self.out, "unconfirmed", "[Confirm: theirdomain.co.uk]")
        self.assertEqual(cs.live_sites(self.out), [("kerr-roofing", "kerrroofing.co.uk")])

    def test_middle_of_three_runs_so_one_fluke_cant_decide_it(self):
        self.assertEqual(cs.measure("a.co.uk", "k", psi({"a.co.uk": [99, 71, 93]}))[0], 93)
        self.assertEqual(cs.measure("a.co.uk", "k", psi({"a.co.uk": [95, 88]}))[0], 88)  # two runs: the lower
        self.assertIsNone(cs.measure("a.co.uk", "k", psi({})))

    def test_under_90_or_a_5_point_drop_is_flagged_and_texted(self):
        self.assertEqual(cs.verdict(96, 97), "")
        self.assertEqual(cs.verdict(89, None), "under 90")
        self.assertEqual(cs.verdict(91, 98), "down 7 since last time")

        client(self.out, "kerr-roofing", "kerrroofing.co.uk")
        client(self.out, "smith-drives", "smithdriveways.co.uk")
        with (self.out / cs.LOG).open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=cs.FIELDS)
            w.writeheader()
            w.writerow({"date": "2026-09-01", "folder": "smith-drives", "domain": "smithdriveways.co.uk", "mobile_score": 95, "lcp_s": 1.1})
        fake = psi({"kerrroofing.co.uk": [96, 97, 95], "smithdriveways.co.uk": [84, 86, 83]})
        with mock.patch.object(cs, "text_me") as texted, redirect_stdout(io.StringIO()) as out:
            code = cs.run(self.out, "k", date(2026, 10, 1), fake)
        self.assertEqual(code, 0)
        self.assertIn("LOOK AT  smith-drives", out.getvalue())
        self.assertIn("(was 95)", out.getvalue())
        texted.assert_called_once_with(["smithdriveways.co.uk: 84 - under 90"])
        rows = list(csv.DictReader((self.out / cs.LOG).open(encoding="utf-8")))
        self.assertEqual([(r["date"], r["folder"], r["mobile_score"]) for r in rows[1:]],
                         [("2026-10-01", "kerr-roofing", "96"), ("2026-10-01", "smith-drives", "84")])

    def test_no_live_sites_says_so(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(cs.run(self.out, "k", run_psi=psi({})), 0)
        self.assertIn("No live client sites yet", out.getvalue())

    def test_panel_button_needs_the_key(self):
        import control_panel as cp
        self.assertIsNone(cp.build_steps({"action": "client_speed"}, {})[0])
        make, err = cp.build_steps({"action": "client_speed"}, {"PAGESPEED_API_KEY": "k"})
        self.assertEqual(make(None), [(cp.CLIENT_SPEED, [])])


if __name__ == "__main__":
    unittest.main()
