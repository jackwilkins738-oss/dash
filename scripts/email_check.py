"""A free check that each email address can receive mail at all.

Used by push_prospects.py --check-emails. Catches the addresses that would
bounce for certain - a typo'd domain, a domain that no longer exists, a
domain with no mail server - not a mailbox that's been deleted on a live
domain (only sending to it can tell that). Bounces hurt the sending
account's reputation, so these go by letter instead.

The domain is looked up over DNS-over-HTTPS (Cloudflare, then Google), so it needs no
extra install. Only the domain after the @ is sent, never the address.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+'-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}$")

# Common slips on the big free providers.
TYPOS = {
    "gmial.com": "gmail.com", "gmai.com": "gmail.com", "gamil.com": "gmail.com", "gnail.com": "gmail.com",
    "gmail.co": "gmail.com", "gmail.co.uk": "gmail.com", "gmaill.com": "gmail.com", "googlemail.co": "googlemail.com",
    "hotmial.com": "hotmail.com", "hotmail.co": "hotmail.co.uk", "hotmal.com": "hotmail.com", "hotmai.com": "hotmail.com",
    "outlook.co": "outlook.com", "outlok.com": "outlook.com", "yahoo.co": "yahoo.co.uk", "yaho.com": "yahoo.com",
    "btinternet.co": "btinternet.com", "btinternet.co.uk": "btinternet.com", "btinterent.com": "btinternet.com",
    "sky.co.uk": "sky.com", "icloud.co": "icloud.com", "iclould.com": "icloud.com",
}

# Results that mean "don't email this address".
BAD = ("bad-format", "no-domain", "no-mail-server", "typo")


def is_bad(result: str) -> bool:
    return result.startswith(BAD)


DOH = ["https://cloudflare-dns.com/dns-query", "https://dns.google/resolve"]


def _dns(name: str, rtype: str) -> dict | None:
    """A DNS answer in the JSON form both providers share, or None if neither answered."""
    query = urllib.parse.urlencode({"name": name, "type": rtype})
    for base in DOH:
        req = urllib.request.Request(f"{base}?{query}", headers={"Accept": "application/dns-json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                return json.loads(res.read())
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            continue
    return None


def check_domain(domain: str) -> str:
    """ok | no-domain | no-mail-server | unknown (couldn't ask - never counted as bad)."""
    mx = _dns(domain, "MX")
    if mx is None or mx.get("Status") not in (0, 3):
        return "unknown"
    if mx.get("Status") == 3:
        return "no-domain"
    hosts = [(a.get("data") or "").split()[-1:] for a in mx.get("Answer") or [] if a.get("type") == 15]
    if hosts:
        # "0 ." is a null MX: the domain says it never takes mail.
        return "ok" if any(h and h[0] != "." for h in hosts) else "no-mail-server"
    # No MX: mail falls back to the domain's own address, if it has one.
    a = _dns(domain, "A")
    if a is None:
        return "unknown"
    return "ok" if any(r.get("type") == 1 for r in a.get("Answer") or []) else "no-mail-server"


def check_format(email: str) -> str | None:
    """A result without any network, or None if the domain still needs looking up."""
    email = email.strip()
    if not EMAIL_RE.match(email) or ".." in email:
        return "bad-format"
    domain = email.rsplit("@", 1)[1].lower()
    if domain in TYPOS:
        return f"typo (did they mean {TYPOS[domain]}?)"
    return None


def check(email: str, cache: dict[str, str] | None = None) -> str:
    early = check_format(email)
    if early:
        return early
    domain = email.strip().rsplit("@", 1)[1].lower()
    if cache is not None and domain in cache:
        return cache[domain]
    result = check_domain(domain)
    if cache is not None and result != "unknown":
        cache[domain] = result
    return result
