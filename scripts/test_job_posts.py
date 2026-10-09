"""Offline tests for job posts (job_posts.py): honest drafts, and only approved posts ever go live."""

import json
import tempfile
import unittest
from pathlib import Path

import job_posts as jp

TENANT = "abdc6408-1fd5-4fb6-9c4c-53600b571a6d"
PHOTO = "https://abcd.supabase.co/storage/v1/object/public/project-photos/t/1.jpg"
SECRET = "s" * 40
BODY = " ".join(["We replaced the roof on this house."] * 15) + "\n\nGet in touch through the website if you need the same."


def site_cfg():
    return {"business": "Kerr Roofing", "trade": "roofing", "domain": "kerrroofing.co.uk",
            "services": [{"name": "Roof repairs"}], "areas": [{"town": "Maidstone"}, {"town": "Tunbridge Wells"}],
            "dashboard": {"tenant_id": TENANT, "site_key": "4bdac492-8a7d-4826-8e25-059326f5c07f"}}


def ai(answer: dict):
    seen = {}

    def request(path, key, payload):
        seen["payload"] = payload
        return {"content": [{"type": "text", "text": "Here you go:\n" + json.dumps(answer)}]}
    return request, seen


GOOD = {"title": "New roof in Maidstone", "body": BODY, "google_post": "We've just finished a new roof in Maidstone. Get a free quote.",
        "alts": ["New roof"]}
JOB = {"project_id": "11111111-2222-3333-4444-555555555555", "project_type": "Re-roof", "location": "14 Acacia Ave, Maidstone ME14 2AB",
       "photos": [{"url": PHOTO, "caption": "Finished roof"}, {"url": "https://evil.example/x.jpg", "caption": "x"}]}


class Drafts(unittest.TestCase):
    def test_town_only_never_the_address(self):
        areas = site_cfg()["areas"]
        self.assertEqual(jp.town_for("14 Acacia Ave, Maidstone ME14 2AB", areas), "Maidstone")
        self.assertEqual(jp.town_for("Tunbridge Wells", areas), "Tunbridge Wells")
        self.assertIsNone(jp.town_for("Ashford", areas))
        self.assertIsNone(jp.town_for(None, areas))

    def test_a_good_draft(self):
        request, seen = ai(GOOD)
        d, why = jp.draft(JOB, site_cfg(), "k", "some-model", request)
        self.assertEqual(why, "")
        self.assertEqual(d["town"], "Maidstone")
        self.assertEqual(d["slug"], "new-roof-in-maidstone")
        self.assertEqual(d["photos"], [{"url": PHOTO, "alt": "New roof"}])
        prompt = json.dumps(seen["payload"])
        self.assertNotIn("Acacia", prompt)  # the street address never reaches Claude
        self.assertNotIn("evil.example", prompt)

    def test_rule_breaking_drafts_are_thrown_away(self):
        for change, why in [({"body": BODY + " It cost £4,000."}, "mentions money"),
                            ({"google_post": "Call 07700 900123 today."}, "has a phone number"),
                            ({"body": "Too short."}, "words"),
                            ({"google_post": "See www.kerr.co.uk"}, "has a link or email")]:
            request, _ = ai({**GOOD, **change})
            d, reason = jp.draft(JOB, site_cfg(), "k", "m", request)
            self.assertIsNone(d)
            self.assertIn(why, reason)

    def test_unreadable_answer(self):
        d, reason = jp.draft(JOB, site_cfg(), "k", "m", lambda *a: {"content": [{"type": "text", "text": "sorry"}]})
        self.assertIsNone(d)
        self.assertIn("readable", reason)


class Sync(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.outreach = Path(self.tmp.name)
        folder = self.outreach / "sites" / "kerr-roofing"
        folder.mkdir(parents=True)
        (folder / "site.json").write_text(json.dumps(site_cfg()), encoding="utf-8")
        unwired = self.outreach / "sites" / "draft-firm"
        unwired.mkdir()
        (unwired / "site.json").write_text(json.dumps({**site_cfg(), "dashboard": {"tenant_id": "[Confirm]", "site_key": ""}}), encoding="utf-8")
        self.calls = []

    def tearDown(self):
        self.tmp.cleanup()

    def api(self, answer):
        def call(method, url, secret, body=None):
            self.calls.append((method, url, body))
            return answer if method == "GET" else {"ok": True, "id": "x"}
        return call

    def test_drafts_due_jobs_and_publishes_approved_posts(self):
        approved = {"id": "p1", "status": "approved", "slug": "new-roof-in-maidstone", "title": "New roof in Maidstone", "body": "b"}
        live = {"id": "p0", "status": "published", "slug": "old-job", "title": "Old job", "body": "b"}
        built, published = [], []
        request, _ = ai(GOOD)
        lines = jp.sync(self.outreach, {"PROSPECTS_API_SECRET": SECRET, "ANTHROPIC_API_KEY": "k", "AI_MODEL": "m"},
                        call=self.api({"due": [JOB], "posts": [approved, live]}), request=request,
                        builder=lambda f: built.append(f.name), publisher=lambda o, f, s: published.append(f))
        self.assertEqual([c[0] for c in self.calls], ["GET", "POST", "PATCH"])  # the unwired site is never asked about
        self.assertIn(TENANT, self.calls[0][1])
        self.assertEqual(self.calls[1][2]["tenant_id"], TENANT)
        self.assertEqual(self.calls[2][2], {"id": "p1", "tenant_id": TENANT, "page_url": "https://kerrroofing.co.uk/work/new-roof-in-maidstone.html"})
        self.assertEqual((built, published), (["kerr-roofing"], ["kerr-roofing"]))
        saved = json.loads((self.outreach / "sites" / "kerr-roofing" / "job-posts.json").read_text(encoding="utf-8"))
        self.assertEqual([p["id"] for p in saved], ["p1", "p0"])
        self.assertTrue(any("drafted" in line for line in lines))
        self.assertTrue(any("now live on kerrroofing.co.uk" in line for line in lines))

    def test_nothing_approved_nothing_published(self):
        lines = jp.sync(self.outreach, {"PROSPECTS_API_SECRET": SECRET}, call=self.api({"due": [], "posts": []}),
                        builder=lambda f: self.fail("built"), publisher=lambda *a: self.fail("published"))
        self.assertEqual(lines, [])

    def test_a_failed_publish_never_marks_posts_live(self):
        approved = {"id": "p1", "status": "approved", "slug": "a", "title": "A", "body": "b"}

        def boom(*a):
            raise RuntimeError("Cloudflare said no")
        lines = jp.sync(self.outreach, {"PROSPECTS_API_SECRET": SECRET}, call=self.api({"due": [], "posts": [approved]}),
                        builder=lambda f: None, publisher=boom)
        self.assertNotIn("PATCH", [c[0] for c in self.calls])
        self.assertIn("not published - Cloudflare said no", lines[0])

    def test_no_ai_key_says_so(self):
        lines = jp.sync(self.outreach, {"PROSPECTS_API_SECRET": SECRET}, call=self.api({"due": [JOB], "posts": []}))
        self.assertIn("ANTHROPIC_API_KEY", lines[0])

    def test_no_secret_does_nothing(self):
        self.assertEqual(jp.sync(self.outreach, {}, call=self.api({})), [])
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
