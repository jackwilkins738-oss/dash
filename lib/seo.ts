import type { Metadata } from 'next'
import seo from '@/content/seo.json'
import { SITE } from '@/lib/site'
import { applySeo, laterDate, mergeFaqs, type SeoEntry, type SeoQA } from '@/lib/seo-merge'

const ENTRIES = seo as Record<string, SeoEntry>

// A page's metadata with this month's Search Console fixes laid over it (see scripts/seo_loop.py).
export function withSeo(path: string, metadata: Metadata): Metadata {
  return applySeo(metadata, ENTRIES[path], SITE.name)
}

export function withMoreFaqs<T extends SeoQA>(path: string | undefined, items: T[]): SeoQA[] {
  return path ? mergeFaqs(items, ENTRIES[path]?.faqs) : items
}

export function lastmod(path: string, base: string): string {
  return laterDate(base, ENTRIES[path]?.changed)
}
