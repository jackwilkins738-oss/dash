import { NextResponse } from 'next/server'
import { isProspectSlug, recordProspectEngagement } from '@/lib/prospect-api'
import { clampEngagement, isBotUserAgent } from '@/lib/engagement'

// How long a prospect looked at their preview and how far they got - sent by
// components/preview-beacon.tsx when the page is put away (sendBeacon, so it
// arrives as text). Numbers are clamped and only known section names kept
// before anything reaches the dashboard; scanners and crawlers are ignored.

const RATE_LIMIT = 30
const WINDOW_MS = 10 * 60 * 1000
const hits = new Map<string, number[]>()

function isRateLimited(ip: string) {
  const now = Date.now()
  const recent = (hits.get(ip) ?? []).filter((t) => now - t < WINDOW_MS)
  recent.push(now)
  hits.set(ip, recent)
  if (hits.size > 5000) hits.clear()
  return recent.length > RATE_LIMIT
}

export async function POST(request: Request) {
  const origin = request.headers.get('origin')
  if (origin && origin !== new URL(request.url).origin) return NextResponse.json({ ok: true })
  if (isBotUserAgent(request.headers.get('user-agent'))) return NextResponse.json({ ok: true })
  const ip =
    request.headers.get('x-vercel-forwarded-for')?.split(',')[0]?.trim() ||
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    'unknown'
  if (isRateLimited(ip)) return NextResponse.json({ ok: true })
  let body: Record<string, unknown>
  try {
    body = JSON.parse(await request.text())
  } catch {
    return NextResponse.json({ ok: true })
  }
  const slug = typeof body.slug === 'string' ? body.slug : ''
  if (!isProspectSlug(slug) || body.src === 'dashboard') return NextResponse.json({ ok: true })
  const e = clampEngagement(body)
  if (e.seconds > 0 || e.reached.length) await recordProspectEngagement(slug, e)
  return NextResponse.json({ ok: true })
}
