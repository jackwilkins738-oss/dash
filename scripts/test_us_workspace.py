"""The US workspace (outreach-us/): its own folder, Google Maps in the US, CAN-SPAM instead of PECR,
no letters, no pound-and-VAT quotes, and no email without a postal address."""

import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import ai_reply
import email_batches as eb
import find_prospects
import places_finder
import push_prospects
import saved_replies
import send_email as se
import workspace
from test_send_email import FIRMS, TODAY, FakeSMTP


def write(path: Path, fields: list[str], rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


class Folder(unittest.TestCase):
    def test_the_folder_name_decides_the_market(self):
        self.assertEqual(workspace.market(Path("/x/outreach")), "uk")
        self.assertEqual(workspace.market(Path("/x/outreach-us")), "us")
        self.assertEqual(workspace.market(Path("/x/outreach-xx")), "uk")  # unknown market: the UK's rules
        self.assertEqual(workspace.market(Path("/tmp/somewhere")), "uk")

    def test_outreach_dir_follows_outreach_dir_setting(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"OUTREACH_DIR": str(Path(tmp) / "outreach-us")}):
            self.assertEqual(workspace.outreach_dir(), Path(tmp) / "outreach-us")
            self.assertEqual(workspace.market(), "us")
        with mock.patch.dict(os.environ, {"OUTREACH_DIR": ""}):
            self.assertEqual(workspace.outreach_dir().name, "outreach")
            self.assertEqual(workspace.market(), "uk")

    def test_money(self):
        self.assertEqual(workspace.money(4500, Path("outreach-us")), "$4,500")
        self.assertEqual(workspace.money(750, Path("outreach")), "£750")


class Finding(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"OUTREACH_DIR": "outreach-us"})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_a_state_stays_with_its_city(self):
        self.assertEqual(find_prospects.split_areas("Provo, UT, Ogden, ut; Salt Lake City, UT"),
                         ["Provo, UT", "Ogden, UT", "Salt Lake City, UT"])
        with mock.patch.dict(os.environ, {"OUTREACH_DIR": ""}):
            self.assertEqual(find_prospects.split_areas("Guildford, GU1"), ["Guildford", "GU1"])

    def test_us_searches_use_us_words_region_and_area_names(self):
        self.assertEqual(places_finder.query_for("hvac", "Provo, UT"), "HVAC contractor in Provo, UT")
        self.assertEqual(places_finder.query_for("roofing", "Provo, UT"), "roofing contractor in Provo, UT")
        self.assertEqual(places_finder.area_label("provo, ut"), "Provo, UT")
        bodies = []
        places_finder.search("plumber in Provo, UT", "k", post=lambda body, key: bodies.append(body) or {})
        self.assertEqual((bodies[0]["regionCode"], bodies[0]["languageCode"]), ("us", "en-US"))

    def test_us_chains_and_lead_sites_are_left_out(self):
        for name in ("Roto-Rooter Plumbing & Water Cleanup", "The Home Depot", "Angi"):
            self.assertFalse(places_finder.keep({"displayName": {"text": name}, "businessStatus": "OPERATIONAL"}, [], []), name)
        self.assertTrue(places_finder.keep({"displayName": {"text": "Wasatch Plumbing"}, "businessStatus": "OPERATIONAL"}, [], []))
        self.assertEqual(places_finder.own_site("https://www.yelp.com/biz/wasatch-plumbing"), "")

    def test_companies_house_is_refused_in_the_us(self):
        with self.assertRaises(SystemExit) as stop:
            find_prospects.main(["--trades", "plumbing", "--areas", "Provo, UT", "--source", "companies"])
        self.assertIn("Google Maps", str(stop.exception))


class Scout(unittest.TestCase):
    def test_us_scout_searches_us_towns_with_us_words_and_counts_no_letters(self):
        import area_scout
        from test_area_scout import place

        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {"OUTREACH_DIR": "outreach-us"}):
            out = Path(tmp) / "outreach-us"
            out.mkdir()
            queries = []

            def post(body, key):
                queries.append((body["textQuery"], body["regionCode"]))
                return {"places": [place(1, "No Site Roofing", "", 40)]} if "Provo" in body["textQuery"] else {}

            # The towns the panel's Areas box becomes: a state stays with its city; blank is Utah, not Surrey.
            with mock.patch.object(area_scout, "run") as run:
                area_scout.main(["--trades", "roofing", "--areas", "provo, ut, Ogden, UT", "--outreach", str(out)])
                area_scout.main(["--trades", "roofing", "--outreach", str(out)])
            self.assertEqual(run.call_args_list[0].args[0], ["Provo, UT", "Ogden, UT"])
            self.assertEqual(run.call_args_list[1].args[0], area_scout.US_DEFAULT_TOWNS)
            rows = area_scout.run(["Provo, UT"], ["roofing"], out, "k", "", post=post, log=lambda s: None)
        self.assertEqual(queries, [("roofing contractor in Provo, UT", "us")])
        self.assertEqual(rows[0]["Established, no website"], 1)
        self.assertEqual(rows[0]["Opportunity"], 0)  # no letters in the US: a firm without a website adds nothing


