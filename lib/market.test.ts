import { test } from 'node:test'
import assert from 'node:assert/strict'
import { formatPrice, marketFor, pricesFor, usHosts } from './market.ts'

const HOSTS = usHosts('scalardigital.com, www.scalardigital.com')

test('a preview opened on a US host is the US version', () => {
  assert.equal(marketFor('www.scalardigital.com', undefined, HOSTS), 'us')
  assert.equal(marketFor('Scalardigital.com:443', undefined, HOSTS), 'us')
  assert.equal(marketFor('www.scalardigital.co.uk', undefined, HOSTS), 'uk')
  assert.equal(marketFor(null, undefined, HOSTS), 'uk')
})

test('no US hosts set: everything stays UK, unless ?m=us asks', () => {
  assert.equal(marketFor('scalardigital.com', undefined, []), 'uk')
  assert.equal(marketFor('www.scalardigital.co.uk', 'us', []), 'us')
  assert.equal(marketFor('www.scalardigital.co.uk', 'uk', HOSTS), 'uk')
})

test('prices and how they read in each market', () => {
  assert.deepEqual(pricesFor('us'), { landing: 1500, build: 4500, dashboardMonthly: 59, landingMonthly: 125, buildMonthly: 375 })
  assert.equal(formatPrice('us', pricesFor('us').dashboardMonthly), '$59')
  assert.equal(formatPrice('us', pricesFor('us').build), '$4,500')
  assert.equal(formatPrice('uk', pricesFor('uk').build), '£2,500')
})

test('pay monthly never costs more than paying outright', () => {
  for (const m of ['uk', 'us'] as const) {
    const p = pricesFor(m)
    assert.ok(p.buildMonthly * 12 <= p.build && p.buildMonthly * 12 > p.build - 12)
    assert.ok(p.landingMonthly * 12 <= p.landing && p.landingMonthly * 12 > p.landing - 12)
  }
  assert.equal(pricesFor('uk').buildMonthly, 208)
  assert.equal(pricesFor('uk').landingMonthly, 62)
})
