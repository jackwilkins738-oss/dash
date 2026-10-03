// Guides the monthly SEO loop drafts (scripts/seo_loop.py) live as JSON in content/guides/ and are
// rendered by app/guides/[slug]. These are the pure parts: the shape, and turning a paragraph's
// [link text](/path) and **bold** into pieces the page can render.

export type GuideSection = { heading: string; paragraphs: string[]; bullets?: { lead: string; text: string }[] }
export type Guide = {
  slug: string
  title: string // the page's H1 and Article headline
  metaTitle: string // what Google shows, before " | Scalar Digital"
  description: string
  summary: string // "The short answer" box
  sections: GuideSection[]
  faqs: { q: string; a: string }[]
  published: string // YYYY-MM-DD
  card: string // one line for the guides index
}

export type Piece = { text: string; href?: string; bold?: boolean }

// Only site-relative links (/work, /guides/x) become links; anything else stays plain text.
export function pieces(text: string): Piece[] {
  const out: Piece[] = []
  const re = /\[([^\]]+)\]\((\/[a-z0-9\-/#]*)\)|\*\*([^*]+)\*\*/g
  let last = 0
  for (let m = re.exec(text); m; m = re.exec(text)) {
    if (m.index > last) out.push({ text: text.slice(last, m.index) })
    out.push(m[1] !== undefined ? { text: m[1], href: m[2] } : { text: m[3], bold: true })
    last = re.lastIndex
  }
  if (last < text.length) out.push({ text: text.slice(last) })
  return out
}

// Plain text for structured data and descriptions.
export function plain(text: string): string {
  return pieces(text)
    .map((p) => p.text)
    .join('')
}

export function isGuide(g: unknown): g is Guide {
  const x = g as Guide
  return (
    !!x &&
    typeof x.slug === 'string' &&
    /^[a-z0-9]+(-[a-z0-9]+)*$/.test(x.slug) &&
    typeof x.title === 'string' &&
    typeof x.metaTitle === 'string' &&
    typeof x.description === 'string' &&
    typeof x.summary === 'string' &&
    typeof x.card === 'string' &&
    /^\d{4}-\d{2}-\d{2}$/.test(x.published ?? '') &&
    Array.isArray(x.sections) &&
    x.sections.every((s) => typeof s.heading === 'string' && Array.isArray(s.paragraphs)) &&
    Array.isArray(x.faqs)
  )
}

// Newest first, for the index.
export function byNewest(guides: Guide[]): Guide[] {
  return [...guides].sort((a, b) => (a.published < b.published ? 1 : a.published > b.published ? -1 : a.slug.localeCompare(b.slug)))
}
