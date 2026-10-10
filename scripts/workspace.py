"""Which outreach folder this run works in, and which market that folder sells to.

The UK workspace is outreach/ - beside this checkout, or in the main checkout when run from a git
worktree. A second market gets a folder of its own, named after it: outreach-us/. Its lists, sent
log, do-not-contact list, email templates, inboxes and settings (its own panel.env) never mix with
the UK's, so a US firm can't be sent a UK email from a UK inbox, or the other way round.

control_panel_us.bat starts the panel with OUTREACH_DIR=outreach-us; every script the panel runs
inherits it. The market is read from the folder's name, never set separately, so the two can't
disagree.
"""

from __future__ import annotations

import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT = "outreach"

MARKETS: dict[str, dict] = {
    "uk": {
        "label": "UK",
        "currency": "£",
        "region": "gb",  # Google Places regionCode
        "language": "en-GB",
        # PECR: no cold email to sole traders or ordinary partnerships - they get a letter instead.
        "pecr": True,
        "letters": True,
        # Quotes go through the dashboard, which prices in pounds with UK VAT and UK terms.
        "online_quotes": True,
        # Defaults when QUOTE_PRICE_BUILD / QUOTE_PRICE_LANDING aren't set - the website's own (lib/site.ts).
        "prices": {"build": 2500, "landing": 750},
    },
    "us": {
        "label": "US",
        "currency": "$",
        "region": "us",
        "language": "en-US",
        # CAN-SPAM: any business may be emailed, sole proprietors included, if every email carries a
        # real postal address and a working way to opt out (honoured within 10 business days).
        "pecr": False,
        # Letters are UK A4 with UK postage - never for a US firm. No email means no contact.
        "letters": False,
        # The dashboard's quotes are pounds + UK VAT + UK terms: a US firm gets its price in a reply instead.
        "online_quotes": False,
        "prices": {"build": 4500, "landing": 1500},
    },
}


def folder_name() -> str:
    return (os.environ.get("OUTREACH_DIR") or "").strip() or DEFAULT


def outreach_dir() -> Path:
    """This run's outreach folder. OUTREACH_DIR may be a full path, or a folder name found the same
    way as outreach/ itself: beside this checkout, or the main one when run from a worktree."""
    name = folder_name()
    path = Path(name)
    if path.is_absolute():
        return path
    for parent in [HERE.parent, *HERE.parents]:
        if (parent / name).is_dir():
            return parent / name
    return HERE.parent / name


def market(outreach: Path | None = None) -> str:
    """"uk" or "us": from the folder's name - outreach-us is the US, anything else the UK."""
    name = (outreach.name if outreach is not None else Path(folder_name()).name).lower()
    suffix = name.rsplit("-", 1)[-1] if name.startswith(DEFAULT + "-") else ""
    return suffix if suffix in MARKETS else "uk"


def config(outreach: Path | None = None) -> dict:
    return MARKETS[market(outreach)]


def money(amount, outreach: Path | None = None) -> str:
    """"£2,500" or "$4,500" - whole amounts without pence, others with."""
    symbol = config(outreach)["currency"]
    value = float(amount or 0)
    return f"{symbol}{value:,.0f}" if value == int(value) else f"{symbol}{value:,.2f}"
