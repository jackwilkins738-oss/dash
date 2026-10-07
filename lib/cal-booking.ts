// Cal.com bookings, told to the owner on Telegram with a "📋 Brief me" button. The panel's bot on the
// owner's PC answers it - it alone has the firm's phone, preview, score and history - and sends the
// brief again 15 minutes before the call. The website keeps nothing.
//
// Cal.com -> Settings -> Developer -> Webhooks: URL https://www.scalardigital.co.uk/api/cal-booking,
// events Booking created / rescheduled / cancelled, and a secret - the same value as CAL_WEBHOOK_SECRET
// in Vercel. Cal.com signs each delivery (x-cal-signature-256: HMAC-SHA256 of the body, hex).
import { createHmac, timingSafeEqual } from 'node:crypto'

export function validSignature(body: string, signature: string | null, secret: string): boolean {
  if (!signature || !secret) return false
  const expected = createHmac('sha256', secret).update(body).digest('hex')
  const a = Buffer.from(expected)
  const b = Buffer.from(signature.trim().toLowerCase())
  return a.length === b.length && timingSafeEqual(a, b)
}

type Attendee = { name?: unknown; email?: unknown }
export type CalEvent = {
  triggerEvent?: unknown
  payload?: { startTime?: unknown; attendees?: Attendee[]; additionalNotes?: unknown; title?: unknown }
}

const clean = (v: unknown, max: number) => (typeof v === 'string' ? v.replace(/[\r\n]+/g, ' ').trim().slice(0, max) : '')

// The alert's text - its "Email:" and "Start:" lines are what the panel's bot reads back.
export function bookingAlert(event: CalEvent): { text: string; brief: boolean } | null {
  const kind = event.triggerEvent
  const p = event.payload ?? {}
  const who = (p.attendees ?? [])[0] ?? {}
  const email = clean(who.email, 120)
  const start = clean(p.startTime, 40)
  const when = Number.isNaN(Date.parse(start))
    ? ''
    : new Intl.DateTimeFormat('en-GB', {
        weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'Europe/London',
      }).format(new Date(start))
  if (!email || !when) return null
  const name = clean(who.name, 80) || email
  const notes = clean(p.additionalNotes, 300)
  if (kind === 'BOOKING_CANCELLED') return { text: `❌ Call cancelled: ${name} (${when})\nEmail: ${email}`, brief: false }
  if (kind !== 'BOOKING_CREATED' && kind !== 'BOOKING_RESCHEDULED') return null
  const head = kind === 'BOOKING_RESCHEDULED' ? '🔁 Call moved' : '📅 Call booked'
  return {
    text: `${head}: ${name}\nWhen: ${when} (UK)\nEmail: ${email}\nStart: ${start}${notes ? `\nNotes: ${notes}` : ''}`,
    brief: true,
  }
}
