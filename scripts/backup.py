"""A copy of everything in outreach/, every day, somewhere that isn't this PC.

    python scripts/backup.py                    back up now (the panel's "Back up now", and the end of every autopilot run)
    python scripts/backup.py --restore <zip>    unpack a backup into outreach-restored/ (never over your current files)

Your prospects, who's been emailed, replies, call-backs and client folders live only in outreach/ on
this computer - a dead disk or a lost laptop would take the whole pipeline with it. This zips the
folder into BACKUP_DIR (Settings), or your OneDrive folder if that's not set (Windows makes one
for every Microsoft account), as outreach-YYYY-MM-DD.zip, and keeps the newest 14. A folder
OneDrive, Google Drive or Dropbox syncs means the copy is off this PC within minutes.

It holds the same business contact details the panel does; keep the backup folder in your own
private cloud account and nowhere shared.
"""

from __future__ import annotations

import argparse
import os
import sys
import zipfile
from datetime import date, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

KEEP = 14
PREFIX = "outreach-"
SKIP_SUFFIXES = (".lock", ".tmp")
LAST = ".last-backup"  # in outreach/: when the last good backup was made, for the panel


def backup_dir(env: dict | None = None) -> Path | None:
    env = os.environ if env is None else env
    chosen = (env.get("BACKUP_DIR") or "").strip()
    if chosen:
        return Path(chosen).expanduser()
    onedrive = (env.get("OneDrive") or env.get("ONEDRIVE") or "").strip()
    return Path(onedrive) / "Scalar backups" if onedrive else None


def make(outreach: Path, dest: Path, today: date | None = None) -> tuple[Path, int]:
    """Writes dest/outreach-<date>.zip (replacing today's if run twice) -> (zip, files in it)."""
    today = today or date.today()
    dest.mkdir(parents=True, exist_ok=True)
    final = dest / f"{PREFIX}{today.isoformat()}.zip"
    part = final.with_suffix(".zip.part")  # never leave a half-written zip looking like a good one
    count = 0
    with zipfile.ZipFile(part, "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(outreach.rglob("*")):
            if not path.is_file() or path.name.endswith(SKIP_SUFFIXES) or path.name == LAST:
                continue
            try:
                z.write(path, path.relative_to(outreach).as_posix())
                count += 1
            except OSError:  # a file open in Excel; the rest still go
                continue
    os.replace(part, final)
    return final, count


def prune(dest: Path, keep: int = KEEP) -> list[Path]:
    """Deletes all but the newest `keep` backups this script made (nothing else in the folder)."""
    ours = sorted(p for p in dest.glob(f"{PREFIX}????-??-??.zip"))
    gone = ours[:-keep] if len(ours) > keep else []
    for p in gone:
        p.unlink(missing_ok=True)
    return gone


def last_backup(outreach: Path) -> str | None:
    path = outreach / LAST
    return path.read_text(encoding="utf-8").strip() if path.exists() else None


def restore(zip_path: Path, outreach: Path) -> Path:
    """Unpacks next to outreach/, never over it - you choose what to copy back."""
    target = outreach.parent / "outreach-restored"
    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"{target} isn't empty - move it aside first, so nothing gets mixed up.")
    with zipfile.ZipFile(zip_path) as z:
        for name in z.namelist():  # refuse anything that would land outside the folder
            if name.startswith("/") or ".." in Path(name).parts:
                raise SystemExit(f"{zip_path.name} contains an unsafe path ({name}) - not restoring it.")
        z.extractall(target)
    return target


def main() -> None:
    import reply_scanner

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--restore", metavar="ZIP")
    args = ap.parse_args()
    outreach = reply_scanner.outreach_dir()
    if args.restore:
        target = restore(Path(args.restore), outreach)
        print(f"Unpacked into {target}. Copy back whatever you need into {outreach}.")
        return
    dest = backup_dir()
    if dest is None:
        sys.exit("Choose a backup folder in Settings (BACKUP_DIR) - ideally one OneDrive, Google Drive or Dropbox syncs.")
    if not outreach.exists():
        sys.exit("There's no outreach folder yet - nothing to back up.")
    try:
        final, count = make(outreach, dest)
    except OSError as e:
        sys.exit(f"Couldn't write the backup to {dest} ({e.strerror or e}). Is the folder there, and is there space?")
    gone = prune(dest)
    (outreach / LAST).write_text(datetime.now().strftime("%Y-%m-%d %H:%M"), encoding="utf-8")
    size = final.stat().st_size / 1_048_576
    print(f"Backed up {count} files ({size:.1f} MB) to {final}" + (f"; removed {len(gone)} older backup(s)" if gone else "") + ".")


if __name__ == "__main__":
    main()
