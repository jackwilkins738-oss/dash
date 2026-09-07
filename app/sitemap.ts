import type { MetadataRoute } from 'next'

const BASE_URL = 'https://www.scalardigital.co.uk'

export default function sitemap(): MetadataRoute.Sitemap {
  const pages = ['', '/work', '/process', '/contact']
  return pages.map((path) => ({
    url: `${BASE_URL}${path}`,
    lastModified: new Date(),
    changeFrequency: 'monthly' as const,
    priority: path === '' ? 1 : 0.8,
  }))
}
