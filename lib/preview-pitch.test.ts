import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { heroPitch, reportTiles } from './preview-pitch.ts'

const base = { business: 'JBL Roofing', site: 'jblroofing.co.uk', score: 42, lcp: 6.2, rivalsAhead: 0, findings: 3 }

describe('heroPitch', () => {
  it('leads with rivals, then slowness, then findings', () => {
    assert.equal(heroPitch({ ...base, rivalsAhead: 3 }).title, '3 rivals near the top of Google Maps load faster than JBL Roofing.')
    assert.equal(heroPitch({ ...base, rivalsAhead: 1 }).title, 'A rival near the top of Google Maps loads faster than JBL Roofing.')
    assert.equal(heroPitch(base).title, 'jblroofing.co.uk takes 6.2s to show on a phone.')
    assert.equal(heroPitch({ ...base, lcp: 3.1 }).title, '3 things on jblroofing.co.uk could be losing you enquiries.')
    assert.equal(heroPitch({ ...base, lcp: null, findings: 1 }).title, 'One thing on jblroofing.co.uk could be losing you enquiries.')
  })

  it('falls back to the plain headline with nothing measured', () => {
    const p = heroPitch({ ...base, score: null, lcp: null, findings: 0 })
    assert.equal(p.kind, 'plain')
    assert.equal(p.title, 'A sharper website for JBL Roofing.')
  })
})

describe('reportTiles', () => {
  it('colours by Google’s bands and caps at four', () => {
    const tiles = reportTiles({ score: 42, lcp: 6.2, findings: 3, mapsPosition: 5, mapsQuery: 'roofer woking' })
    assert.deepEqual(tiles.map((t) => [t.value, t.tone]), [['42/100', 'bad'], ['6.2s', 'bad'], ['3', 'bad'], ['#5', 'warn']])
    assert.deepEqual(reportTiles({ score: 95, lcp: 1.8, findings: 0 }).map((t) => t.tone), ['ok', 'ok'])
    assert.deepEqual(reportTiles({ score: null, lcp: null, findings: 0 }), [])
  })
})
