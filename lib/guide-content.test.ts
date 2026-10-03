import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { byNewest, isGuide, pieces, plain } from './guide-content.ts'

describe('pieces', () => {
  it('turns site links and bold into pieces', () => {
    assert.deepEqual(pieces('See [our prices](/work#pricing) and **ask first**.'), [
      { text: 'See ' },
      { text: 'our prices', href: '/work#pricing' },
      { text: ' and ' },
      { text: 'ask first', bold: true },
      { text: '.' },
    ])
  })

  it('leaves outside links as plain text', () => {
    assert.deepEqual(pieces('Go to [Google](https://google.com) now'), [{ text: 'Go to [Google](https://google.com) now' }])
  })

  it('plain drops the markup', () => {
    assert.equal(plain('A [link](/guides) and **bold**'), 'A link and bold')
  })
})

describe('isGuide', () => {
  const g = { slug: 'a-guide', title: 'T', metaTitle: 'M', description: 'D', summary: 'S', card: 'C', published: '2026-10-03', sections: [{ heading: 'H', paragraphs: ['p'] }], faqs: [] }

  it('accepts a whole guide and rejects a broken one', () => {
    assert.equal(isGuide(g), true)
    assert.equal(isGuide({ ...g, slug: 'Bad Slug' }), false)
    assert.equal(isGuide({ ...g, published: 'soon' }), false)
    assert.equal(isGuide({ ...g, sections: 'x' }), false)
  })

  it('sorts newest first', () => {
    assert.deepEqual(byNewest([{ ...g, slug: 'old', published: '2026-01-01' }, g]).map((x) => x.slug), ['a-guide', 'old'])
  })
})
