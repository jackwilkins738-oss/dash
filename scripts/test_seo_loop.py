"""Offline tests for seo_loop - no Google, no Anthropic, no network.

Run: python -m unittest scripts/test_seo_loop.py
"""

import base64
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

import seo_loop

TODAY = date(2026, 11, 1)
PAGE_HTML = """<html><head><title>How Much Does a Tradesman Website Cost? | Scalar Digital</title>
<meta name="description" content="Real UK prices for a trades website."></head><body>
<h1>How much does a tradesman website cost?</h1>
<p>A landing page is £750 and a five-page site is £2,500. You own it outright. Most builds take 2 weeks.</p>
<details><summary>Do I pay monthly?</summary><p>No.</p></details>
<script>var best = 1</script></body></html>"""
SITEMAP = """<urlset><url><loc>https://www.scalardigital.co.uk</loc></url>
<url><loc>https://www.scalardigital.co.uk/guides/how-much-does-a-tradesman-website-cost</loc></url>
<url><loc>https://www.scalardigital.co.uk/work</loc></url>
<url><loc>https://www.scalardigital.co.uk/privacy</loc></url></urlset>"""
COST = "https://www.scalardigital.co.uk/guides/how-much-does-a-tradesman-website-cost"


def row(page, query, imp, clicks, pos):
    return {"keys": [page, query] if query else [page], "impressions": imp, "clicks": clicks, "position": pos}


class FakeConsole:
    def __init__(self, rows, before=None):
        self._rows, self._before, self.calls = rows, before or [], []

    def property_for(self, site):
        return "sc-domain:scalardigital.co.uk"

    def rows(self, prop, start, end, dims):
        self.calls.append((start, end, dims))
        return self._rows if dims == ["page", "query"] else self._before


class Jwt(unittest.TestCase):
    def test_signs_a_token_google_can_verify(self):
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding, rsa

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
        jwt = seo_loop.signed_jwt({"client_email": "loop@x.iam.gserviceaccount.com", "private_key": pem, "private_key_id": "k1"}, now=1000)
        head, claims, sig = jwt.split(".")

        def unb64(s):
            return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))

        self.assertEqual(json.loads(unb64(head)), {"alg": "RS256", "typ": "JWT", "kid": "k1"})
        c = json.loads(unb64(claims))
        self.assertEqual((c["iss"], c["scope"], c["iat"], c["exp"]), ("loop@x.iam.gserviceaccount.com", seo_loop.SCOPE, 1000, 4600))
        key.public_key().verify(unb64(sig), f"{head}.{claims}".encode(), padding.PKCS1v15(), hashes.SHA256())

    def test_a_bad_key_is_a_plain_error(self):
        with self.assertRaises(seo_loop.LoopError):
            seo_loop.Console({"client_email": "x", "private_key": "nope"}, http=lambda *a: {})


class Token(unittest.TestCase):
    def test_a_ready_token_skips_the_key(self):
        calls = []
        c = seo_loop.Console(token="abc", http=lambda url, data, headers: calls.append((url, headers)) or {"siteEntry": []})
        with self.assertRaises(seo_loop.LoopError):
            c.property_for(seo_loop.SITE)
        self.assertEqual(calls[0][1]["Authorization"], "Bearer abc")
        self.assertTrue(calls[0][0].endswith("/sites"))


class Property(unittest.TestCase):
    def test_prefers_the_domain_property(self):
        sites = [{"siteUrl": "https://www.scalardigital.co.uk/", "permissionLevel": "siteFullUser"},
                 {"siteUrl": "sc-domain:scalardigital.co.uk", "permissionLevel": "siteRestrictedUser"}]
        self.assertEqual(seo_loop.pick_property(sites, seo_loop.SITE), "sc-domain:scalardigital.co.uk")

    def test_url_property_and_unverified(self):
        self.assertEqual(seo_loop.pick_property([{"siteUrl": "https://www.scalardigital.co.uk/", "permissionLevel": "siteOwner"}],
                                                seo_loop.SITE), "https://www.scalardigital.co.uk/")
        with self.assertRaises(seo_loop.LoopError):
            seo_loop.pick_property([{"siteUrl": "sc-domain:scalardigital.co.uk", "permissionLevel": "siteUnverifiedUser"}], seo_loop.SITE)


class Choosing(unittest.TestCase):
    def test_paths(self):
        self.assertEqual(seo_loop.path_of("https://scalardigital.co.uk/work/"), "/work")
        self.assertEqual(seo_loop.path_of("https://www.scalardigital.co.uk/"), "/")
        self.assertIsNone(seo_loop.path_of("https://www.scalardigital.co.uk/for/kerr-roofing"))
        self.assertIsNone(seo_loop.path_of("https://example.com/work"))
        self.assertEqual(seo_loop.sitemap_paths(SITEMAP), {"/", "/guides/how-much-does-a-tradesman-website-cost", "/work"})

    def test_nearly_there_phrases_and_poor_click_rates_win(self):
        rows = [row(COST, "tradesman website cost", 40, 0, 9.0), row(COST, "website price uk", 2, 0, 12.0),
                row(COST, "scalar digital", 10, 5, 1.0),
                row("https://www.scalardigital.co.uk/work", "web design", 60, 0, 3.0),  # page one, nobody clicks
                row("https://www.scalardigital.co.uk/process", "how builds work", 30, 0, 50.0)]  # too far back
        pages = seo_loop.summarise(rows)
        self.assertEqual(pages["/guides/how-much-does-a-tradesman-website-cost"]["impressions"], 52)
        self.assertEqual(seo_loop.opportunity(pages["/guides/how-much-does-a-tradesman-website-cost"]), 40)
        self.assertEqual(seo_loop.opportunity(pages["/work"]), 60)
        self.assertEqual(seo_loop.opportunity(pages["/process"]), 0)
        live = {"/work", "/guides/how-much-does-a-tradesman-website-cost", "/process"}
        self.assertEqual(seo_loop.choose(pages, live, {}, TODAY), ["/work", "/guides/how-much-does-a-tradesman-website-cost"])
        # A page changed recently rests; one not in the sitemap is never touched.
        self.assertEqual(seo_loop.choose(pages, live, {"/work": {"changed": "2026-10-20"}}, TODAY),
                         ["/guides/how-much-does-a-tradesman-website-cost"])
        self.assertEqual(seo_loop.choose(pages, {"/process"}, {}, TODAY), [])


