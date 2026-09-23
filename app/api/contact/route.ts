import { NextResponse } from 'next/server'

// In-memory sliding-window limit - good enough for a single-instance
// marketing site's contact form; resets on redeploy/restart.
const RATE_LIMIT = 5
const WINDOW_MS = 10 * 60 * 1000
const hits = new Map<string, number[]>()

function isRateLimited(ip: string) {
  const now = Date.now()
  const recent = (hits.get(ip) ?? []).filter((t) => now - t < WINDOW_MS)
  recent.push(now)
  hits.set(ip, recent)
  if (hits.size > 5000) {
    for (const [key, times] of hits) {
      if (times.every((t) => now - t > WINDOW_MS)) hits.delete(key)
    }
  }
  return recent.length > RATE_LIMIT
}

type ContactPayload = {
  name?: string
  email?: string
  phone?: string
  trade?: string
  budget?: string
  projectType?: string
  message?: string
  // Honeypot — real users never fill this
  company?: string
  // Set when they arrive through a referral link
  referredBy?: string
}

function isEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
}

export async function POST(request: Request) {
  // Cross-site fetch() calls always send an Origin header, even ones using
  // text/plain to dodge CORS preflight; same-origin browser submissions and
  // legitimate non-browser clients may omit it. Reject only a mismatch, not
  // an absence - that's the standard stateless CSRF check for a route with
  // no session/cookie to protect otherwise.
  const origin = request.headers.get('origin')
  if (origin && origin !== new URL(request.url).origin) {
    return NextResponse.json({ error: 'Invalid request.' }, { status: 403 })
  }

  // x-vercel-forwarded-for is the header Vercel's own edge sets and trusts;
  // x-forwarded-for is kept only as a fallback for non-Vercel environments.
  const ip =
    request.headers.get('x-vercel-forwarded-for')?.split(',')[0]?.trim() ||
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    'unknown'
  if (isRateLimited(ip)) {
    return NextResponse.json({ error: 'Too many requests. Please try again shortly.' }, { status: 429 })
  }

  let body: ContactPayload
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid request.' }, { status: 400 })
  }

  // Spam honeypot: silently accept and drop
  if (body.company) {
    return NextResponse.json({ ok: true })
  }

  const name = (body.name ?? '').trim().slice(0, 100)
  const email = (body.email ?? '').trim().slice(0, 254)
  const message = (body.message ?? '').trim().slice(0, 4000)
  const phone = (body.phone ?? '').trim().slice(0, 30)
  const trade = (body.trade ?? '').trim().slice(0, 60)
  const projectType = (body.projectType ?? '').trim().slice(0, 60)
  const budget = (body.budget ?? '').trim().slice(0, 60)

  if (name.length < 2) {
    return NextResponse.json({ error: 'Please enter your name.' }, { status: 422 })
  }
  if (!isEmail(email)) {
    return NextResponse.json({ error: 'Please enter a valid email address.' }, { status: 422 })
  }
  if (message.length < 5) {
    return NextResponse.json({ error: 'Tell me a little about the job.' }, { status: 422 })
  }

  // Only letters, numbers, spaces and a few name marks; never trust the link.
  const referredBy = (body.referredBy ?? '')
    .replace(/[^\p{L}\p{N} .'&-]/gu, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 60)

  const lines = [
    'New enquiry — Scalar Digital',
    referredBy ? `REFERRAL: referred by ${referredBy} (15% off their build - check with them, 10% off theirs later)` : null,
    '',
    `Name: ${name}`,
    `Email: ${email}`,
    phone ? `Phone: ${phone}` : null,
    trade ? `Trade: ${trade}` : null,
    projectType ? `Project type: ${projectType}` : null,
    budget ? `Budget: ${budget}` : null,
    '',
    'Message:',
    message,
  ]
    .filter(Boolean)
    .join('\n')

  // Telegram Worker integration.
  // Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to forward enquiries to Telegram.
  const token = process.env.TELEGRAM_BOT_TOKEN
  const chatId = process.env.TELEGRAM_CHAT_ID

  if (token && chatId) {
    try {
      const res = await fetch(`https://api.telegram.org/bot${token}/sendMessage`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ chat_id: chatId, text: lines, disable_web_page_preview: true }),
      })
      if (!res.ok) {
        console.error('[contact] Telegram send failed:', res.status, await res.text())
        return NextResponse.json({ error: 'Could not send right now. Please try WhatsApp.' }, { status: 502 })
      }
    } catch (error) {
      console.error('[contact] Telegram request error:', error)
      return NextResponse.json({ error: 'Could not send right now. Please try WhatsApp.' }, { status: 502 })
    }
  } else if (process.env.NODE_ENV === 'production') {
    // Never tell a visitor their enquiry was sent when nothing is there to
    // receive it: fail loudly (and log the message so it isn't lost).
    // This does put the visitor's name/email/phone/message into server logs
    // - a deliberate, reviewed trade-off: Vercel logs are private to this
    // account, and losing a real lead outright is worse than that. Revisit
    // if a log drain to a less-trusted third party is ever added.
    console.error('[contact] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set - enquiry NOT delivered:\n' + lines)
    return NextResponse.json({ error: 'Could not send right now. Please try WhatsApp.' }, { status: 503 })
  } else {
    // Local development: no bot configured, just log the enquiry.
    console.log('[contact] Enquiry (Telegram not configured, dev only):\n' + lines)
  }

  return NextResponse.json({ ok: true })
}
