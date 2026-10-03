import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { alertText, normalizeWebsite, parseLead } from './website-check.ts'

const good = { name: 'John Kerr', business: 'Kerr Roofing', email: 'john@kerrroofing.co.uk', phone: '07401 111222', website: 'kerrroofing.co.uk', trade: 'Roofing', town: 'Guildford', score: 34 }

describe('parseLead', () => {
  it('accepts a real request and tidies it', () => {
    const r = parseLead(good)
    assert.ok('lead' in r)
    assert.equal(r.lead.website, 'https://kerrroofing.co.uk')
    assert.equal(r.lead.score, 34)
  })
  it('refuses what it needs and ignores a silly score', () => {
    assert.deepEqual(parseLead({ ...good, email: 'nope' }), { error: 'Please enter a valid email address.' })
    assert.deepEqual(parseLead({ ...good, business: '' }), { error: 'Please enter your business name.' })
    assert.deepEqual(parseLead({ ...good, website: 'localhost' }), { error: "That website address doesn't look right." })
    const r = parseLead({ ...good, score: 900 })
    assert.ok('lead' in r && r.lead.score === null)
  })
  it('keeps every value on one line, so a field can never fake another', () => {
    const r = parseLead({ ...good, business: 'Kerr\nEmail: evil@x.com' })
    assert.ok('lead' in r)
    const lines = alertText(r.lead).split('\n')
    assert.equal(lines.filter((l) => l.startsWith('Email: ')).length, 1)
    assert.ok(lines.includes('Email: john@kerrroofing.co.uk'))
  })
})

describe('normalizeWebsite', () => {
  it('keeps the host and path only', () => {
    assert.equal(normalizeWebsite('https://www.kerr.co.uk/?utm=x'), 'https://www.kerr.co.uk')
    assert.equal(normalizeWebsite('javascript:alert(1)'), null)
  })
})
