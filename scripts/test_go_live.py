"""go_live.py: the DNS snapshot catches a lost email record, and the launch checks catch a bad launch."""

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import go_live as gl

D = "kerrroofing.co.uk"

# Their DNS at the registrar, before the switch: Google Workspace email.
BEFORE = {
    (D, "NS"): ["ns1.registrar.net", "ns2.registrar.net"],
    (D, "MX"): ["1 aspmx.l.google.com", "5 alt1.aspmx.l.google.com"],
    (D, "TXT"): ["v=spf1 include:_spf.google.com ~all", "google-site-verification=abc"],
    (D, "A"): ["192.0.2.10"],
    (f"_dmarc.{D}", "TXT"): ["v=DMARC1; p=none"],
    (f"google._domainkey.{D}", "TXT"): ["v=DKIM1; k=rsa; p=MIIB"],
    (f"mail.{D}", "CNAME"): ["ghs.googlehosted.com"],
}


def dns(table):
    return lambda name, rtype: list(table.get((name, rtype), []))


def site(pages):
    """A fake web: url -> (status, final url, body); anything else is a 404."""
    def get(url):
        return pages.get(url, (404, url, "Not found"))
    return get


GOOD_HOME = '<html><head><meta charset="utf-8"></head><body><script src="https://admin.scalardigital.co.uk/track.js" defer></script></body></html>'
GOOD = {
    f"https://{D}/": (200, f"https://{D}/", GOOD_HOME),
    f"https://www.{D}/": (200, f"https://{D}/", GOOD_HOME),
    f"http://{D}/": (200, f"https://{D}/", GOOD_HOME),
    f"https://{D}/sitemap.xml": (200, "", '<?xml version="1.0"?><urlset></urlset>'),
    f"https://{D}/robots.txt": (200, "", "User-agent: *\nAllow: /\n"),
    f"https://{D}/contact.html": (200, "", '<form class="quote-form" data-lead-form>'),
}


class Snapshot(unittest.TestCase):
    def test_reads_email_records_and_names_the_host(self):
        snap = gl.snapshot(D, dns(BEFORE))
        self.assertIn(f"{D} MX", snap["records"])
        self.assertIn(f"google._domainkey.{D} TXT", snap["records"])
        self.assertEqual(gl.email_host(snap["records"], D), "Google Workspace")
        self.assertIn("doesn't receive email", gl.email_host({}, D))

    def test_moving_the_site_is_fine_losing_an_email_record_is_not(self):
        before = gl.snapshot(D, dns(BEFORE))
        moved = dict(BEFORE)
        moved[(D, "NS")] = ["ada.ns.cloudflare.com", "bob.ns.cloudflare.com"]
        moved[(D, "A")] = ["172.66.0.1"]
        self.assertEqual(gl.compare(before, gl.snapshot(D, dns(moved))), [])

        broken = dict(moved)
        del broken[(f"google._domainkey.{D}", "TXT")]  # Cloudflare's import missed the DKIM key
        broken[(D, "TXT")] = ["google-site-verification=abc"]  # and the SPF record
        problems = gl.compare(before, gl.snapshot(D, dns(broken)))
        self.assertTrue(any("google._domainkey" in p and p.startswith("MISSING") for p in problems))
        self.assertTrue(any("v=spf1" in p for p in problems))
        self.assertFalse(any("verification" in p for p in problems))

    def test_first_run_saves_second_run_compares_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as d:
            outreach = Path(d)
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(gl.run_dns(D, outreach, None, False, dns(BEFORE)), 0)
            path = outreach / "dns" / f"{D}.json"
            self.assertTrue(path.exists())
            self.assertIn("Google Workspace", out.getvalue())
            saved = path.read_text(encoding="utf-8")

            lost = {k: v for k, v in BEFORE.items() if k != (D, "MX")}
            with redirect_stdout(io.StringIO()) as out:
                self.assertEqual(gl.run_dns(D, outreach, None, False, dns(lost)), 1)
            self.assertIn("STOP - EMAIL AT RISK", out.getvalue())
            self.assertIn("aspmx.l.google.com", out.getvalue())
            self.assertEqual(path.read_text(encoding="utf-8"), saved)

    def test_snapshot_goes_in_the_client_folder_when_given(self):
        self.assertEqual(gl.snapshot_path(Path("o"), D, "kerr-roofing"), Path("o/sites/kerr-roofing/dns-before.json"))


