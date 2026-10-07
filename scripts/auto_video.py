"""Make a walkthrough video for one preview, automatically, and put it on their page.

The panel's "🎬 Make it for me" (Results card, beside Add a video), or 🎬 on a Telegram nudge. A
phone-sized browser on this PC records about 45 seconds:

    their current site, scrolled, captioned with their own numbers (score, load time, worst problems)
    then their preview page, scrolled, captioned "a faster site, made for <business>"
    and a last caption with your name and number

No voice and nothing invented - captions use only what their speed check measured. The recording is
turned into a small MP4, uploaded to the dashboard (migration 063) and shown at the top of their page.
Your own Loom is still best for the hottest leads; this is for the warm ones you'd otherwise skip.

One-off setup: Settings -> "Install video maker" (Playwright's browser and ffmpeg, about 250 MB).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PHONE = {"width": 390, "height": 844}  # recorded at this size: the preview page shows it about phone-width, so 1:1
MAX_MB = 25

OVERLAY = """(text) => {
  // Old sites with no mobile viewport are laid out ~980px wide and zoomed out on a phone: scale the
  // caption with them, so it reads the same size on every site.
  const k = Math.max(1, window.innerWidth / 390);
  let el = document.getElementById('__scalar_caption');
  if (!el) {
    el = document.createElement('div');
    el.id = '__scalar_caption';
    document.documentElement.appendChild(el);
  }
  el.style.cssText = `position:fixed;left:${14 * k}px;right:${14 * k}px;bottom:${56 * k}px;z-index:2147483647;` +
    `padding:${16 * k}px ${18 * k}px;background:rgba(10,14,24,.9);color:#fff;font:700 ${23 * k}px/1.3 Arial,sans-serif;` +
    `border-radius:${14 * k}px;box-shadow:0 6px 24px rgba(0,0,0,.35)`;
  el.textContent = text;
}"""


class VideoUnavailable(Exception):
    pass


def captions(row: dict, business: str, your_name: str, phone: str, year: int) -> dict[str, list[str]]:
    """What the video says, from their measured numbers only - a line is left out when its fact is missing."""
    from findings import all_issues

    site = row.get("website") or "your website"
    score, lcp = row.get("mobile_score"), row.get("lcp_s")
    first = [f"{site} today, on a phone"]
    if score is not None:
        first.append(f"Google's phone speed test: {int(score)}/100" + (f" - {float(lcp):.1f}s before anything shows" if lcp else ""))
    issues = all_issues(row.get("teardown"), year)[:2]
    first += [f"I noticed {i}" for i in issues]
    return {
        "site": first,
        "preview": [f"A faster site, made for {business}", "Built for 90+ on the same Google test"
                    if score is not None and int(score) < 90 else "Built to turn visits into calls"],
        "end": [f"{your_name or 'Scalar Digital'} · {phone}" if phone else (your_name or "Scalar Digital"),
                "Reply to my email or give me a ring"],
    }


def record(site_url: str | None, preview_url: str, words: dict[str, list[str]], out_dir: Path) -> Path:
    try:
        from playwright.sync_api import Error as PWError
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise VideoUnavailable("The video maker needs one-off setup: Settings -> Install video maker.") from e

    def show(page, lines: list[str], seconds: float, scroll: bool) -> None:
        per = seconds / max(1, len(lines))
        for line in lines:
            page.evaluate(OVERLAY, line)
            steps = 6
            for _ in range(steps):
                if scroll:
                    page.mouse.wheel(0, 260)
                page.wait_for_timeout(int(per * 1000 / steps))

    with sync_playwright() as pw:
        try:
            browser = pw.chromium.launch()
        except PWError as e:
            raise VideoUnavailable("The video maker's browser isn't installed: Settings -> Install video maker.") from e
        ctx = browser.new_context(viewport=PHONE, device_scale_factor=2, is_mobile=True, has_touch=True,
                                  record_video_dir=str(out_dir), record_video_size=PHONE)
        page = ctx.new_page()
        if site_url:
            try:
                page.goto(site_url, wait_until="load", timeout=30000)
                page.wait_for_timeout(1500)
                show(page, words["site"], 4.0 * len(words["site"]), scroll=True)
            except PWError:
                pass  # their site wouldn't load: straight to the preview
        page.goto(preview_url, wait_until="load", timeout=30000)
        page.wait_for_timeout(1500)
        show(page, words["preview"], 14, scroll=True)
        show(page, words["end"], 6, scroll=False)
        video = page.video.path() if page.video else None
        ctx.close()
        browser.close()
    if not video or not Path(video).exists():
        raise VideoUnavailable("The browser didn't save a recording - try again.")
    return Path(video)


def to_mp4(webm: Path, mp4: Path) -> Path:
    try:
        import imageio_ffmpeg
    except ImportError as e:
        raise VideoUnavailable("The video maker needs one-off setup: Settings -> Install video maker.") from e
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-i", str(webm), "-an", "-c:v", "libx264",
           "-preset", "veryfast", "-crf", "30", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(mp4)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if res.returncode != 0 or not mp4.exists():
        raise VideoUnavailable(f"Couldn't make the MP4 ({(res.stderr or '').strip()[-200:]}).")
    return mp4


def upload(api: str, secret: str, slug: str, mp4: Path, post=None, put=None, patch=None) -> str:
    """Upload to the dashboard's storage and put it on their page -> the video's address."""
    def _json(method: str, url: str, body: dict | None) -> dict:
        req = urllib.request.Request(url, data=json.dumps(body).encode() if body is not None else b"", method=method,
                                     headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.loads(res.read())

    def _put(url: str, data: bytes) -> None:
        req = urllib.request.Request(url, data=data, method="PUT", headers={"Content-Type": "video/mp4"})
        with urllib.request.urlopen(req, timeout=300):
            pass

    got = (post or (lambda url: _json("POST", url, None)))(f"{api}/api/prospects/{slug}/video-upload")
    (put or _put)(got["upload_url"], mp4.read_bytes())
    out = (patch or (lambda url, body: _json("PATCH", url, body)))(f"{api}/api/prospects/{slug}", {"video_url": got["video_url"]})
    if out.get("error"):
        raise VideoUnavailable(f"Uploaded, but the page didn't take it: {out['error']}")
    return got["video_url"]


def main(argv: list[str] | None = None) -> int:
    from check_preview import dashboard_row, slug_from

    import daily

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--link", required=True, help="their preview link")
    args = ap.parse_args(argv)
    slug = slug_from(args.link)
    if not slug:
        raise SystemExit("That doesn't look like a preview link.")
    secret = os.environ.get("PROSPECTS_API_SECRET", "")
    if len(secret) < 32:
        raise SystemExit("Add PROSPECTS_API_SECRET in Settings first.")
    api = os.environ.get("DASHBOARD_API_URL", "https://admin.scalardigital.co.uk").rstrip("/")
    site = os.environ.get("SITE_URL", "https://www.scalardigital.co.uk").rstrip("/")
    row = dashboard_row(api, secret, slug)
    if not row:
        raise SystemExit("The dashboard has no page with that link.")
    business = row.get("business_name") or "you"
    words = captions(row, business, os.environ.get("MAIL_FROM_NAME", ""), os.environ.get("LETTER_PHONE", "") or "07401 696272",
                     date.today().year)
    print(f"Recording {business}'s walkthrough (about 45 seconds) ...", flush=True)
    work = Path(tempfile.mkdtemp(prefix="scalar-video-"))
    try:
        webm = record(f"https://{row['website']}/" if row.get("website") else None, f"{site}/for/{slug}?src=dashboard", words, work)
        mp4 = to_mp4(webm, work / f"{slug}.mp4")
        size = mp4.stat().st_size / 1_000_000
        if size > MAX_MB:
            raise SystemExit(f"The video came out at {size:.0f} MB - over the {MAX_MB} MB limit. Try again.")
        url = upload(api, secret, slug, mp4)
    except VideoUnavailable as e:
        raise SystemExit(str(e)) from e
    finally:
        shutil.rmtree(work, ignore_errors=True)
    outreach = next((d / "outreach" for d in [HERE.parent, *HERE.parents] if (d / "outreach").is_dir()), HERE.parent / "outreach")
    daily.log_video(outreach, slug, date.today())
    print(f"READY: {size:.1f} MB video on {site}/for/{slug} - it's at the top of their page ({url}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
