import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { callNowButtons } from './owner-alert.ts'

describe('callNowButtons', () => {
  it('carries the slug for the panel bot', () => {
    assert.equal(callNowButtons('kerr-roofing-d50846')?.inline_keyboard[0][0].callback_data, 'callnow:kerr-roofing-d50846')
  })
  it('leaves the button off when Telegram would refuse it (64 bytes)', () => {
    assert.equal(callNowButtons('a'.repeat(60)), undefined)
  })
})
