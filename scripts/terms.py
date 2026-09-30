"""Scalar Digital's terms of business - what a client signs when they accept a quote.

Every quote from the panel carries these (quotes.create_quote -> the dashboard stores them
on the quote, and the accept page shows them above "I accept"), and the printable proposal
repeats them (proposal.py). They say, in plain English, exactly what the website already
promises - fixed price, tweaks included, 30/14 days' aftercare, you own the code and domain,
no monthly fee on the website - plus what happens if things go sideways.

Have a solicitor read these once before relying on them. They're written to be fair and
clear, not to be clever; a one-off review of a single page like this is cheap.
"""

from __future__ import annotations

VERSION = "2026-09"
BUSINESS = "Scalar Digital"
DASHBOARD_MONTHLY = 39

# What's in each package - the same lists as the pricing section (components/pricing.tsx).
INCLUDED = {
    "build": [
        "Five hand-coded pages, including a gallery and a service-areas page",
        "Your own private dashboard - enquiries, quotes, jobs, invoices and a customer portal, under your business name",
        "Custom design, built around how your business actually wins work - no templates",
        "Mobile-first, built for 90+ on Google's mobile speed test",
        "Local SEO built into the site's structure",
        "WhatsApp, call and enquiry routing built in",
        "Google Business and reviews wired in",
        "You own the code and the domain outright",
        "30 days of support after launch",
    ],
    "landing": [
        "One hand-coded page, built to turn visitors into enquiries",
        "Custom design, built for your business - no templates",
        "Mobile-first, built for 90+ on Google's mobile speed test",
        "Local search foundations built in",
        "WhatsApp, call and enquiry routing built in",
        "You own the code and the domain outright",
        "14 days of support after launch",
    ],
}
FOUNDING_EXTRAS = [
    "Dashboard hosting free for 24 months (twice the usual 12)",
    "Speed guarantee: 90+ on Google's mobile speed test at launch, checked together on the live site, or the balance isn't due",
    "First place in the build queue",
]
AFTERCARE_DAYS = {"build": 30, "landing": 14}

EXCLUSIONS = (
    "Your domain name's yearly renewal (paid to your registrar, typically £10-£20 a year). "
    "Email hosting. Paid stock photos or a photoshoot. Advertising spend (Google Ads, social media). "
    "Printed materials. Anything not listed in this quote - it's quoted separately before any work."
)


def payment_terms(deposit_percent: int) -> str:
    """The one-line version, shown beside the price."""
    if deposit_percent >= 100:
        return "Paid in full on acceptance. Invoices are due within 7 days."
    if deposit_percent > 0:
        return (f"{deposit_percent}% deposit on acceptance - your build is booked in once it's paid. "
                "The balance when your site is ready to go live and you've checked it. Invoices are due within 7 days.")
    return "Paid in full when your site is ready to go live and you've checked it. Invoices are due within 7 days."


