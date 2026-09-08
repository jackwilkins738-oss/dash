import type { MetadataRoute } from 'next'

const BASE_URL = 'https://www.scalardigital.co.uk'

export default function sitemap(): MetadataRoute.Sitemap {
  const pages = ['', '/work', '/process', '/contact']
  const entries: MetadataRoute.Sitemap = pages.map((path) => ({
    url: `${BASE_URL}${path}`,
    lastModified: new Date(),
    changeFrequency: 'monthly' as const,
    priority: path === '' ? 1 : 0.8,
  }))
  entries.push({ url: `${BASE_URL}/privacy`, lastModified: new Date(), changeFrequency: 'yearly' as const, priority: 0.3 })
  return entries
}
