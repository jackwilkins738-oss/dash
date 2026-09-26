"""Offline tests for site_teardown's HTML checks - no network.

Run: python -m unittest scripts/test_site_teardown.py
"""

import unittest

from site_teardown import analyse_html, copyright_year, visible_text_length

FILLER = "<p>" + ("We do roofing across Surrey, from repairs to full re-roofs. " * 12) + "</p>"


def page(body: str, head: str = "") -> str:
    return f"<html><head>{head}</head><body>{body}{FILLER}</body></html>"


class AnalyseHtml(unittest.TestCase):
    def test_finds_links_form_and_schema_when_present(self):
        html = page(
            '<a href="tel:01483000000">Call</a><a href="https://wa.me/447700900000">WhatsApp</a>'
            '<form><input type="email" name="email"><textarea></textarea></form>',
            '<script type="application/ld+json">{"@context":"https://schema.org","@type":"RoofingContractor"}</script>',
        )
        checks = analyse_html(html, "https://example.com/")["checks"]
        self.assertEqual(
            checks,
            {"tapToCall": True, "whatsapp": True, "contactForm": True, "localSchema": True},
        )

    def test_reports_missing_links_and_form_on_a_content_page(self):
        checks = analyse_html(page("<p>Call us on 01483 000000</p>"), "https://example.com/")["checks"]
        self.assertFalse(checks["tapToCall"])
        self.assertFalse(checks["whatsapp"])
        self.assertFalse(checks["contactForm"])
        self.assertFalse(checks["localSchema"])

    def test_skips_link_and_form_checks_on_a_browser_rendered_shell(self):
        shell = '<html><body><div id="root"></div><script src="/app.js"></script></body></html>'
        checks = analyse_html(shell, "https://example.com/")["checks"]
        for key in ("tapToCall", "whatsapp", "contactForm"):
            self.assertNotIn(key, checks, f"{key} must be left unchecked, not reported missing")

    def test_a_call_button_added_by_javascript_counts(self):
        html = page("<p>No links in the HTML itself</p>")
        self.assertFalse(analyse_html(html, None)["checks"]["tapToCall"])
        script = "bar.innerHTML = '<a href=\"tel:01892000000\">Call</a><a href=\"https://wa.me/447700900123\">WA</a>'"
        checks = analyse_html(html, None, [script])["checks"]
        self.assertTrue(checks["tapToCall"])
        self.assertTrue(checks["whatsapp"])

    def test_counts_an_embedded_form_provider(self):
        html = page('<div class="wpforms-container"></div>')
        self.assertTrue(analyse_html(html, None)["checks"]["contactForm"])

    def test_schema_in_a_graph_and_microdata(self):
        graph = '<script type="application/ld+json">{"@graph":[{"@type":"WebSite"},{"@type":["LocalBusiness"]}]}</script>'
        self.assertTrue(analyse_html(page("", graph), None)["checks"]["localSchema"])
        micro = page('<div itemscope itemtype="https://schema.org/HomeAndConstructionBusiness"></div>')
        self.assertTrue(analyse_html(micro, None)["checks"]["localSchema"])

    def test_platform_and_homepage_plugin_count(self):
        html = page(
            '<link href="/wp-content/plugins/elementor/a.css"><script src="/wp-content/plugins/jetpack/b.js"></script>'
            '<script src="/wp-content/plugins/elementor/c.js"></script>'
        )
        out = analyse_html(html, None)
        self.assertEqual(out["platform"], "wordpress")
        self.assertEqual(out["wpPluginCount"], 2)
        self.assertEqual(analyse_html(page('<img src="https://static.wixstatic.com/x.jpg">'), None)["platform"], "wix")

    def test_plain_http_is_flagged(self):
        self.assertFalse(analyse_html(page(""), "http://example.com/")["checks"]["https"])
        self.assertNotIn("https", analyse_html(page(""), "https://example.com/")["checks"])


class CopyrightYear(unittest.TestCase):
    def test_reads_single_years_and_ranges(self):
        self.assertEqual(copyright_year("<footer>© 2019 Smith Roofing</footer>"), 2019)
        self.assertEqual(copyright_year("<footer>&copy; 2015 - 2021 Smith Roofing Ltd</footer>"), 2021)
        self.assertEqual(copyright_year("<footer>Copyright Smith Roofing 2018–2024</footer>"), 2024)

    def test_none_when_the_year_is_written_by_script(self):
        self.assertIsNone(copyright_year("<footer>© <script>document.write(new Date().getFullYear())</script></footer>"))

    def test_ignores_years_away_from_a_copyright_mark(self):
        self.assertIsNone(copyright_year("<p>Established 1998. Over 20 years of roofing.</p>"))


class VisibleText(unittest.TestCase):
    def test_ignores_scripts_and_styles(self):
        self.assertEqual(visible_text_length("<script>var x = 'lots of text here';</script><style>a{}</style><p>Hi</p>"), 2)


if __name__ == "__main__":
    unittest.main()