def terms(package: str, deposit_percent: int, vat_rate: int = 0, founding: bool = False) -> str:
    """The full terms for one quote, numbered, as plain text (the quote page keeps the line breaks)."""
    if package not in INCLUDED:
        raise ValueError(f"unknown package {package!r}")
    founding = founding and package == "build"  # the founding offer is for The Scalar build only
    days = AFTERCARE_DAYS[package]
    free_months = 24 if founding else 12
    if deposit_percent >= 100:
        paying = "You pay the full price on acceptance."
    elif deposit_percent > 0:
        paying = (f"A {deposit_percent}% deposit is due when you accept, and your build is booked in once it's paid. "
                  "The balance is due when your site is ready to go live and you've checked it; it goes live on your domain once that's paid.")
    else:
        paying = "Nothing is due until your site is ready to go live and you've checked it; it goes live on your domain once it's paid."
    if founding:
        paying += (" Founding-client speed guarantee: if the live site doesn't score 90+ on Google's mobile speed test at launch "
                   "(checked together), the balance isn't due.")
    sections = [
        ("What you're getting",
         "The work listed in this quote. Anything else - an extra page, a new feature - is quoted separately, and nothing is "
         "added to the price without your written go-ahead."),
        ("The price",
         "The price is fixed. It doesn't move once we start, whatever the job turns out to involve. "
         + ("It includes VAT at 20%." if vat_rate == 20 else "No VAT is charged.")),
        ("Paying", paying + " Invoices are due within 7 days, by bank transfer or card."),
        ("Your part",
         "Send me what I ask for - photos of your work, your logo, reviews you're happy to show, the towns you cover, and logins for "
         "your domain - within 14 days of my asking, and check things when I ask you to. You confirm you have the right to use "
         "anything you send me. If I'm waiting on you for more than 60 days, I can close the project and invoice for the work done "
         "so far; picking it back up later costs nothing extra."),
        ("Checking it before launch",
         "You see the whole site, on your own phone, before anything is public. Tweaks to what we agreed are included, not billed as "
         "extras. It goes live when you're happy with it."),
        ("Aftercare",
         f"For {days} days after launch, tweaks and fixes are free. After that there's no retainer on your website: any later change "
         "is quoted as a one-off, and you're free to use anyone you like."),
        ("Ownership",
         "Once it's paid for in full, the site's code, design and the words written for it are yours, and your domain is registered "
         "in your name. Your photos, logo and content stay yours throughout. I may show the finished site in my portfolio unless you "
         "ask me not to."),
        ("Hosting",
         "Your site is hosted on Cloudflare, on a free account in your name, so there's no monthly hosting fee on the website. "
         "Cloudflare provides the hosting under its own terms; I set it up and publish to it."),
    ]
    if founding:
        sections.append((
            "Founding client",
            "You're one of the first three Scalar builds, so you also get first place in the build queue and the speed guarantee "
            "above. In return you agree to a short case study with your real before-and-after numbers, a 60-second video and a "
            "Google review, once the site has been live long enough to have numbers worth showing."))
    if package == "build":
        sections.append((
            "Your dashboard",
            f"Your dashboard (enquiries, quotes, jobs, invoices, customer portal) is free for your first {free_months} months. After "
            f"that it's £{DASHBOARD_MONTHLY} a month if you want to keep it - entirely optional, cancel any time. Your website carries "
            "on working without it: if you stop, I'll switch your enquiry form to email you directly at no charge, and you can have "
            "a copy of your data."))
    sections += [
        ("Not included", EXCLUSIONS),
        ("Results",
         "I build every site to be fast and found locally, but nobody can honestly promise a Google ranking or a number of "
         "enquiries, so I don't."),
        ("Cancelling",
         "You can cancel at any time by telling me in writing. Before I've started, any deposit is refunded in full. After that, you "
         "pay for the work done up to that point - never more than the full price - with the deposit counting towards it, and you "
         "get everything built so far."),
        ("Liability",
         "If something goes wrong that's my fault, my liability is limited to the price of this quote, and I'm not liable for "
         "indirect losses such as lost profit or business. Nothing here limits anything the law doesn't allow to be limited."),
        ("Personal data",
         "We each look after personal data as UK GDPR requires. Enquiries from your site pass through my systems only to reach "
         "you, and are never used for anything else. Details: scalardigital.co.uk/privacy."),
        ("The agreement",
         f"This quote and these terms are the whole agreement between you and {BUSINESS}. Accepting online - typing your name and "
         "ticking the box - is signing it. It's governed by the law of England and Wales."),
    ]
    body = "\n\n".join(f"{i}. {title}\n{text}" for i, (title, text) in enumerate(sections, 1))
    return f"{BUSINESS} terms of business ({VERSION})\n\n{body}"


def included(package: str, founding: bool = False) -> list[str]:
    return INCLUDED[package] + (FOUNDING_EXTRAS if founding and package == "build" else [])
