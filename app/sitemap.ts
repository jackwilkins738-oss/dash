import type { MetadataRoute } from 'next'
import { TRADES } from '@/lib/trades'
import { SITE, UPDATED } from '@/lib/site'
import { lastmod } from '@/lib/seo'

// `lastModified` is the date the page's content last really changed (see lib/site.ts), not the
// build time. A date that changes on every deploy teaches Google to ignore the field.
export default function sitemap(): MetadataRoute.Sitemap {
  const at = (path: string, lastModified: string, priority: number): MetadataRoute.Sitemap[number] => ({
    url: `${SITE.url}${path}`,
    lastModified: lastmod(path || '/', lastModified),
    priority,
  })

  return [
    at('', UPDATED, 1),
    at('/work', UPDATED, 0.9),
    ...TRADES.map((t) => at(`/websites-for/${t.slug}`, UPDATED, 0.8)),
    at('/guides', UPDATED, 0.6),
    at('/guides/how-much-does-a-tradesman-website-cost', UPDATED, 0.8),
    at('/guides/website-or-facebook-page-for-tradesmen', UPDATED, 0.8),
    at('/guides/google-business-profile-for-tradesmen', '2026-09-28', 0.7),
    at('/guides/how-to-get-more-google-reviews', '2026-09-28', 0.7),
    at('/guides/checkatrade-or-your-own-website', '2026-10-01', 0.7),
    at('/guides/wix-or-hand-coded-website-for-tradesmen', '2026-10-01', 0.7),
    at('/guides/website-not-getting-enquiries', '2026-10-02', 0.7),
    at('/guides/is-a-website-worth-it-for-tradesmen', '2026-10-02', 0.7),
    at('/process', UPDATED, 0.6),
    at('/speed-test', UPDATED, 0.7),
    at('/contact', UPDATED, 0.7),
    at('/refer', UPDATED, 0.4),
    at('/partners', '2026-09-29', 0.4),
    at('/privacy', '2026-09-26', 0.2),
  ]
}
