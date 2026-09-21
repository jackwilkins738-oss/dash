import type { MetadataRoute } from 'next'
import { TRADES } from '@/lib/trades'
import { SITE, UPDATED } from '@/lib/site'

// `lastModified` is the date the page's content last really changed (see lib/site.ts), not the
// build time. A date that changes on every deploy teaches Google to ignore the field.
export default function sitemap(): MetadataRoute.Sitemap {
  const at = (path: string, lastModified: string, priority: number): MetadataRoute.Sitemap[number] => ({
    url: `${SITE.url}${path}`,
    lastModified,
    priority,
  })

  return [
    at('', UPDATED, 1),
    at('/work', UPDATED, 0.9),
    ...TRADES.map((t) => at(`/websites-for/${t.slug}`, UPDATED, 0.8)),
    at('/guides', UPDATED, 0.6),
    at('/guides/how-much-does-a-tradesman-website-cost', UPDATED, 0.8),
    at('/process', UPDATED, 0.6),
    at('/contact', UPDATED, 0.7),
    at('/refer', UPDATED, 0.4),
    at('/privacy', '2026-09-21', 0.2),
  ]
}
