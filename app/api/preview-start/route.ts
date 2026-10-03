import { NextResponse } from 'next/server'
import { isProspectSlug, startProspectQuote } from '@/lib/prospect-api'
import { ownerAlert } from '@/lib/owner-alert'
import { startAlert } from '@/lib/checkout'

// "See my quote" on a prospect's preview: their quote (made from the package the owner published),
// and the owner told at once. Anything wrong - not published yet, dashboard down - answers
// { url: null } and the page falls back to the contact form, so a keen prospect is never stuck.
const RATE_LIMIT = 6
const WINDOW_MS = 10 * 60 * 1000
const hits = new Map<string, number[]>()

function isRateLimited(ip: string) {
  const now = Date.now()
  const recent = (hits.get(ip) ?? []).filter((t) => now - t < WINDOW_MS)
  recent.push(now)
  hits.set(ip, recent)
  if (hits.size > 5000) {
    for (const [key, times] of hits) if (times.every((t) => now - t > WINDOW_MS)) hits.delete(key)
  }
  return recent.length > RATE_LIMIT
}

export async function POST(request: Request) {
  const origin = request.headers.get('origin')
  if (origin && origin !== new URL(request.url).origin) return NextResponse.json({ url: null }, { status: 403 })
  const ip =
    request.headers.get('x-vercel-forwarded-for')?.split(',')[0]?.trim() ||
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    'unknown'
  if (isRateLimited(ip)) return NextResponse.json({ url: null }, { status: 429 })
  let body: { slug?: unknown; package?: unknown }
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ url: null }, { status: 400 })
  }
  const slug = typeof body.slug === 'string' ? body.slug : ''
  const pkg = body.package === 'build' || body.package === 'landing' ? body.package : null
  if (!isProspectSlug(slug) || !pkg) return NextResponse.json({ url: null }, { status: 400 })

  const quote = await startProspectQuote(slug, pkg)
  if (!quote) return NextResponse.json({ url: null })
  await ownerAlert(startAlert(quote, pkg), 'preview-start')
  return NextResponse.json({ url: quote.quote_url })
}
