"""backup.py: everything in outreach/ zipped off the PC, the newest 14 kept, restore never overwrites; the health strip."""

import tempfile
import unittest
import zipfile
from datetime import date, datetime
from pathlib import Path

import backup
import control_panel as panel


class Backup(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.out, self.dest = root / "outreach", root / "OneDrive" / "Scalar backups"
        (self.out / "sites" / "kerr").mkdir(parents=True)
        (self.out / "outreach-sent.csv").write_text("email,sent\nbill@kerr.co.uk,2026-10-01\n", encoding="utf-8")
        (self.out / "sites" / "kerr" / "site.json").write_text("{}", encoding="utf-8")
        (self.out / ".autopilot.lock").write_text("123", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_zips_everything_but_locks(self):
        final, n = backup.make(self.out, self.dest, date(2026, 10, 2))
        self.assertEqual(final.name, "outreach-2026-10-02.zip")
        with zipfile.ZipFile(final) as z:
            self.assertEqual(sorted(z.namelist()), ["outreach-sent.csv", "sites/kerr/site.json"])
        self.assertEqual(n, 2)
        self.assertFalse(list(self.dest.glob("*.part")))

    def test_keeps_the_newest_14_and_nothing_else_is_touched(self):
        self.dest.mkdir(parents=True)
        (self.dest / "my-notes.txt").write_text("keep me", encoding="utf-8")
        for d in range(1, 18):
            backup.make(self.out, self.dest, date(2026, 9, d))
        gone = backup.prune(self.dest)
        self.assertEqual(len(gone), 3)
        self.assertEqual(sorted(p.name for p in self.dest.glob("outreach-*.zip"))[0], "outreach-2026-09-04.zip")
        self.assertTrue((self.dest / "my-notes.txt").exists())

    def test_folder_defaults_to_onedrive(self):
        self.assertEqual(backup.backup_dir({"BACKUP_DIR": "D:/b"}), Path("D:/b"))
        self.assertEqual(backup.backup_dir({"OneDrive": "C:/Users/a/OneDrive"}), Path("C:/Users/a/OneDrive") / "Scalar backups")
        self.assertIsNone(backup.backup_dir({}))

    def test_restore_unpacks_beside_never_over(self):
        final, _ = backup.make(self.out, self.dest, date(2026, 10, 2))
        target = backup.restore(final, self.out)
        self.assertEqual(target.name, "outreach-restored")
        self.assertTrue((target / "sites" / "kerr" / "site.json").exists())
        with self.assertRaises(SystemExit):  # not into a folder that already has files
            backup.restore(final, self.out)

    def test_restore_refuses_a_zip_that_escapes_the_folder(self):
        bad = Path(self.tmp.name) / "bad.zip"
        with zipfile.ZipFile(bad, "w") as z:
            z.writestr("../evil.txt", "x")
        with self.assertRaises(SystemExit):
            backup.restore(bad, self.out)


class Health(unittest.TestCase):
    def test_backup_age_and_missing_login_show_red(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            now = datetime(2026, 10, 2, 9, 0)
            first = {h["name"]: h for h in panel.health(out, {}, now)}
            self.assertFalse(first["Backup"]["ok"])
            self.assertIn("BACKUP_DIR", first["Backup"]["text"])
            self.assertFalse(first["Inbox"]["ok"])
            (out / backup.LAST).write_text("2026-10-01 22:00", encoding="utf-8")
            later = {h["name"]: h for h in panel.health(out, {"MAIL_ADDRESS": "a@b.c", "MAIL_APP_PASSWORD": "x"}, now)}
            self.assertTrue(later["Backup"]["ok"])
            self.assertNotIn("Inbox", later)
            stale = {h["name"]: h for h in panel.health(out, {}, datetime(2026, 10, 5, 9, 0))}
            self.assertFalse(stale["Backup"]["ok"])


if __name__ == "__main__":
    unittest.main()