class Channel(unittest.TestCase):
    def test_us_sole_traders_get_email_and_no_one_gets_a_letter(self):
        row = {"Email": "mike@wasatchplumbing.com", "Company type": "Sole trader"}
        self.assertEqual(push_prospects.channel_for(row, market="us"), "email")
        self.assertEqual(push_prospects.channel_for({"Email": ""}, market="us"), "none")
        self.assertEqual(push_prospects.channel_for(row, email_bad=True, market="us"), "none")
        # The UK keeps PECR.
        self.assertEqual(push_prospects.channel_for(row), "letter")


class Sending(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.out = Path(self.tmp.name) / "outreach-us"
        self.out.mkdir()
        write(self.out / "mailmeteor-batch-2026-09-28.csv", list(FIRMS[0]), FIRMS)
        write(self.out / eb.PENDING, ["email", "business", "preview_url", "batch"],
              [{"email": f["email"], "business": f["business"], "preview_url": f["preview_url"],
                "batch": "mailmeteor-batch-2026-09-28.csv"} for f in FIRMS])
        self.env = mock.patch.dict(os.environ, {"MAIL_ADDRESS": "jack@scalardigital.com", "MAIL_APP_PASSWORD": "abcd",
                                                "MAIL_FROM_NAME": "Jack Wilkins", "POSTAL_ADDRESS": ""})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def send(self, smtp):
        return se.send_batch(self.out, smtp=smtp, sleep=lambda s: None, today=TODAY, out=lambda s: None)

    def test_no_postal_address_no_sending(self):
        smtp = FakeSMTP()
        with self.assertRaises(se.SendStopped) as stop:
            self.send(smtp)
        self.assertIn("POSTAL_ADDRESS", str(stop.exception))
        self.assertEqual(smtp.sent, [])

    def test_us_emails_carry_the_address_and_an_opt_out_and_no_uk_phone(self):
        os.environ["POSTAL_ADDRESS"] = "Scalar Digital, 123 Main St #4, Provo, UT 84601"
        smtp = FakeSMTP()
        self.assertEqual(self.send(smtp), 3)
        body = smtp.sent[0].get_content()
        self.assertIn("123 Main St #4, Provo, UT 84601", body)
        self.assertIn('Reply "no"', body)
        self.assertNotIn("07401", body)
        self.assertNotIn("{{", body)
        self.assertTrue(smtp.sent[0]["List-Unsubscribe"])

    def test_us_templates_without_the_address_are_refused(self):
        t = dict(se.US_DEFAULT_TEMPLATES)
        self.assertEqual(se.template_problem(t, "us"), "")
        t["first_body"] = "Hi {{greeting_name}}, {{preview_url}}"
        self.assertIn("CAN-SPAM", se.template_problem(t, "us"))
        self.assertIn("CAN-SPAM", se.save_templates(self.out, {**t}))
        self.assertEqual(se.template_problem(t, "uk"), "")  # the UK has no such rule
        self.assertEqual(se.load_templates(self.out)["first_body"], se.US_DEFAULT_TEMPLATES["first_body"])


class Replies(unittest.TestCase):
    def test_us_replies_are_in_dollars_and_us_english(self):
        with mock.patch.dict(os.environ, {"OUTREACH_DIR": "outreach-us"}):
            text = saved_replies.default_for()
            values = ai_reply.env_values({})
        self.assertNotIn("£", text)
        self.assertIn("${{price_build}}", text)
        self.assertEqual((values["currency"], values["price_build"], values["price_landing"]), ("$", "4,500", "1,500"))
        prompt = ai_reply.system_prompt("us")
        for _, new in ai_reply.US_SYSTEM_SWAPS:
            self.assertIn(new, prompt)
        self.assertIn("$4,500", ai_reply.brief({"message": "how much?"}, values, ""))
        self.assertEqual(ai_reply.system_prompt("uk"), ai_reply.SYSTEM)


if __name__ == "__main__":
    unittest.main()
