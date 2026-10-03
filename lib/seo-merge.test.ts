import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { applySeo, laterDate, mergeFaqs } from './seo-merge.ts'

describe('applySeo', () => {
  const base = { title: 'Old', description: 'Old desc', alternates: { canonical: '/x' }, openGraph: { title: 'OG', description: 'Old desc', url: '/x' } }

  it('leaves a page alone with no entry', () => {
    assert.deepEqual(applySeo(base, undefined, 'Brand'), base)
  })

  it('sets the full title, description and the share description', () => {
    const out = applySeo(base, { title: ' New title ', description: 'New desc' }, 'Brand')
    assert.deepEqual(out.title, { absolute: 'New title | Brand' })
    assert.equal(out.description, 'New desc')
    assert.deepEqual(out.openGraph, { title: 'OG', description: 'New desc', url: '/x' })
    assert.deepEqual(out.alternates, { canonical: '/x' })
  })

  it('ignores blank fields and adds no openGraph a page never had', () => {
    const out = applySeo({ title: 'Old' }, { title: '', description: 'D' }, 'Brand')
    assert.equal(out.title, 'Old')
    assert.equal(out.description, 'D')
    assert.equal(out.openGraph, undefined)
  })
})

describe('mergeFaqs', () => {
  const own = [{ q: 'How much does it cost?', a: 'From £750.' }]

  it('adds new questions after the page’s own', () => {
    assert.deepEqual(mergeFaqs(own, [{ q: 'Do I own it?', a: 'Yes.' }]).map((i) => i.q), ['How much does it cost?', 'Do I own it?'])
  })

  it('skips repeats (case and punctuation aside) and empty ones', () => {
    const extra = [{ q: 'how much does it cost', a: 'x' }, { q: 'Empty?', a: ' ' }, { q: 'New?', a: 'A' }, { q: 'new', a: 'B' }]
    assert.deepEqual(mergeFaqs(own, extra).map((i) => i.q), ['How much does it cost?', 'New?'])
  })

  it('copes with no extras', () => {
    assert.deepEqual(mergeFaqs(own, undefined), own)
  })
})

describe('laterDate', () => {
  it('takes the loop’s date only when it is a later real date', () => {
    assert.equal(laterDate('2026-09-24', '2026-11-01'), '2026-11-01')
    assert.equal(laterDate('2026-09-24', '2026-01-01'), '2026-09-24')
    assert.equal(laterDate('2026-09-24', 'soon'), '2026-09-24')
    assert.equal(laterDate('2026-09-24', undefined), '2026-09-24')
  })
})
