import { NextResponse } from 'next/server'
import { isProspectSlug, recordProspectView } from '@/lib/prospect-api'

// "A prospect just opened their preview page." Called once per browser
// session by components/preview-beacon.tsx. Records the visit in the
// dashboard (count, dates, status new -> viewed) and pings the owner on
// Telegram - the same bot the contact form uses - so the call can happen
// while they're still looking.
//
// Only a slug and a source label come in; everything in the alert comes
// back from the dashboard's own record, never from the request, so nobody
// can make the bot say something of their choosing.

const ALERT_COOLDOWN_MS = 30 * 60 * 1000
const lastAlert = new Map<string, number>()

const RATE_LIMIT = 20
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

// Where the visit came from, from the preview link's ?src= - one of a known
// few, so an alert can say "from the letter" without echoing free text.
const SOURCES: Record<string, string> = {
  email: 'the email',
  letter: 'the letter (QR code)',
  qr: 'the letter (QR code)',
  whatsapp: 'WhatsApp',
  linkedin: 'LinkedIn',
  call: 'the phone call',
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

  let body: { slug?: unknown; src?: unknown }
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid request.' }, { status: 400 })
  }
  const slug = typeof body.slug === 'string' ? body.slug : ''
  const src = typeof body.src === 'string' ? body.src.toLowerCase() : ''
  if (!isProspectSlug(slug)) return NextResponse.json({ ok: true })

  // The owner opening it from the dashboard's own "Open their preview"
  // link isn't the prospect looking - don't count it or alert on it.
  if (src === 'dashboard') return NextResponse.json({ ok: true })

  const prospect = await recordProspectView(slug)
  if (!prospect) return NextResponse.json({ ok: true })

  const now = Date.now()
  if (now - (lastAlert.get(slug) ?? 0) < ALERT_COOLDOWN_MS) return NextResponse.json({ ok: true })
  lastAlert.set(slug, now)
  if (lastAlert.size > 2000) lastAlert.clear()

  const token = process.env.TELEGRAM_BOT_TOKEN
  const chatId = process.env.TELEGRAM_CHAT_ID
  const visit = prospect.view_count > 1 ? ` (visit ${prospect.view_count})` : ''
  const text = [
    `${prospect.business_name} just opened their preview page${visit}.`,
    [prospect.trade, prospect.area].filter(Boolean).join(', ') || null,
    SOURCES[src] ? `Came from ${SOURCES[src]}.` : null,
    prospect.website
      ? `Their site: ${prospect.website}${prospect.mobile_score != null ? ` (${prospect.mobile_score}/100 on mobile)` : ''}`
      : null,
    '',
    'Worth a call while it is fresh - check the number against TPS/CTPS first.',
  ]
    .filter((l) => l !== null)
    .join('\n')

  if (token && chatId) {
    try {
      await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: chatId, text, disable_web_page_preview: true }),
      })
    } catch (error) {
      console.error('[preview-view] Telegram request error:', error)
    }
  } else {
    console.log('[preview-view] (Telegram not configured)\n' + text)
  }

  return NextResponse.json({ ok: true })
}
