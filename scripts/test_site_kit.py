"""Offline tests for the client-site starter kit (site_kit.py): what a build must always get right."""

import json
import re
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

import site_kit as sk

TENANT = "abdc6408-1fd5-4fb6-9c4c-53600b571a6d"
KEY = "4bdac492-8a7d-4826-8e25-059326f5c07f"


def config(**over) -> dict:
    cfg = {
        "business": "Kerr & Sons <Roofing>",
        "trade": "roofing",
        "title_trade": "Roofers",
        "domain": "kerrroofing.co.uk",
        "headline": "Roofing done properly, first time.",
        "lede": "New roofs and repairs from a family firm.",
        "phone": "07700 900123",
        "whatsapp": "447700900123",
        "email": "office@kerrroofing.co.uk",
        "colour": "#f4c542",  # too light for white text: the build must darken it
        "hours": "Mon-Fri 8am-6pm",
        "years_trading": 22,
        "services": [{"name": "Roof repairs", "summary": "Leaks found and fixed."}, {"name": "Flat roofs", "summary": "GRP and EPDM."}],
        "areas": [{"town": "Maidstone", "note": "Our home town."}, {"town": "Tunbridge Wells"}],
        "reviews": {"google_url": "https://g.page/r/x", "rating": 4.9, "count": 57, "quotes": [{"text": "Great <b>job</b>", "name": "Sue"}]},
        "faqs": [{"q": "Free quotes?", "a": "Yes."}],
        "gallery": {"photos": [], "from_dashboard": True},
        "company": {"legal_name": "Kerr & Sons Roofing Ltd", "number": "01234567", "registered_office": "12 High St, Maidstone"},
        "dashboard": {"tenant_id": TENANT, "site_key": KEY},
        "redirects": [["/our-services", "/services.html"]],
    }
    cfg.update(over)
    return cfg


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ld, self._in_ld = [], [], False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href", "").startswith("/"):
            self.links.append(a["href"])
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld = True

    def handle_endtag(self, tag):
        self._in_ld = False if tag == "script" else self._in_ld

    def handle_data(self, data):
        if self._in_ld:
            self.ld.append(data)


