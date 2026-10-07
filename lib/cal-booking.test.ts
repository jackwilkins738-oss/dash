import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { createHmac } from 'node:crypto'
import { bookingAlert, validSignature } from './cal-booking.ts'

const event = (triggerEvent: string, extra: Record<string, unknown> = {}) => ({
  triggerEvent,
  payload: { startTime: '2026-10-14T09:30:00Z', attendees: [{ name: 'Sam Kerr', email: 'sam@kerr.co.uk' }], ...extra },
})

describe('validSignature', () => {
  it('accepts only the body signed with the secret', () => {
    const body = '{"a":1}'
    const sig = createHmac('sha256', 's3cret').update(body).digest('hex')
    assert.equal(validSignature(body, sig, 's3cret'), true)
    assert.equal(validSignature(body + ' ', sig, 's3cret'), false)
    assert.equal(validSignature(body, sig, ''), false)
    assert.equal(validSignature(body, null, 's3cret'), false)
  })
})

describe('bookingAlert', () => {
  it('a new booking: who, when in UK time, and the lines the bot reads', () => {
    const a = bookingAlert(event('BOOKING_CREATED', { additionalNotes: 'Roof\nquote' }))
    assert.equal(a?.brief, true)
    assert.match(a!.text, /📅 Call booked: Sam Kerr\nWhen: Wed 14 Oct, 10:30 \(UK\)\nEmail: sam@kerr.co.uk\nStart: 2026-10-14T09:30:00Z\nNotes: Roof quote/)
  })
  it('moved and cancelled', () => {
    assert.match(bookingAlert(event('BOOKING_RESCHEDULED'))!.text, /^🔁 Call moved/)
    const c = bookingAlert(event('BOOKING_CANCELLED'))
    assert.equal(c?.brief, false)
    assert.match(c!.text, /^❌ Call cancelled: Sam Kerr/)
  })
  it('ignores anything else or incomplete', () => {
    assert.equal(bookingAlert(event('MEETING_ENDED')), null)
    assert.equal(bookingAlert({ triggerEvent: 'BOOKING_CREATED', payload: { attendees: [] } }), null)
  })
})
