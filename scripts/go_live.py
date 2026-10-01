"""Go live without breaking their email: save their DNS before the switch, then check the launch.

    python scripts/go_live.py dns   kerrroofing.co.uk [--folder kerr-roofing] [--fresh]
    python scripts/go_live.py check kerrroofing.co.uk [--folder kerr-roofing]

The one thing that turns a launch into an emergency is the client's email stopping, because a
record didn't come across when their nameservers moved to Cloudflare (docs/launching-a-client-site.md,
step 5). So:

  dns    BEFORE you touch anything: reads every record their email depends on (MX, SPF, DMARC, DKIM
         for the usual providers, autodiscover and mail CNAMEs) and saves it - outreach/sites/<folder>/
         dns-before.json, or outreach/dns/<domain>.json without a folder. Says who hosts their email.
         Run it again after the switch and it compares: anything missing or changed is listed, in
         red, with what to add in Cloudflare. The first snapshot is never overwritten (--fresh does).

  check  AFTER launch: the 15-minute checklist, done for you - https on both the bare domain and www,
         http goes to https, a made-up page gives a real 404, sitemap.xml and robots.txt are there,
         nothing says noindex or "Draft", the dashboard's tracking and the quote form are on the site,
         and how long the certificate has left. Then the email records again, if a snapshot exists.

Read-only: it only looks things up (Google's public DNS, and the site itself). Nothing is changed.
"""

from __future__ import annotations

import argparse
import json
import re
import socket
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

DOH = "https://dns.google/resolve"
TIMEOUT = 20
UA = "Mozilla/5.0 (compatible; ScalarLaunchCheck/1.0)"

# What their email depends on. DKIM lives under a selector only the provider knows, so the usual
# ones are tried: Google Workspace, Microsoft 365, and the common defaults hosts and senders use.
DKIM_SELECTORS = ["google", "selector1", "selector2", "default", "k1", "k2", "s1", "s2", "dkim", "mail", "mxvault"]
EMAIL_NAMES = ["autodiscover", "mail", "webmail", "smtp", "imap", "pop", "_autodiscover._tcp"]
TYPES = {1: "A", 5: "CNAME", 15: "MX", 16: "TXT", 28: "AAAA", 2: "NS", 33: "SRV"}