class SiteKit(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name) / "kerr-roofing"
        self.folder.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, draft=False, **over):
        (self.folder / "site.json").write_text(json.dumps(config(**over)), encoding="utf-8")
        return sk.build(self.folder, draft=draft)

    def page(self, rel):
        return (self.folder / "site" / rel).read_text(encoding="utf-8")

    def test_every_page_and_a_page_per_town(self):
        pages = self.build()["pages"]
        for p in ["index.html", "services.html", "gallery.html", "reviews.html", "contact.html", "thanks.html",
                  "privacy.html", "404.html", "areas/index.html", "areas/maidstone.html", "areas/tunbridge-wells.html"]:
            self.assertIn(p, pages)
        for f in ["site.css", "sitemap.xml", "robots.txt", "_redirects", "_headers", "favicon.svg"]:
            self.assertTrue((self.folder / "site" / f).exists(), f)

    def test_no_broken_internal_links(self):
        self.build()
        site = self.folder / "site"
        for html_file in site.rglob("*.html"):
            parser = Links()
            parser.feed(html_file.read_text(encoding="utf-8"))
            for href in parser.links:
                path = href.split("#")[0].split("?")[0]
                target = site / path.lstrip("/")
                if path.endswith("/"):
                    target = target / "index.html"
                self.assertTrue(target.exists(), f"{html_file.relative_to(site)} links to missing {href}")

    def test_structured_data_is_valid_and_honest(self):
        self.build()
        parser = Links()
        parser.feed(self.page("index.html"))
        blocks = [json.loads(b) for b in parser.ld]
        biz = next(b for b in blocks if b["@type"] == "RoofingContractor")
        self.assertEqual(biz["name"], "Kerr & Sons <Roofing>")
        self.assertEqual(biz["telephone"], "+447700900123")
        self.assertEqual([a["name"] for a in biz["areaServed"]], ["Maidstone", "Tunbridge Wells"])
        self.assertEqual(biz["aggregateRating"], {"@type": "AggregateRating", "ratingValue": 4.9, "reviewCount": 57})
        self.assertTrue(any(b["@type"] == "FAQPage" for b in blocks))

    def test_no_rating_is_ever_invented(self):
        self.build(reviews={"quotes": []})
        self.assertNotIn("aggregateRating", self.page("index.html"))
        self.assertNotIn("★", self.page("index.html"))

    def test_a_rating_without_a_count_is_refused(self):
        with self.assertRaises(sk.SiteError):
            self.build(reviews={"rating": 5})

    def test_everything_typed_is_escaped(self):
        self.build()
        home = self.page("index.html")
        self.assertNotIn("<Roofing>", home.split("</head>")[1])  # visible HTML escaped (JSON-LD keeps the real name)
        self.assertIn("Kerr &amp; Sons &lt;Roofing&gt;", home)
        self.assertNotIn("<b>job</b>", home)

    def test_json_ld_cant_close_its_script_tag(self):
        self.build(business="Evil </script><script>alert(1)</script>")
        home = self.page("index.html")
        self.assertNotIn("</script><script>alert(1)", home)

    def test_enquiry_form_is_wired_to_the_dashboard(self):
        self.build()
        contact = self.page("contact.html")
        self.assertIn("data-lead-form", contact)
        self.assertIn('data-lead-redirect="/thanks.html"', contact)
        for field in ('name="name"', 'name="phone"', 'name="email"', 'name="message"', 'name="photos"'):
            self.assertIn(field, contact)
        self.assertIn(f'data-tenant="{TENANT}" data-site-key="{KEY}"', contact)
        self.assertIn("track.js", self.page("index.html"))

    def test_live_gallery_and_reviews_use_the_dashboard_hooks(self):
        self.build()
        gallery, reviews = self.page("gallery.html"), self.page("reviews.html")
        self.assertIn('id="project-gallery"', gallery)
        self.assertIn(f'gallery.js" data-tenant="{TENANT}"', gallery)
        self.assertIn('id="testimonials-list"', reviews)
        self.assertIn(f'testimonials.js" data-tenant="{TENANT}"', reviews)

    def test_nothing_unconfirmed_goes_live(self):
        with self.assertRaises(sk.SiteError) as e:
            self.build(guarantee="[Confirm with the client: years]")
        self.assertIn("guarantee", str(e.exception))

    def test_a_site_that_catches_no_enquiries_is_refused(self):
        with self.assertRaises(sk.SiteError) as e:
            self.build(dashboard={})
        self.assertIn("enquiry form goes nowhere", str(e.exception))

    def test_draft_builds_but_is_hidden_from_google(self):
        result = self.build(draft=True, guarantee="[Confirm: years]", dashboard={})
        self.assertTrue(result["draft"])
        self.assertIn('<meta name="robots" content="noindex">', self.page("index.html"))
        self.assertIn("Draft for review", self.page("index.html"))
        self.assertIn("Disallow: /", self.page("robots.txt"))

    def test_brand_colour_is_made_readable(self):
        self.build()
        brand = re.search(r"--brand-in: (#[0-9a-f]{6})", self.page("site.css")).group(1)
        self.assertNotEqual(brand, "#f4c542")
        self.assertGreaterEqual(1.05 / (sk._luminance(brand) + 0.05), 4.5)

    def test_company_details_a_limited_company_must_show(self):
        self.build()
        self.assertIn("company no. 01234567", self.page("index.html"))
        self.assertIn("Registered office: 12 High St, Maidstone", self.page("contact.html"))

    def test_sitemap_redirects_and_headers(self):
        self.build()
        sitemap = self.page("sitemap.xml")
        self.assertIn("https://kerrroofing.co.uk/areas/tunbridge-wells.html", sitemap)
        self.assertNotIn("thanks.html", sitemap)
        self.assertNotIn("404.html", sitemap)
        self.assertIn("/our-services /services.html 301", self.page("_redirects"))
        self.assertIn("X-Content-Type-Options: nosniff", self.page("_headers"))
        self.assertIn("Sitemap: https://kerrroofing.co.uk/sitemap.xml", self.page("robots.txt"))

    def test_thanks_and_404_stay_out_of_search(self):
        self.build()
        for p in ("thanks.html", "404.html"):
            self.assertIn('content="noindex"', self.page(p))
        self.assertNotIn('content="noindex"', self.page("index.html"))

    def test_bad_config_explains_itself(self):
        problems = sk.validate(config(colour="blue", domain="https://x.co.uk/", phone="123", areas=[], services=[]), self.folder)
        text = " ".join(problems)
        for word in ("colour", "domain", "phone", "areas", "services"):
            self.assertIn(word, text)

    def test_missing_photo_is_caught(self):
        with self.assertRaises(sk.SiteError) as e:
            self.build(hero_photo="client-files/nope.jpg")
        self.assertIn("nope.jpg", str(e.exception))

    def test_init_writes_a_starter_that_wont_build_until_confirmed(self):
        sk.init(self.folder)
        with self.assertRaises(sk.SiteError):
            sk.build(self.folder)
        with self.assertRaises(sk.SiteError):
            sk.init(self.folder)  # never overwrites work