class Lookup(unittest.TestCase):
    def test_parses_googles_dns_answers(self):
        from unittest import mock
        answer = {"Answer": [
            {"name": f"mail.{D}.", "type": 5, "data": "ghs.googlehosted.com."},  # the CNAME on the way
            {"name": "ghs.googlehosted.com.", "type": 1, "data": "142.250.0.1"},
            {"name": f"{D}.", "type": 16, "data": '"v=spf1 include:_spf.google.com" " ~all"'},
            {"name": f"{D}.", "type": 15, "data": "1 ASPMX.L.GOOGLE.COM."},
        ]}

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with mock.patch.object(gl.urllib.request, "urlopen", lambda *a, **k: Resp(json.dumps(answer).encode())):
            self.assertEqual(gl.lookup(f"mail.{D}", "A"), ["142.250.0.1"])
            self.assertEqual(gl.lookup(D, "TXT"), ["v=spf1 include:_spf.google.com ~all"])
            self.assertEqual(gl.lookup(D, "MX"), ["1 aspmx.l.google.com"])
            self.assertEqual(gl.lookup(f"mail.{D}", "CNAME"), ["ghs.googlehosted.com"])


class SiteChecks(unittest.TestCase):
    def test_a_good_launch_passes_everything(self):
        results = gl.site_checks(D, site(GOOD), days=lambda h: 80)
        self.assertTrue(all(ok for ok, _ in results), [w for ok, w in results if not ok])

    def test_a_draft_left_live_with_no_www_is_caught(self):
        bad = dict(GOOD)
        bad[f"https://{D}/"] = (200, f"https://{D}/", '<meta name="robots" content="noindex"><div class="draft-banner">Draft</div>')
        del bad[f"https://www.{D}/"]
        bad[f"http://{D}/"] = (200, f"http://{D}/", "")
        failed = [w for ok, w in gl.site_checks(D, site(bad), days=lambda h: 80) if not ok]
        self.assertTrue(any("noindex" in w for w in failed))
        self.assertTrue(any("draft banner" in w for w in failed))
        self.assertTrue(any("www" in w for w in failed))
        self.assertTrue(any("https://" in w and "http://" in w for w in failed))
        self.assertTrue(any("track.js" in w for w in failed))

    def test_a_site_that_is_down_is_a_failed_check_not_a_crash(self):
        def down(url):
            raise OSError("connection refused")
        failed = [w for ok, w in gl.site_checks(D, down, days=lambda h: 80) if not ok]
        self.assertTrue(any("doesn't load" in w for w in failed))

    def test_check_reports_ready_and_compares_email_when_a_snapshot_exists(self):
        with tempfile.TemporaryDirectory() as d:
            outreach = Path(d)
            (outreach / "dns").mkdir()
            (outreach / "dns" / f"{D}.json").write_text(json.dumps(gl.snapshot(D, dns(BEFORE))), encoding="utf-8")
            with redirect_stdout(io.StringIO()) as out:
                code = gl.run_check(D, outreach, None, dns(BEFORE), site(GOOD), lambda h: 80)
            self.assertEqual(code, 0, out.getvalue())
            self.assertIn("EMAIL OK", out.getvalue())
            self.assertIn(f"READY: {D}", out.getvalue())


class PanelButtons(unittest.TestCase):
    def test_buttons_run_go_live_with_the_domain_and_folder(self):
        import control_panel as cp
        make, err = cp.build_steps({"action": "dns_snapshot", "golive_domain": "https://www.KerrRoofing.co.uk/", "publish_folder": "kerr-roofing"}, {})
        self.assertEqual(err, "")
        self.assertEqual(make(None), [(cp.GO_LIVE, ["dns", D, "--folder", "kerr-roofing"])])
        make, err = cp.build_steps({"action": "launch_check", "golive_domain": D}, {})
        self.assertEqual(make(None), [(cp.GO_LIVE, ["check", D])])
        self.assertIsNone(cp.build_steps({"action": "launch_check", "golive_domain": "not a domain"}, {})[0])


if __name__ == "__main__":
    unittest.main()