def lookup(name: str, rtype: str) -> list[str]:
    """Answers for one name and type, as plain strings (sorted, so snapshots compare cleanly)."""
    url = f"{DOH}?{urllib.parse.urlencode({'name': name, 'type': rtype})}"
    req = urllib.request.Request(url, headers={"accept": "application/dns-json", "User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        data = json.load(r)
    out = []
    for a in data.get("Answer") or []:
        if TYPES.get(a.get("type")) != rtype:
            continue  # a CNAME on the way to the answer, not the answer
        value = str(a.get("data", "")).strip()
        if rtype == "TXT":
            value = "".join(re.findall(r'"([^"]*)"', value)) or value.strip('"')
        out.append(value.rstrip(".").lower() if rtype in ("MX", "CNAME", "NS") else value)
    return sorted(set(out))


def snapshot(domain: str, ask=lookup) -> dict:
    """Every record their email (and their site) depends on, keyed 'name TYPE'."""
    records: dict[str, list[str]] = {}

    def get(name: str, rtype: str) -> None:
        values = ask(name, rtype)
        if values:
            records[f"{name} {rtype}"] = values

    for rtype in ("NS", "MX", "TXT", "A"):
        get(domain, rtype)
    get(f"_dmarc.{domain}", "TXT")
    for sel in DKIM_SELECTORS:
        get(f"{sel}._domainkey.{domain}", "TXT")
        get(f"{sel}._domainkey.{domain}", "CNAME")
    for sub in EMAIL_NAMES:
        name = f"{sub}.{domain}"
        if sub.startswith("_"):
            get(name, "SRV")
        else:
            get(name, "CNAME")
            if f"{name} CNAME" not in records:
                get(name, "A")
    return {"domain": domain, "taken": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"), "records": records}


def email_host(records: dict[str, list[str]], domain: str) -> str:
    mx = " ".join(records.get(f"{domain} MX", []))
    if not mx:
        return "nobody - there are no MX records, so this domain doesn't receive email"
    for needle, who in (("google", "Google Workspace"), ("googlemail", "Google Workspace"), ("outlook.com", "Microsoft 365"),
                        ("protection.outlook", "Microsoft 365"), ("zoho", "Zoho Mail"), ("ionos", "IONOS"), ("123-reg", "123-reg"),
                        ("secureserver", "GoDaddy"), ("titan", "Titan (via their registrar)"), ("mimecast", "Mimecast"),
                        ("fasthosts", "Fasthosts"), ("livemail", "Fasthosts"), ("names.co.uk", "Names.co.uk"), ("krystal", "Krystal")):
        if needle in mx:
            return who
    return f"their own or their registrar's mail server ({mx.split()[-1]})"


# Records that are SUPPOSED to change when the site moves: nameservers and the site's own address.
EXPECTED_TO_CHANGE = re.compile(r"^\S+ (NS|A|AAAA)$")


def compare(before: dict, after: dict) -> list[str]:
    """Problems: email records that existed before and are now missing or different."""
    problems = []
    domain = before["domain"]
    for key, old in sorted(before["records"].items()):
        name, rtype = key.split(" ")
        if EXPECTED_TO_CHANGE.match(key) and not (rtype == "A" and name != domain):
            continue
        new = after["records"].get(key, [])
        if rtype == "TXT" and name == domain:
            # The apex TXT holds SPF and verification records; any one of them going missing matters.
            missing = [v for v in old if v not in new]
            for v in missing:
                problems.append(f"MISSING  {name} TXT  \"{v}\"")
            continue
        if not new:
            problems.append(f"MISSING  {name} {rtype}  {', '.join(old)}")
        elif new != old:
            problems.append(f"CHANGED  {name} {rtype}  was {', '.join(old)}  now {', '.join(new)}")
    return problems


def snapshot_path(outreach: Path, domain: str, folder: str | None) -> Path:
    return outreach / "sites" / folder / "dns-before.json" if folder else outreach / "dns" / f"{domain}.json"


def print_snapshot(snap: dict) -> None:
    for key, values in sorted(snap["records"].items()):
        for v in values:
            print(f"  {key:<45} {v}")


def run_dns(domain: str, outreach: Path, folder: str | None, fresh: bool, ask=lookup) -> int:
    path = snapshot_path(outreach, domain, folder)
    now = snapshot(domain, ask)
    rec = now["records"]
    print(f"Email for {domain} is hosted by: {email_host(rec, domain)}")
    if path.exists() and not fresh:
        before = json.loads(path.read_text(encoding="utf-8"))
        print(f"Comparing with the snapshot from {before['taken']} ({path.name}).")
        return report_compare(before, now)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(now, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(rec)} records to {path}:")
    print_snapshot(now)
    spf = [v for v in rec.get(f"{domain} TXT", []) if v.lower().startswith("v=spf1")]
    if f"{domain} MX" in rec and not spf:
        print("Note: they receive email but have no SPF record - not your doing, but worth telling them.")
    if f"_dmarc.{domain} TXT" not in rec and f"{domain} MX" in rec:
        print("Note: no DMARC record - again not your doing; their email still works without it.")
    print("NEXT: add their domain in Cloudflare, check every record above came across (MX and TXT especially),")
    print("then change the nameservers. Afterwards run this again (or Check the launch) to compare.")
    return 0


def report_compare(before: dict, after: dict) -> int:
    problems = compare(before, after)
    if not problems:
        print("EMAIL OK: every email record from before the switch is still there, unchanged.")
        return 0
    print("STOP - EMAIL AT RISK: these records were there before the switch and aren't now.")
    print("Add them in Cloudflare > their domain > DNS > Records, exactly as shown (Cloudflare can take a few")
    print("minutes to answer with them). Their email may bounce until they're back:")
    for p in problems:
        print(f"  {p}")
    return 1


# ---------------------------------------------------------------- the site checks


def fetch(url: str) -> tuple[int, str, str]:
    """(status, final url, body) - following redirects; an HTTP error is a status, not an exception."""
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.geturl(), r.read(600_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, e.read(200_000).decode("utf-8", "replace") if e.fp else ""


def cert_days(host: str) -> int:
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=TIMEOUT) as sock, ctx.wrap_socket(sock, server_hostname=host) as s:
        expires = ssl.cert_time_to_seconds(s.getpeercert()["notAfter"])
    return int((expires - datetime.now(timezone.utc).timestamp()) // 86400)


def site_checks(domain: str, get=fetch, days=cert_days) -> list[tuple[bool, str]]:
    """(passed, what) for each launch check."""
    out: list[tuple[bool, str]] = []

    def check(ok: bool, good: str, bad: str) -> None:
        out.append((ok, good if ok else bad))

    def safe(url: str) -> tuple[int, str, str]:
        try:
            return get(url)
        except (urllib.error.URLError, OSError, ValueError) as e:
            return 0, url, f"{type(e).__name__}: {getattr(e, 'reason', e)}"

    status, final, home = safe(f"https://{domain}/")
    check(status == 200, f"https://{domain} loads", f"https://{domain} doesn't load ({status or home})")
    w_status, w_final, _ = safe(f"https://www.{domain}/")
    check(w_status == 200, f"https://www.{domain} loads too", f"https://www.{domain} doesn't load ({w_status}) - add www as a custom domain in the Pages project")
    h_status, h_final, _ = safe(f"http://{domain}/")
    check(h_final.startswith("https://"), "http:// goes to https://", "http:// doesn't move to https:// - turn on Always Use HTTPS in Cloudflare (SSL/TLS > Edge Certificates)")
    n_status, _, _ = safe(f"https://{domain}/this-page-does-not-exist-{int(datetime.now().timestamp())}")
    check(n_status == 404, "a made-up page gives a proper 404", f"a made-up page gives {n_status}, not 404 - is 404.html in the site folder?")
    s_status, _, sitemap = safe(f"https://{domain}/sitemap.xml")
    check(s_status == 200 and "<urlset" in sitemap, "sitemap.xml is there", "no sitemap.xml - rebuild with Build site and publish again")
    r_status, _, robots = safe(f"https://{domain}/robots.txt")
    blocked = bool(re.search(r"(?im)^disallow:\s*/\s*$", robots))
    check(r_status == 200 and not blocked, "robots.txt lets Google in", "robots.txt is missing or blocks Google")
    if status == 200:
        check(not re.search(r'<meta[^>]+name=["\']robots["\'][^>]+noindex', home, re.I), "the homepage can be indexed",
              "the homepage says noindex - it's a draft build; finish site.json, Build site without Draft, publish again")
        check("draft-banner" not in home, "no draft banner", "the draft banner is showing - publish the real build")
        check("/track.js" in home, "the dashboard's tracking is on the page", "no track.js on the homepage - page views and enquiries won't reach the dashboard")
        c_status, _, contact = safe(f"https://{domain}/contact.html")
        check(c_status == 200 and "data-lead-form" in contact, "the quote form is wired to the dashboard",
              "the contact page's form isn't wired to the dashboard (no data-lead-form)")
    try:
        left = days(domain)
        check(left > 14, f"certificate fine ({left} days left; Cloudflare renews it)", f"certificate expires in {left} days")
    except (OSError, ssl.SSLError, KeyError, ValueError) as e:
        check(False, "", f"couldn't check the certificate ({type(e).__name__})")
    return out


def run_check(domain: str, outreach: Path, folder: str | None, ask=lookup, get=fetch, days=cert_days) -> int:
    results = site_checks(domain, get, days)
    for ok, what in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {what}")
    failed = sum(1 for ok, _ in results if not ok)
    code = 1 if failed else 0
    path = snapshot_path(outreach, domain, folder)
    if path.exists():
        before = json.loads(path.read_text(encoding="utf-8"))
        print(f"Email records, against the snapshot from {before['taken']}:")
        code |= report_compare(before, snapshot(domain, ask))
    else:
        print("No DNS snapshot from before the switch, so email records weren't compared. Send a test email to")
        print("and from their address instead.")
    print("Still by hand: tap-to-call and WhatsApp on your phone, a test enquiry (arrives in the dashboard and")
    print("by email), and a test email to and from their address.")
    if not code:
        print(f"READY: {domain} passed every check.")
    elif failed:
        print(f"Not ready: {failed} site check(s) failed (above).")
    else:
        print("Not ready: the site's fine, but email records need fixing (above).")
    return code


def outreach_dir() -> Path:
    import reply_scanner
    return reply_scanner.outreach_dir()


def main() -> None:
    from push_prospects import domain_of

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("command", choices=["dns", "check"])
    ap.add_argument("domain")
    ap.add_argument("--folder", help="their folder under outreach/sites (the snapshot is kept there)")
    ap.add_argument("--fresh", action="store_true", help="dns: take a new 'before' snapshot instead of comparing")
    args = ap.parse_args()
    domain = domain_of(args.domain)
    if not domain:
        sys.exit("Give their domain, e.g. kerrroofing.co.uk")
    folder = args.folder if args.folder and (outreach_dir() / "sites" / args.folder).is_dir() else None
    try:
        if args.command == "dns":
            sys.exit(run_dns(domain, outreach_dir(), folder, args.fresh))
        sys.exit(run_check(domain, outreach_dir(), folder))
    except (urllib.error.URLError, OSError) as e:
        sys.exit(f"Couldn't look up {domain}'s DNS ({type(e).__name__}) - check the internet connection and try again.")


if __name__ == "__main__":
    main()
