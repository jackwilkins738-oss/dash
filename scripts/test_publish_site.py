import json
import tempfile
import unittest
from pathlib import Path

import publish_site as ps

ACCOUNT = "0123456789abcdef0123456789abcdef"


class PublishSite(unittest.TestCase):
    def test_only_the_site_subfolder_is_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "sites" / "kerr-roofing" / "client-files").mkdir(parents=True)
            with self.assertRaises(ValueError) as e:
                ps.site_dir(d, "kerr-roofing")
            self.assertIn("/site/", str(e.exception))
            (d / "sites" / "kerr-roofing" / "site").mkdir()
            (d / "sites" / "kerr-roofing" / "site" / "index.html").write_text("<h1>hi</h1>")
            self.assertEqual(ps.site_dir(d, "kerr-roofing"), d / "sites" / "kerr-roofing" / "site")

    def test_folder_names_cant_climb_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            for bad in ("../x", "Kerr Roofing", "", "a/b"):
                with self.assertRaises(ValueError):
                    ps.site_dir(Path(tmp), bad)

    def test_remembers_account_and_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            (d / "sites" / "kerr").mkdir(parents=True)
            self.assertEqual(ps.settings_for(d, "kerr", ACCOUNT.upper(), ""), (ACCOUNT, "kerr"))
            self.assertEqual(json.loads((d / "sites" / "kerr" / "publish.json").read_text()), {"account": ACCOUNT, "project": "kerr"})
            self.assertEqual(ps.settings_for(d, "kerr", "", ""), (ACCOUNT, "kerr"))
            with self.assertRaises(ValueError):
                ps.settings_for(d, "kerr", "", "Bad Name!")
            (d / "sites" / "other").mkdir()
            with self.assertRaises(ValueError):
                ps.settings_for(d, "other", "not-an-id", "")

    def test_commands_and_first_publish(self):
        cmd = ps.deploy_command("npx", Path("/o/sites/kerr/site"), "kerr")
        self.assertEqual(cmd[:5], ["npx", "--yes", ps.WRANGLER, "pages", "deploy"])
        self.assertIn("--project-name", cmd)
        self.assertEqual(cmd[cmd.index("--branch") + 1], "main")
        preview = ps.deploy_command("npx", Path("/o/sites/kerr/site"), "kerr", "preview")
        self.assertEqual(preview[preview.index("--branch") + 1], "preview")  # never the live branch
        self.assertTrue(ps.missing_project("✘ [ERROR] Project not found. The specified project name does not match"))
        self.assertFalse(ps.missing_project("Authentication error [code: 10000]"))


if __name__ == "__main__":
    unittest.main()
