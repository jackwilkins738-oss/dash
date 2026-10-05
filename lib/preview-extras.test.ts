import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { reviewsView, rivalsView, stars } from './preview-extras.ts'
import type { Teardown } from './teardown.ts'

const t = (extra: Partial<Teardown>): Teardown => ({ v: 1, checks: {}, ...extra })
const rivals = { query: 'roofer in Guildford', position: 7, items: [{ name: 'Top Roofing', score: 88 }, { name: 'Second', score: 30 }] }

describe('reviewsView', () => {
  it('shows a good rating, with whether their homepage shows reviews', () => {
    assert.deepEqual(reviewsView(t({ google: { rating: 4.8, reviews: 63 }, checks: { showsReviews: false } })), {
      rating: 4.8,
      reviews: 63,
      shownOnSite: false,
    })
    assert.equal(reviewsView(t({ google: { rating: 4.8, reviews: 63 } }))?.shownOnSite, undefined)
  })

  it('leaves out a weak or thin rating, and no rating at all', () => {
    assert.equal(reviewsView(t({ google: { rating: 3.9, reviews: 63 } })), null)
    assert.equal(reviewsView(t({ google: { rating: 5, reviews: 3 } })), null)
    assert.equal(reviewsView(t({})), null)
    assert.equal(reviewsView(null), null)
  })
})

describe('rivalsView', () => {
  it('ranks them among the top firms, fastest first', () => {
    const v = rivalsView(t({ rivals }), 34, 'Kerr Roofing')!
    assert.deepEqual(v.rows, [
      { name: 'Top Roofing', score: 88 },
      { name: 'Kerr Roofing', score: 34, you: true },
      { name: 'Second', score: 30 },
    ])
    assert.equal(v.ahead, 1)
    assert.equal(v.position, 7)
  })

  it('says nothing when they are quickest, or there is no score', () => {
    assert.equal(rivalsView(t({ rivals }), 90, 'Kerr'), null)
    assert.equal(rivalsView(t({ rivals }), null, 'Kerr'), null)
    assert.equal(rivalsView(t({}), 34, 'Kerr'), null)
  })

  it('a tie puts them below the rival', () => {
    const v = rivalsView(t({ rivals: { ...rivals, items: [{ name: 'A', score: 50 }, { name: 'B', score: 60 }] } }), 50, 'Kerr')!
    assert.deepEqual(v.rows.map((r) => r.name), ['B', 'A', 'Kerr'])
  })
})

describe('stars', () => {
  it('rounds to whole stars', () => {
    assert.equal(stars(4.8), '★★★★★')
    assert.equal(stars(4.2), '★★★★☆')
  })
})
