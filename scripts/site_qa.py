"""Pre-launch QA for a built client site: what would embarrass you, caught before anyone sees it.

    python scripts/site_qa.py kerr-roofing

Reads outreach/sites/<firm>/site/ (what Build site wrote) - nothing online - and checks every page:

    links       every internal link, image, script and stylesheet points at a file that exists
    pages       a <title> (unique across pages), a meta description, one <h1>, lang="en-GB"
    images      every <img> has alt text (alt="" is fine for decoration); none over 500 KB
    data        every Google structured-data block is valid JSON
    leftovers   no "[Confirm", TODO or lorem ipsum anywhere a visitor could see
    contact     the quote form is wired to the dashboard; phone links are in +44 form
    files       404.html, robots.txt that lets Google in, a sitemap listing every real page,
                and every _redirects target exists

Publish site runs it first and won't publish a site with problems (warnings don't stop it).
The live checks after the domain is switched are go_live.py's "Check the launch".
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

BIG_IMAGE = 500_000
LEFTOVER = re.compile(r"\[confirm|\btodo\b|lorem ipsum", re.I)
NOT_INDEXED = {"thanks.html", "404.html"}


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.imgs: list[dict] = []
        self.title = ""
        self.description = None
        self.h1 = 0
        self.lang = ""
        self.tels: list[str] = []
        self.ld: list[str] = []
        self.lead_form = False
        self.text: list[str] = []
        self._in = ""
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang") or ""
        if tag in ("a", "link") and a.get("href"):
            href = a["href"]
            if href.startswith("tel:"):
                self.tels.append(href)
            elif not (tag == "link" and (a.get("rel") or "") in ("preconnect", "dns-prefetch", "canonical", "alternate")):
                self.links.append(href)
        if tag in ("img", "script", "source") and a.get("src"):
            self.links.append(a["src"])
        if tag == "img":
            self.imgs.append(a)
        if tag == "meta" and (a.get("name") or "").lower() == "description":
            self.description = a.get("content") or ""
        if tag == "h1":
            self.h1 += 1
        if tag == "form" and "data-lead-form" in a:
            self.lead_form = True
        if tag == "title" or (tag == "script" and a.get("type") == "application/ld+json"):
            self._in, self._buf = ("title" if tag == "title" else "ld"), []
        if tag in ("script", "style") and self._in != "ld":
            self._in = "skip"

    def handle_endtag(self, tag):
        if self._in == "title" and tag == "title":
            self.title = "".join(self._buf).strip()
        elif self._in == "ld" and tag == "script":
            self.ld.append("".join(self._buf))
        if tag in ("title", "script", "style"):
            self._in = ""

    def handle_data(self, data):
        if self._in in ("title", "ld"):
            self._buf.append(data)
        elif self._in != "skip":
            self.text.append(data)


def _target(site: Path, page: Path, link: str) -> Path | None:
    """The file a link points at, or None when it isn't ours to check (another site, mailto, an anchor)."""
    link = link.split("#", 1)[0].split("?", 1)[0]
    if not link or re.match(r"^[a-z][a-z0-9+.-]*:", link, re.I) or link.startswith("//"):
        return None
    path = site / link.lstrip("/") if link.startswith("/") else page.parent / link
    if link.endswith("/"):
        path = path / "index.html"
    return path


PREVIEW_OK = ("robots.txt blocks Google", "placeholder text left in")


def check(site: Path, preview: bool = False) -> tuple[list[str], list[str]]:
    """(problems, warnings) for a built site folder. preview: a draft for the client to review - its
    noindex robots.txt and [Confirm notes are expected there, everything else still has to work."""
    problems, warnings = _check(site)
    if preview:
        problems = [p for p in problems if not any(ok in p for ok in PREVIEW_OK)]
    elif (site / "feedback.js").exists():
        problems.append("feedback.js is in the build - that's the draft's Leave feedback button; build without Draft")
    return problems, warnings