class PanelButtons(unittest.TestCase):
    """Build site / Publish site on the panel: the right command, and never a draft made live."""

    def setUp(self):
        import control_panel as cp

        self.cp = cp
        self.tmp = tempfile.TemporaryDirectory()
        self.old = cp.OUTREACH
        cp.OUTREACH = Path(self.tmp.name)
        (cp.OUTREACH / "sites" / "kerr-roofing").mkdir(parents=True)

    def tearDown(self):
        self.cp.OUTREACH = self.old
        self.tmp.cleanup()

    def steps(self, **body):
        make, err = self.cp.build_steps({"publish_folder": "kerr-roofing", **body}, {"CLOUDFLARE_API_TOKEN": "t"})
        return (make(None) if make else None), err

    def test_build_starts_with_init_then_builds(self):
        steps, _ = self.steps(action="build_site")
        self.assertEqual(steps[0][1], ["init", "kerr-roofing"])
        (self.cp.OUTREACH / "sites" / "kerr-roofing" / "site.json").write_text("{}")
        self.assertEqual(self.steps(action="build_site")[0][0][1], ["build", "kerr-roofing"])
        self.assertEqual(self.steps(action="build_site", build_draft=True)[0][0][1], ["build", "kerr-roofing", "--draft"])

    def test_build_needs_a_real_folder(self):
        self.assertIsNone(self.steps(action="build_site", publish_folder="../etc")[0])
        self.assertIn("Draft their site", self.steps(action="build_site", publish_folder="nobody")[1])

    def test_a_draft_build_cant_be_published(self):
        site = self.cp.OUTREACH / "sites" / "kerr-roofing" / "site"
        site.mkdir()
        (site / "index.html").write_text('<div class="draft-banner">Draft</div>')
        steps, err = self.steps(action="publish_site")
        self.assertIsNone(steps)
        self.assertIn("draft build", err)
        (site / "index.html").write_text("<h1>Live</h1>")
        self.assertIsNotNone(self.steps(action="publish_site")[0])


class StarterFromOnboarding(unittest.TestCase):
    """What the client typed on their onboarding page lands in the right place in site.json."""

    TOLD = {
        "services": "Flat roofs - GRP and EPDM, 20-year guarantee\nRoof repairs",
        "areas": "Guildford\nWoking",
        "years_trading": "Since 2009",
        "whatsapp": "07700 900456",
        "show_address": "Unit 4, Mill Lane, Guildford, GU1 2AB",
        "reviews_link": "https://g.page/r/kerr",
        "review_quotes": '"Brilliant job, tidy and on time" - Sue, Guildford\n\nFixed our leak the same day. - Tom',
        "free_quotes": "Yes",
        "lead_time": "Visit within a week",
        "call_outs": "Yes, 7 days a week for leaks.",
        "guarantee": "10 years on new roofs",
        "domain": "https://www.kerrroofing.co.uk/",
    }

    def cfg(self, **told):
        import site_draft

        return sk.starter_config({"business": "Kerr Roofing", "trade": "Roofing", "phone": "01483 111222",
                                  "told": {**self.TOLD, **told}, "copy": site_draft.TRADE_COPY["roofing"]})

    def test_the_basics_they_typed(self):
        c = self.cfg()
        self.assertEqual(c["domain"], "kerrroofing.co.uk")
        self.assertEqual(c["whatsapp"], "447700900456")
        self.assertEqual(c["years_trading"], sk.date.today().year - 2009)
        self.assertEqual(c["services"][0], {"name": "Flat roofs", "summary": "GRP and EPDM, 20-year guarantee", "details": "", "photo": ""})
        self.assertEqual(c["services"][1]["name"], "Roof repairs")
        self.assertNotIn("[Confirm", c["services"][1]["summary"])  # the trade's own line fills a gap, not their words

    def test_address_is_kept_not_thrown_away(self):
        self.assertEqual(self.cfg()["address"], {"show": True, "street": "Unit 4, Mill Lane", "town": "Guildford", "postcode": "GU1 2AB"})
        self.assertEqual(self.cfg(show_address="")["address"], {"show": False})
        self.assertIn("[Confirm", self.cfg(show_address="The yard behind the pub")["address"]["town"])

    def test_reviews_and_faqs_come_from_them(self):
        c = self.cfg()
        self.assertEqual(c["reviews"]["google_url"], "https://g.page/r/kerr")
        self.assertEqual(c["reviews"]["quotes"], [{"text": "Brilliant job, tidy and on time", "name": "Sue, Guildford"},
                                                  {"text": "Fixed our leak the same day.", "name": "Tom"}])
        self.assertIsNone(c["reviews"]["rating"])  # quotes never become an invented star rating
        answers = {f["q"]: f["a"] for f in c["faqs"]}
        self.assertEqual(answers["Do you give free quotes?"], "Yes - quotes are free and there's no obligation. Visit within a week.")
        self.assertEqual(answers["Can you help with an emergency leak?"], "Yes, 7 days a week for leaks.")
        self.assertEqual(answers["Is the work guaranteed?"], "Yes - 10 years on new roofs.")

    def test_a_non_google_reviews_link_isnt_called_google(self):
        c = self.cfg(reviews_link="https://www.checkatrade.com/trades/kerr")
        self.assertEqual(c["reviews"]["google_url"], "")
        self.assertEqual(c["social"], ["https://www.checkatrade.com/trades/kerr"])

    def test_unanswered_stays_to_confirm(self):
        c = self.cfg(free_quotes="", call_outs="", guarantee="", years_trading="a good while", whatsapp="")
        self.assertTrue(all("[Confirm" in f["a"] for f in c["faqs"]))
        self.assertIsNone(c["years_trading"])
        self.assertEqual(c["whatsapp"], "")  # a landline isn't a WhatsApp number

    def test_years_parsing(self):
        for text, want in (("15 years", 15), ("over 20 yrs", 20), ("est. 1998", 2026 - 1998), ("2030", None), ("ages", None)):
            self.assertEqual(sk._years(text, 2026), want, text)


if __name__ == "__main__":
    unittest.main()
