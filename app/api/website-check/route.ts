import { NextResponse } from 'next/server'
import { alertText, INBOUND_BUTTONS, parseLead } from '@/lib/website-check'

// "Send me the full report" under the free speed test. Same guards as the contact form: a
// same-origin check, a per-IP limit and a honeypot. A lead is never reported as sent when
// nothing received it.
const RATE_LIMIT = 5
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
  if (origin && origin !== new URL(request.url).origin) {
    return NextResponse.json({ error: 'Invalid request.' }, { status: 403 })
  }
  const ip =
    request.headers.get('x-vercel-forwarded-for')?.split(',')[0]?.trim() ||
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    'unknown'
  if (isRateLimited(ip)) {
    return NextResponse.json({ error: 'Too many requests. Please try again shortly.' }, { status: 429 })
  }
  let body: Record<string, unknown>
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid request.' }, { status: 400 })
  }
  if (body.company) return NextResponse.json({ ok: true }) // honeypot
  const parsed = parseLead(body)
  if ('error' in parsed) return NextResponse.json({ error: parsed.error }, { status: 422 })

  const text = alertText(parsed.lead)
  const token = process.env.TELEGRAM_BOT_TOKEN
  const chatId = process.env.TELEGRAM_CHAT_ID
  if (!token || !chatId) {
    if (process.env.NODE_ENV === 'production') {
      console.error('[website-check] Telegram not set - lead NOT delivered:\n' + text)
      return NextResponse.json({ error: 'Could not send right now. Please try WhatsApp.' }, { status: 503 })
    }
    console.log('[website-check] (Telegram not configured, dev only)\n' + text)
    return NextResponse.json({ ok: true })
  }
  try {
    const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ chat_id: chatId, text, disable_web_page_preview: true, reply_markup: INBOUND_BUTTONS }),
    })
    if (!res.ok) {
      console.error('[website-check] Telegram send failed:', res.status)
      return NextResponse.json({ error: 'Could not send right now. Please try WhatsApp.' }, { status: 502 })
    }
  } catch (error) {
    console.error('[website-check] Telegram request error:', error)
    return NextResponse.json({ error: 'Could not send right now. Please try WhatsApp.' }, { status: 502 })
  }
  return NextResponse.json({ ok: true })
}
