"""Saved replies: one-click answers to the replies outreach gets most, sent from the Calls tab.

Kept in outreach/reply-templates.txt, edited in the panel as one block of text:

    === How much? ===
    Hi {{greeting_name}}, ...

    === Not right now ===
    ...

Placeholders: {{greeting_name}} {{business}} {{your_name}} {{preview_url}} {{booking_link}}
{{price_build}} {{price_landing}}. A line with {{booking_link}} is left out while no booking
link is set in Settings, so nothing reads "pick a time: " with nothing after it.
"""

from __future__ import annotations

import re
from pathlib import Path

FILE = "reply-templates.txt"
FIELDS = {"greeting_name", "business", "your_name", "preview_url", "booking_link", "price_build", "price_landing"}
HEADING = re.compile(r"^===\s*(.+?)\s*===\s*$", re.M)
PLACEHOLDER = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")

DEFAULT = """=== How much? ===
Hi {{greeting_name}},

Thanks for getting back to me. It's a fixed price, agreed before I start anything:

- £{{price_landing}} for a single-page site
- £{{price_build}} for a five-page site, plus your own dashboard for enquiries, quotes, jobs and invoices (free for the first 12 months, then £39 a month if you want to keep it)

You own the site outright either way - no monthly fee on the website itself.

If it's easier to talk it through, pick a time that suits you here: {{booking_link}}
Or just reply with a good time and number and I'll ring you.

Kind regards,
{{your_name}}

=== How does it work? ===
Hi {{greeting_name}},

Thanks for replying. In short:

1. A 10-minute call about the work you want more of and the areas you cover.
2. You fill in one page with your details and send a few photos of your work.
3. I build it - usually live within two weeks - and you check it on your phone before it goes live.
4. It's yours outright. Enquiries come straight to your phone.

The preview I made is still here if you want another look: {{preview_url}}

If it's easier to talk, pick a time here: {{booking_link}}

Kind regards,
{{your_name}}

=== Call me / tell me more ===
Hi {{greeting_name}},

Great - happy to. What's a good number and time to call? Or pick a slot that suits you here: {{booking_link}}

It'll take ten minutes, and there's nothing to sign up for.

Kind regards,
{{your_name}}

=== Not right now ===
Hi {{greeting_name}},

No problem at all - thanks for letting me know. I'll leave it there.

If anything changes, just reply to this email and I'll pick it up.

All the best,
{{your_name}}

=== Already sorted ===
Hi {{greeting_name}},

Understood, and thanks for taking the time to reply - good to hear you're covered. I won't get in touch again.

All the best,
{{your_name}}
"""


def parse(text: str) -> dict[str, str]:
    """{"How much?": "Hi ...", ...} in the order written."""
    parts = HEADING.split(text or "")
    return {name.strip()[:60]: body.strip() for name, body in zip(parts[1::2], parts[2::2]) if name.strip() and body.strip()}


def problem(text: str) -> str:
    """Why this block of replies can't be saved, or ''."""
    replies = parse(text)
    if not replies:
        return "Nothing to save - each reply starts with a line like === How much? ==="
    if len(text) > 20_000:
        return "That's too long - keep it under 20,000 characters."
    for name, body in replies.items():
        unknown = sorted(set(PLACEHOLDER.findall(body)) - FIELDS)
        if unknown:
            return f'"{name}" uses {{{{{unknown[0]}}}}}, which isn\'t a field. Fields: ' + ", ".join(sorted(FIELDS))
    return ""


def load(outreach: Path) -> str:
    path = outreach / FILE
    return path.read_text(encoding="utf-8") if path.exists() else DEFAULT


def save(outreach: Path, text: str) -> str:
    why = problem(text)
    if not why:
        (outreach / FILE).write_text(text.strip() + "\n", encoding="utf-8")
    return why


def render(body: str, values: dict[str, str]) -> str:
    if not (values.get("booking_link") or "").strip():
        body = "\n".join(line for line in body.split("\n") if not re.search(r"\{\{\s*booking_link\s*\}\}", line))
    out = PLACEHOLDER.sub(lambda m: str(values.get(m.group(1)) or ""), body)
    out = re.sub(r"\n{3,}", "\n\n", out)
    return out.strip() + "\n"


def first_name(contact: str) -> str:
    """The name to greet: "Mr J Smith" -> "there" (no first name), "Sam Kerr" -> "Sam"."""
    words = [w for w in re.split(r"\s+", (contact or "").strip()) if w]
    words = [w for w in words if w.lower().strip(".") not in {"mr", "mrs", "ms", "miss", "dr"}]
    if not words or len(words[0].strip(".")) <= 1:
        return "there"
    return words[0].capitalize() if words[0].isupper() or words[0].islower() else words[0]
