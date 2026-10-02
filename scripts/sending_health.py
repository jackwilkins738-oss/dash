"""Is your email still landing? A daily check of everything a spam filter looks at before your words.

    python scripts/sending_health.py

For every sending inbox's own domain (Gmail/Outlook addresses are the provider's job) it checks:

    MX      somewhere for replies to land
    SPF     exactly one record, not "+all", and including Google when Google hosts the mail
    DKIM    a signing key under one of the usual selectors (Google Workspace's is "google")
    DMARC   a policy record - Google and Yahoo expect one from anyone sending in volume

...and whether that domain, or your website's (every email links to it), is on the Spamhaus, SURBL or
URIBL domain blocklists. One listing is enough to send a whole batch to spam without a single bounce,
so you'd never know - this is how you know.

The result is kept in outreach/sending-health.json for the panel's health strip; a new problem texts you
(Telegram), and a blocklisting stops sending until the next clean check. The autopilot runs it every
morning before it sends anything. Read-only: it only asks public DNS.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

FILE = "sending-health.json"
FREE = {"gmail.com", "googlemail.com", "outlook.com", "hotmail.com", "hotmail.co.uk", "live.com", "live.co.uk",
        "yahoo.com", "yahoo.co.uk", "icloud.com", "me.com", "aol.com", "btinternet.com", "sky.com"}
# (name, zone, a test entry the list always reports as listed - asked first, so "not listed" is only
# believed from a list that's really answering this computer)
BLOCKLISTS = [("Spamhaus", "dbl.spamhaus.org", "dbltest.com"), ("SURBL", "multi.surbl.org", "test.surbl.org"),
              ("URIBL", "multi.uribl.com", "test.uribl.com")]
STALE_HOURS = 48
DNS_TIMEOUT_S = 10  # a blocklisting older than this no longer stops sending - check again instead


def _ask():
    from go_live import lookup

    return lookup


def system_dns(name: str) -> list[str]:
    """A-record answers from this computer's own resolver - blocklists refuse the big public ones, but
    usually answer a home or office connection. No answer at all comes back as []."""
    import socket
    from concurrent.futures import ThreadPoolExecutor
    from concurrent.futures import TimeoutError as Slow

    def ask() -> list[str]:
        try:
            return socket.gethostbyname_ex(name)[2]
        except (socket.gaierror, socket.herror, UnicodeError):
            return []

    # The system resolver has no timeout of its own; a slow one must never hold up the morning run.
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        return pool.submit(ask).result(timeout=DNS_TIMEOUT_S)
    except Slow as e:
        raise OSError(f"DNS took over {DNS_TIMEOUT_S}s") from e
    finally:
        pool.shutdown(wait=False)


def _hit(answers: list[str]) -> bool | None:
    if not answers:
        return False
    # 127.0.0.1 (SURBL/URIBL) and 127.255.255.x (Spamhaus) mean "query refused", not "listed".
    if all(a == "127.0.0.1" or a.startswith("127.255.255.") for a in answers):
        return None
    return any(a.startswith("127.") for a in answers)


def listed(domain: str, zone: str, test: str, resolve=system_dns) -> bool | None:
    """True if listed, False if not, None if this list isn't really answering us (its test entry didn't
    come back listed - so a 'no' from it would mean nothing)."""
    try:
        if _hit(resolve(f"{test}.{zone}")) is not True:
            return None
        return _hit(resolve(f"{domain}.{zone}"))
    except OSError:
        return None


def check_mail_domain(domain: str, ask) -> list[tuple[str, str]]:
    """[(level, text)] for one sending domain; level is ok, warn or bad."""
    from go_live import DKIM_SELECTORS

    out: list[tuple[str, str]] = []
    failed: list[str] = []

    def get(name: str, rtype: str) -> list[str]:
        try:
            return ask(name, rtype)
        except (OSError, ValueError):
            failed.append(name)
            return []

    mx = get(domain, "MX")
    if failed:  # no answer at all is "couldn't check", never "you have no MX"
        return [("unknown", f"Couldn't reach DNS to check {domain} - is the internet up? Try again.")]
    out.append(("ok", "MX: replies have somewhere to land") if mx else
               ("bad", "No MX record - replies to this address can't arrive. Check the domain's DNS."))
    google = any("google" in m for m in mx)
    spf = [t for t in get(domain, "TXT") if t.lower().startswith("v=spf1")]
    if not spf:
        out.append(("bad", "No SPF record - receivers can't tell this mail is really yours. Add: "
                           + ("v=spf1 include:_spf.google.com ~all" if google else "the SPF line your email provider gives you")))
    elif len(spf) > 1:
        out.append(("bad", f"{len(spf)} SPF records - with more than one, SPF fails outright. Merge them into one."))
    elif "+all" in spf[0].lower():
        out.append(("bad", "SPF ends in +all - that lets anyone send as you, and filters treat it as a red flag. Use ~all."))
    elif google and "_spf.google.com" not in spf[0].lower():
        out.append(("warn", "SPF doesn't include Google (include:_spf.google.com), but Google hosts this mail."))
    else:
        out.append(("ok", "SPF set up"))
    dkim = [s for s in DKIM_SELECTORS if any("p=" in t for t in get(f"{s}._domainkey.{domain}", "TXT"))]
    out.append(("ok", f"DKIM signing key found ({dkim[0]})") if dkim else
               ("warn", "No DKIM key found - unsigned mail is far likelier to go to spam. Google Workspace: Admin -> "
                        "Apps -> Gmail -> Authenticate email -> Generate, add the record, then Start authentication."))
    dmarc = [t for t in get(f"_dmarc.{domain}", "TXT") if t.lower().startswith("v=dmarc1")]
    if not dmarc:
        out.append(("warn", "No DMARC record - Google and Yahoo expect one from bulk senders. Start with: "
                            f"_dmarc.{domain}  TXT  v=DMARC1; p=none; rua=mailto:you@{domain}"))
    else:
        out.append(("ok", "DMARC set up" + (" (p=none - fine while you're starting)" if "p=none" in dmarc[0].lower() else "")))
    if failed:  # a lookup that failed part-way: say so rather than trust a half-answer
        return [("unknown", f"DNS stopped answering part-way through checking {domain} - try again.")]
    return out


def check_blocklists(domain: str, resolve=system_dns) -> list[tuple[str, str]]:
    out = []
    unknown = []
    for name, zone, test in BLOCKLISTS:
        hit = listed(domain, zone, test, resolve)
        if hit:
            out.append(("bad", f"{domain} is on the {name} blocklist - emails from or linking to it go to spam. "
                               f"Stop sending and check it at {name.lower()}'s lookup page."))
        elif hit is None:
            unknown.append(name)
    if not out:
        checked = [n for n, _, _ in BLOCKLISTS if n not in unknown]
        out.append(("ok", f"{domain}: not on {', '.join(checked)}" if checked else f"{domain}: blocklists didn't answer this time"))
    return out


def domains_to_check(env: dict) -> tuple[list[str], list[str]]:
    """(sending domains to check fully, domains to check against blocklists only)."""
    import mail_accounts

    sending = []
    for a in mail_accounts.accounts(env):
        d = a.address.split("@", 1)[-1].lower()
        if d not in FREE and d not in sending:
            sending.append(d)
    site = (env.get("SITE_URL") or "https://www.scalardigital.co.uk").split("//", 1)[-1].split("/", 1)[0].lower()
    site = site.removeprefix("www.")
    return sending, [d for d in [site] if d and d not in sending]


def run(env: dict, ask=None, resolve=system_dns) -> dict:
    ask = ask or _ask()
    sending, links = domains_to_check(env)
    report: dict[str, list[tuple[str, str]]] = {}
    for d in sending:
        report[d] = check_mail_domain(d, ask) + check_blocklists(d, resolve)
    for d in links:
        report[d] = check_blocklists(d, resolve)
    problems = [f"{d}: {text}" for d, items in report.items() for level, text in items if level == "bad"]
    warnings = [f"{d}: {text}" for d, items in report.items() for level, text in items if level == "warn"]
    blocked = [p for p in problems if "blocklist" in p]
    return {"checked_at": datetime.now().isoformat(timespec="minutes"), "domains": report,
            "problems": problems, "warnings": warnings, "blocked": blocked}


def load(outreach: Path) -> dict:
    try:
        return json.loads((outreach / FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def stop_sending(outreach: Path, now: datetime | None = None) -> str:
    """Why sending should stop, or '' - only a recent, confirmed blocklisting stops it."""
    last = load(outreach)
    if not last.get("blocked"):
        return ""
    try:
        age = ((now or datetime.now()) - datetime.fromisoformat(last["checked_at"])).total_seconds() / 3600
    except (KeyError, ValueError):
        return ""
    if age > STALE_HOURS:
        return ""
    return "Sending is paused: " + last["blocked"][0] + " Run Check sending health again once it's cleared."


def new_problems(before: dict, after: dict) -> list[str]:
    return [p for p in after.get("problems", []) + after.get("warnings", [])
            if p not in set(before.get("problems", []) + before.get("warnings", []))]


def alert(text: str) -> None:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN", ""), os.environ.get("TELEGRAM_CHAT_ID", "")
    if not (token and chat):
        return
    try:
        req = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage",
                                     data=json.dumps({"chat_id": chat, "text": text}).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15).close()
    except OSError:
        pass


def main() -> int:
    import reply_scanner

    outreach = reply_scanner.outreach_dir()
    outreach.mkdir(exist_ok=True)
    before = load(outreach)
    result = run(dict(os.environ))
    if not result["domains"]:
        print("No sending inbox in Settings yet - add MAIL_ADDRESS first.")
    for domain, items in result["domains"].items():
        print(f"{domain}")
        for level, text in items:
            print(f"  {dict(ok='OK  ', warn='WARN', bad='BAD ').get(level, '??  ')} {text}")
    (outreach / FILE).write_text(json.dumps(result, indent=2), encoding="utf-8")
    fresh = new_problems(before, result)
    if fresh:
        alert("Sending health - new problem:\n\n" + "\n\n".join(fresh[:5]))
    if result["blocked"]:
        print("\nSending is paused until a clean check - a blocklisting sends whole batches to spam.")
    elif result["problems"]:
        print(f"\n{len(result['problems'])} problem(s) to fix - mail may be going to spam.")
    elif result["warnings"]:
        print(f"\nWorking, with {len(result['warnings'])} thing(s) worth fixing.")
    else:
        print("\nAll clear.")
    return 1 if result["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
