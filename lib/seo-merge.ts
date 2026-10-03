// The monthly SEO loop (scripts/seo_loop.py) writes content/seo.json: a better title, description
// and extra FAQs for pages Search Console says are close to page one. These are the pure rules for
// laying that over a page's own metadata, kept apart from the JSON so they can be tested.
import type { Metadata } from 'next'

export type SeoQA = { q: string; a: string }
export type SeoEntry = { title?: string; description?: string; faqs?: SeoQA[]; changed?: string }

// The title is set in full (not through the layout's "%s | Scalar Digital" template) so the length
// the loop checks is the length Google sees.
export function applySeo(metadata: Metadata, entry: SeoEntry | undefined, brand: string): Metadata {
  if (!entry) return metadata
  const out: Metadata = { ...metadata }
  const title = entry.title?.trim()
  const description = entry.description?.trim()
  if (title) out.title = { absolute: `${title} | ${brand}` }
  if (description) out.description = description
  if (description && metadata.openGraph) out.openGraph = { ...metadata.openGraph, description }
  return out
}

// A page's own questions first; the loop's are added after, never repeating one already there.
export function mergeFaqs<T extends SeoQA>(items: T[], extra: SeoQA[] | undefined): SeoQA[] {
  const seen = new Set(items.map((i) => norm(i.q)))
  const added = (extra ?? []).filter((e) => e.q?.trim() && e.a?.trim() && !seen.has(norm(e.q)) && seen.add(norm(e.q)))
  return [...items, ...added]
}

// The sitemap's lastmod: the later of the page's own date and the loop's last change to it.
export function laterDate(base: string, changed: string | undefined): string {
  return changed && /^\d{4}-\d{2}-\d{2}$/.test(changed) && changed > base ? changed : base
}

function norm(q: string): string {
  return q.toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim()
}
