import { NextResponse } from 'next/server'
import { ownerAlert } from '@/lib/owner-alert'
import { bookingAlert, validSignature, type CalEvent } from '@/lib/cal-booking'

// Cal.com's booking webhook (lib/cal-booking.ts): checked against CAL_WEBHOOK_SECRET, then a Telegram
// alert with "📋 Brief me" for the panel's bot. Nothing is stored here.
export async function POST(request: Request) {
  const secret = process.env.CAL_WEBHOOK_SECRET ?? ''
  if (!secret) return NextResponse.json({ error: 'Not configured' }, { status: 503 })
  const body = await request.text()
  if (body.length > 100_000 || !validSignature(body, request.headers.get('x-cal-signature-256'), secret)) {
    return NextResponse.json({ error: 'Bad signature' }, { status: 401 })
  }
  let event: CalEvent
  try {
    event = JSON.parse(body) as CalEvent
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }
  const alert = bookingAlert(event)
  if (alert) {
    await ownerAlert(alert.text, 'cal-booking', alert.brief ? { inline_keyboard: [[{ text: '📋 Brief me', callback_data: 'brief' }]] } : undefined)
  }
  return NextResponse.json({ ok: true })
}
