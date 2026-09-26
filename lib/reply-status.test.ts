import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { statusFor, ukNow } from './reply-status.ts'

// The contact page tells a visitor, live, when they'll hear back. It has to be
// right at every hour of the week, or it's a broken promise at the last step.

const MON = 1
const SAT = 6
const SUN = 0

describe('statusFor', () => {
  it('is open 7am-7pm Monday to Saturday', () => {
    assert.equal(statusFor({ day: MON, hour: 7 }).open, true)
    assert.equal(statusFor({ day: MON, hour: 18 }).open, true)
    assert.equal(statusFor({ day: SAT, hour: 12 }).open, true)
  })

  it('closes at 7pm sharp', () => {
    assert.deepEqual(statusFor({ day: MON, hour: 19 }), { open: false, next: '7am tomorrow' })
  })

  it('before opening, points at this morning', () => {
    assert.deepEqual(statusFor({ day: MON, hour: 5 }), { open: false, next: '7am today' })
  })

  it('is closed all Sunday, and Sunday points at Monday as "tomorrow"', () => {
    assert.deepEqual(statusFor({ day: SUN, hour: 12 }), { open: false, next: '7am tomorrow' })
    assert.deepEqual(statusFor({ day: SUN, hour: 3 }), { open: false, next: '7am tomorrow' })
  })

  it('Saturday evening skips Sunday', () => {
    assert.deepEqual(statusFor({ day: SAT, hour: 20 }), { open: false, next: '7am Monday' })
  })
})

describe('ukNow', () => {
  it('reads UK wall-clock time, including British Summer Time', () => {
    // 2026-07-15 is a Wednesday; 11:30 UTC is 12:30 BST.
    const n = ukNow(new Date('2026-07-15T11:30:00Z'))
    assert.deepEqual(n, { day: 3, hour: 12, minute: 30, label: '12:30' })
  })

  it('reads GMT in winter', () => {
    // 2026-01-10 is a Saturday; 19:05 UTC is 19:05 GMT.
    const n = ukNow(new Date('2026-01-10T19:05:00Z'))
    assert.deepEqual(n, { day: 6, hour: 19, minute: 5, label: '19:05' })
  })
})
