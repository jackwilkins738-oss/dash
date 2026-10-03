import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { startAlert } from './checkout.ts'

describe('startAlert', () => {
  it('says who, which package and the total', () => {
    const t = startAlert({ business_name: 'Kerr Roofing', quote_number: 'SD-0012', total_pence: 250000, reused: false }, 'build')
    assert.match(t, /Kerr Roofing asked for their quote from their preview: The Scalar build, SD-0012, £2,500 total/)
    assert.doesNotMatch(t, /⚠️/)
  })
  it('warns when the quote price differs from the preview page', () => {
    const t = startAlert({ business_name: 'Kerr Roofing', quote_number: 'SD-0012', total_pence: 300000, reused: false }, 'build')
    assert.match(t, /preview page shows £2,500 but the quote is £3,000/)
  })
  it('a reopened quote is a short note', () => {
    const t = startAlert({ business_name: 'Kerr Roofing', quote_number: 'SD-0012', total_pence: 300000, reused: true }, 'build')
    assert.match(t, /reopened their quote \(SD-0012\)/)
    assert.doesNotMatch(t, /⚠️/)
  })
})
