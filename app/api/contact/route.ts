import { NextResponse } from 'next/server'

type ContactPayload = {
  name?: string
  email?: string
  phone?: string
  trade?: string
  budget?: string
  message?: string
  // Honeypot — real users never fill this
  company?: string
}

function isEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
}

export async function POST(request: Request) {
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

  const name = (body.name ?? '').trim()
  const email = (body.email ?? '').trim()
  const message = (body.message ?? '').trim()

  if (name.length < 2) {
    return NextResponse.json({ error: 'Please enter your name.' }, { status: 422 })
  }
  if (!isEmail(email)) {
    return NextResponse.json({ error: 'Please enter a valid email address.' }, { status: 422 })
  }
  if (message.length < 5) {
    return NextResponse.json({ error: 'Tell me a little about the job.' }, { status: 422 })
  }

  const lines = [
    'New enquiry — Scalar Digital',
    '',
    `Name: ${name}`,
    `Email: ${email}`,
    body.phone ? `Phone: ${body.phone.trim()}` : null,
    body.trade ? `Trade: ${body.trade.trim()}` : null,
    body.budget ? `Budget: ${body.budget.trim()}` : null,
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
        console.error('[v0] Telegram send failed:', res.status, await res.text())
        return NextResponse.json({ error: 'Could not send right now. Please try WhatsApp.' }, { status: 502 })
      }
    } catch (error) {
      console.error('[v0] Telegram request error:', error)
      return NextResponse.json({ error: 'Could not send right now. Please try WhatsApp.' }, { status: 502 })
    }
  } else {
    // No Telegram configured yet — log so the enquiry is never lost during setup.
    console.log('[v0] Contact enquiry (Telegram not configured):\n' + lines)
  }

  return NextResponse.json({ ok: true })
}
