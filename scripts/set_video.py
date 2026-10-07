"""Put a personal walkthrough video on one preview page (or take it off).

The panel's "Add a video to a preview" (Results card). Record 60-90 seconds on Loom (or YouTube
unlisted / Vimeo) scrolling their preview and saying what you'd fix first, then paste both links.
The video shows at the top of their page, with "Watch my walkthrough" as the header button.
Best kept for firms that opened their preview twice or more - the morning nudge lists them.

Needs dashboard migration 062.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

PLAYERS = ("loom.com/", "youtube.com/", "youtu.be/", "vimeo.com/")


def looks_like_video(url: str) -> bool:
    url = (url or "").strip().lower()
    return url.startswith("https://") and any(p in url for p in PLAYERS) and len(url) <= 300


def set_video(api: str, secret: str, slug: str, video: str, send=None) -> dict:
    def _send(url: str, body: dict) -> dict:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method="PATCH",
                                     headers={"Authorization": f"Bearer {secret}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as res:
                return json.loads(res.read())
        except urllib.error.HTTPError as e:
            try:
                return {"error": json.loads(e.read()).get("error") or f"HTTP {e.code}", "status": e.code}
            except ValueError:
                return {"error": f"HTTP {e.code}", "status": e.code}

    return (send or _send)(f"{api}/api/prospects/{slug}", {"video_url": video})


def main(argv: list[str] | None = None) -> int:
    from check_preview import slug_from

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--link", required=True, help="their preview link")
    ap.add_argument("--video", default="", help="Loom / YouTube / Vimeo link; blank takes it off")
    args = ap.parse_args(argv)
    slug = slug_from(args.link)
    if not slug:
        raise SystemExit("That doesn't look like a preview link.")
    secret = os.environ.get("PROSPECTS_API_SECRET", "")
    if not secret:
        raise SystemExit("Add PROSPECTS_API_SECRET in Settings first.")
    api = os.environ.get("DASHBOARD_API_URL", "https://admin.scalardigital.co.uk").rstrip("/")
    try:
        out = set_video(api, secret, slug, args.video.strip())
    except (urllib.error.URLError, OSError, ValueError) as e:
        raise SystemExit(f"Couldn't reach the dashboard ({getattr(e, 'reason', e)}).") from e
    if out.get("error"):
        if out.get("status") == 404:
            raise SystemExit("The dashboard has no page with that link - check it with 'Check a preview link'.")
        raise SystemExit(f"Not saved: {out['error']}")
    site = os.environ.get("SITE_URL", "https://www.scalardigital.co.uk").rstrip("/")
    print(f"Video on: {site}/for/{slug}" if out.get("video_url") else f"Video taken off {site}/for/{slug}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
