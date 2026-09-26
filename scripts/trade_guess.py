"""Guess a prospect's trade from their own homepage, when the sheet leaves it blank.

Used by push_prospects.py --guess-trades. Reads only the homepage's <title>,
meta description and first headings - the words the business itself chose
to describe what it does - and scores them against a few trade vocabularies.
No match, no guess: the preview page then falls back to its default rotation
rather than showing a roofing firm a driveway.

The labels returned are the same style as the sheet's own Trade column, so
the site maps them to a preview scene the same way (lib/showcase.ts).
"""

from __future__ import annotations

import html as htmllib
import re

# Checked in this order; on a tie the earlier (more specific) trade wins.
TRADES: list[tuple[str, list[str]]] = [
    ("Roofing", ["roof", "roofer", "slate", "tiling", "fascia", "soffit", "guttering", "chimney", "lead work", "leadwork", "flat roof"]),
    ("Loft conversions", ["loft", "dormer", "mansard", "hip to gable"]),
    ("Driveways & patios", ["driveway", "paving", "block paving", "resin", "patio", "tarmac", "imprinted"]),
    ("Landscaping", ["landscap", "garden", "turf", "fencing", "decking", "groundwork"]),
    ("Building & extensions", ["extension", "builder", "building", "conversion", "new build", "renovation", "refurbish", "construction"]),
]


def page_text_for_guess(page_html: str) -> str:
    """The words a business uses to describe itself: title, meta description, h1/h2."""
    parts: list[str] = []
    t = re.search(r"<title[^>]*>(.*?)</title>", page_html, re.I | re.S)
    if t:
        parts.append(t.group(1))
    for m in re.finditer(r"<meta[^>]+>", page_html, re.I):
        tag = m.group(0)
        if re.search(r"name\s*=\s*[\"']description[\"']", tag, re.I):
            c = re.search(r"content\s*=\s*[\"']([^\"']*)", tag, re.I)
            if c:
                parts.append(c.group(1))
    parts += re.findall(r"<h[12][^>]*>(.*?)</h[12]>", page_html, re.I | re.S)[:4]
    text = " ".join(re.sub(r"<[^>]+>", " ", p) for p in parts)
    return re.sub(r"\s+", " ", htmllib.unescape(text)).strip()


def guess_trade(text: str) -> str | None:
    """Best-matching trade label for a description, or None if nothing matches."""
    lowered = f" {text.lower()} "
    best, best_score = None, 0
    for label, words in TRADES:
        score = sum(lowered.count(w) for w in words)
        if score > best_score:
            best, best_score = label, score
    return best