def _check(site: Path) -> tuple[list[str], list[str]]:
    problems: list[str] = []
    warnings: list[str] = []
    if not site.is_dir():
        return [f"There's no built site at {site} - press Build site first."], []
    pages = sorted(site.rglob("*.html"))
    if not pages:
        return [f"{site} has no pages - press Build site first."], []
    titles: dict[str, str] = {}
    for page in pages:
        rel = page.relative_to(site).as_posix()
        p = Page()
        p.feed(page.read_text(encoding="utf-8", errors="replace"))
        for link in dict.fromkeys(p.links):
            target = _target(site, page, link)
            if target is not None and not target.exists() and not (target.with_suffix(".html").exists() and not target.suffix):
                problems.append(f"{rel}: broken link to {link}")
        if not p.title:
            problems.append(f"{rel}: no <title>")
        elif p.title in titles and rel not in NOT_INDEXED and titles[p.title] not in NOT_INDEXED:
            warnings.append(f"{rel}: same title as {titles[p.title]} ('{p.title}') - Google prefers each page different")
        titles.setdefault(p.title, rel)
        if rel not in NOT_INDEXED:
            if not (p.description or "").strip():
                warnings.append(f"{rel}: no meta description")
            if p.h1 != 1:
                warnings.append(f"{rel}: {p.h1} <h1> headings - there should be exactly one")
        if not p.lang.lower().startswith("en"):
            warnings.append(f"{rel}: no lang=\"en-GB\" on <html>")
        for img in p.imgs:
            if "alt" not in img:
                problems.append(f"{rel}: image {img.get('src', '?')} has no alt text (screen readers and Google read it)")
        for block in p.ld:
            try:
                json.loads(block)
            except ValueError:
                problems.append(f"{rel}: a structured-data block isn't valid JSON - Google will ignore it")
        for t in p.tels:
            if not re.fullmatch(r"tel:\+44\d{9,10}", t):
                warnings.append(f"{rel}: phone link {t} isn't in +44 form - some phones won't dial it")
        visible = " ".join(p.text)
        if LEFTOVER.search(visible) or LEFTOVER.search(p.title):
            problems.append(f"{rel}: placeholder text left in ('[Confirm', TODO or lorem ipsum)")
        if rel == "contact.html" and not p.lead_form:
            problems.append("contact.html: the quote form isn't wired to the dashboard (no data-lead-form)")
    for img in sorted(site.rglob("*")):
        if img.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp") and img.stat().st_size > BIG_IMAGE:
            warnings.append(f"{img.relative_to(site).as_posix()}: {img.stat().st_size // 1000} KB - shrink it, phones pay for every KB")
    if not (site / "404.html").exists():
        problems.append("no 404.html - a mistyped address shows a bare error")
    robots = (site / "robots.txt").read_text(encoding="utf-8") if (site / "robots.txt").exists() else ""
    if not robots:
        problems.append("no robots.txt")
    elif re.search(r"(?im)^disallow:\s*/\s*$", robots):
        problems.append("robots.txt blocks Google - this is a draft build; build without Draft before publishing")
    sitemap = (site / "sitemap.xml").read_text(encoding="utf-8") if (site / "sitemap.xml").exists() else ""
    if not sitemap:
        problems.append("no sitemap.xml")
    else:
        for page in pages:
            rel = page.relative_to(site).as_posix()
            if rel not in NOT_INDEXED and rel.removesuffix("index.html") not in sitemap and rel not in sitemap:
                warnings.append(f"sitemap.xml doesn't list {rel}")
    if (site / "_redirects").exists():
        for line in (site / "_redirects").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 2 and not line.startswith("#"):
                target = _target(site, site / "index.html", parts[1])
                if target is not None and not target.exists() and not target.with_suffix(".html").exists():
                    problems.append(f"_redirects: {parts[0]} goes to {parts[1]}, which doesn't exist")
    return problems, warnings


def report(site: Path) -> int:
    problems, warnings = check(site)
    for p in problems:
        print(f"PROBLEM  {p}")
    for w in warnings:
        print(f"warning  {w}")
    pages = len(list(site.rglob("*.html"))) if site.is_dir() else 0
    if problems:
        print(f"\n{len(problems)} problem(s) - fix them in site.json, Build site again, then check again.")
        return 1
    print(f"\nQA passed: {pages} pages" + (f", {len(warnings)} warning(s) worth a look." if warnings else ", nothing to fix."))
    return 0


def main() -> None:
    import site_kit

    if len(sys.argv) != 2 or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,80}", sys.argv[1]):
        sys.exit("Usage: python scripts/site_qa.py <folder under outreach/sites>, e.g. kerr-roofing")
    sys.exit(report(site_kit.outreach_dir() / "sites" / sys.argv[1] / "site"))


if __name__ == "__main__":
    main()
