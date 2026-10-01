import { NextResponse } from 'next/server'
import { isProspectSlug, recordProspectOptOut } from '@/lib/prospect-api'

// "Not for us" on a prospect's preview page (components/preview-optout.tsx).
// The dashboard marks them lost, which the owner's panel treats as
// do-not-contact - out of every batch, follow-up and call list - and the
// owner gets a one-line Telegram note. Only the slug comes in; the name in
// the alert comes back from the dashboard's record, never from the request.

const RATE_LIMIT = 10
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
  if (origin && origin !== new URL(request.url).origin) {
    return NextResponse.json({ error: 'Invalid request.' }, { status: 403 })
  }
  const ip =
    request.headers.get('x-vercel-forwarded-for')?.split(',')[0]?.trim() ||
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    'unknown'
  if (isRateLimited(ip)) return NextResponse.json({ ok: true })

  let body: { slug?: unknown }
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid request.' }, { status: 400 })
  }
  const slug = typeof body.slug === 'string' ? body.slug : ''
  if (!isProspectSlug(slug)) return NextResponse.json({ ok: true })

  const name = await recordProspectOptOut(slug)
  const token = process.env.TELEGRAM_BOT_TOKEN
  const chatId = process.env.TELEGRAM_CHAT_ID
  if (name && token && chatId) {
    try {
      await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          chat_id: chatId,
          text: `${name} pressed "not for us" on their preview. They're marked lost and won't be emailed again.`,
        }),
      })
    } catch (error) {
      console.error('[preview-optout] Telegram request error:', error)
    }
  }
  // Always the same answer, whatever happened, so the page can't be used to probe slugs.
  return NextResponse.json({ ok: true })
}