class Checking(unittest.TestCase):
    def setUp(self):
        self.facts = seo_loop.page_facts(PAGE_HTML)

    def test_reads_the_page(self):
        self.assertEqual(self.facts["h1"], "How much does a tradesman website cost?")
        self.assertEqual(self.facts["description"], "Real UK prices for a trades website.")
        self.assertEqual(self.facts["questions"], ["Do I pay monthly?"])
        self.assertNotIn("var best", self.facts["text"])

    def test_keeps_a_good_draft(self):
        fix, dropped = seo_loop.check({
            "title": "Tradesman Website Cost: UK Prices From £750",
            "description": "What a trades website really costs in the UK: £750 for a landing page, £2,500 for five pages, and you own it outright.",
            "faqs": [{"q": "How long does a build take?", "a": "Most builds take 2 weeks from the go-ahead to going live."}],
        }, self.facts)
        self.assertEqual(dropped, [])
        self.assertEqual(set(fix), {"title", "description", "faqs"})

    def test_drops_made_up_numbers_hype_links_and_bad_lengths(self):
        fix, dropped = seo_loop.check({
            "title": "The Best Tradesman Website Prices in the Whole of the UK",
            "description": "Builds from £499, live in 3 days. See www.example.com for more about what you get for the money spent.",
            "faqs": [{"q": "Do I pay monthly?", "a": "No, there is nothing to pay monthly at all for the site."},
                     {"q": "Is it fast", "a": "Yes it is very fast on a phone and on a laptop too."}],
        }, self.facts)
        self.assertEqual(fix, {})
        text = " ".join(dropped)
        for why in ("says 'best'", "title is", "number £499", "number 3", "has a link", "page already asks it", "isn't a short question"):
            self.assertIn(why, text)

    def test_unchanged_title_is_not_a_change(self):
        fix, _ = seo_loop.check({"title": "How Much Does a Tradesman Website Cost?"}, self.facts)
        self.assertEqual(fix, {})

    def test_parse_json(self):
        self.assertEqual(seo_loop.parse_json('Here:\n{"title": "x"}\n'), {"title": "x"})
        self.assertEqual(seo_loop.parse_json("no json"), {})

    def test_merge_keeps_the_newest_faqs(self):
        entries = {"/a": {"title": "Old", "faqs": [{"q": f"Q{i}?", "a": "a"} for i in range(4)], "changed": "2026-01-01"}}
        out = seo_loop.merge(entries, "/a", {"description": "D", "faqs": [{"q": "New?", "a": "b"}]}, TODAY)
        self.assertEqual(out["/a"]["title"], "Old")
        self.assertEqual(out["/a"]["description"], "D")
        self.assertEqual([f["q"] for f in out["/a"]["faqs"]], ["Q1?", "Q2?", "Q3?", "New?"])
        self.assertEqual(out["/a"]["changed"], "2026-11-01")


class Run(unittest.TestCase):
    def fetch(self, url):
        return SITEMAP if url.endswith("sitemap.xml") else PAGE_HTML

    def test_end_to_end(self):
        rows = [row(COST, "how much is a website for a builder", 40, 1, 11.0)]
        before = [row(COST + "/", None, 10, 0, 30.0)]
        console = FakeConsole(rows, before)
        drafts = []

        def draft(path, facts, page):
            drafts.append(path)
            return {"title": "Tradesman Website Cost: UK Prices From £750", "description": "x"}

        with tempfile.TemporaryDirectory() as d:
            seo = Path(d) / "seo.json"
            seo.write_text(json.dumps({"/guides/how-much-does-a-tradesman-website-cost": {"title": "T", "changed": "2026-08-01"}}))
            logs = []
            res = seo_loop.run({}, TODAY, console, self.fetch, draft, seo, logs.append)
            saved = json.loads(seo.read_text())
        path = "/guides/how-much-does-a-tradesman-website-cost"
        self.assertEqual(res["changed"], [path])
        self.assertEqual(saved[path], {"title": "Tradesman Website Cost: UK Prices From £750", "changed": "2026-11-01"})
        # Search phrases never reach the log or the (public) pull request - only the private message.
        for public in [*logs, res["summary"]]:
            self.assertNotIn("for a builder", public)
        self.assertIn("for a builder", res["message"])
        self.assertIn("description: description is 1 characters", res["summary"])
        self.assertIn("before 0 clicks, pos 30.0 -> now 1 clicks, pos 11.0", res["message"])

    def test_no_data_writes_nothing(self):
        with tempfile.TemporaryDirectory() as d:
            seo = Path(d) / "seo.json"
            res = seo_loop.run({}, TODAY, FakeConsole([]), self.fetch, lambda *a: {}, seo, lambda *_: None)
            self.assertFalse(seo.exists())
        self.assertEqual(res["changed"], [])
        self.assertIn("Not enough search data", res["message"])

    def test_missing_secrets(self):
        with self.assertRaises(seo_loop.LoopError):
            seo_loop.run({}, TODAY)


if __name__ == "__main__":
    unittest.main()
