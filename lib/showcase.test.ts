import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  SHOWCASE_CYCLE_MS,
  SHOWCASE_TRADES,
  nextShowcaseIndex,
  showcaseIdForTradeText,
  showcaseIndexForTrade,
} from './showcase.ts'

describe('SHOWCASE_TRADES', () => {
  it('has more than one trade, or there is nothing to switch between', () => {
    assert.ok(SHOWCASE_TRADES.length > 1)
  })

  it('uses unique ids and tab labels', () => {
    const ids = SHOWCASE_TRADES.map((t) => t.id)
    const tabs = SHOWCASE_TRADES.map((t) => t.tab)
    assert.equal(new Set(ids).size, ids.length)
    assert.equal(new Set(tabs).size, tabs.length)
  })

  it('gives every trade all of its copy', () => {
    for (const t of SHOWCASE_TRADES) {
      for (const key of ['tab', 'descriptor', 'eyebrow', 'headline', 'sub', 'cta', 'enquiry'] as const) {
        assert.ok(t[key].trim().length > 0, `${t.id}: ${key} is empty`)
      }
      assert.equal(t.tiles.length, 3, `${t.id}: needs exactly three work tiles`)
      for (const tile of t.tiles) assert.ok(tile.trim().length > 0, `${t.id}: empty tile label`)
    }
  })

  it('gives each trade its own accent and its own artwork', () => {
    // The switcher's job is to show the site re-theming itself. Two trades
    // with the same colour or the same scene would make a tab look broken.
    const accents = SHOWCASE_TRADES.map((t) => t.accent)
    const arts = SHOWCASE_TRADES.map((t) => t.art)
    assert.equal(new Set(accents).size, accents.length)
    assert.equal(new Set(arts).size, arts.length)
  })

  it('defines both colours as oklch, which the stylesheet transitions between', () => {
    for (const t of SHOWCASE_TRADES) {
      assert.match(t.accent, /^oklch\(/, `${t.id}: accent`)
      assert.match(t.accentUi, /^oklch\(/, `${t.id}: accentUi`)
    }
  })

  it('keeps the placeholder generic: no figures or superlatives that read as claims', () => {
    // The preview is an illustration of a site, not a testimonial. lib/trades.ts
    // holds the same rule: nothing here may claim a result, client or credential.
    const banned = /\d+\s*(\+|%|years|reviews|jobs|customers|clients)|\b(best|no\.?\s*1|award|rated|guaranteed)\b/i
    for (const t of SHOWCASE_TRADES) {
      for (const text of [t.headline, t.sub, t.cta, t.eyebrow, t.enquiry, ...t.tiles]) {
        assert.doesNotMatch(text, banned, `${t.id}: "${text}" reads as a claim`)
      }
    }
  })
})

describe('nextShowcaseIndex', () => {
  it('moves to the next trade', () => {
    assert.equal(nextShowcaseIndex(0, 4), 1)
    assert.equal(nextShowcaseIndex(2, 4), 3)
  })

  it('wraps from the last back to the first', () => {
    assert.equal(nextShowcaseIndex(3, 4), 0)
  })

  it('defaults to the real number of trades', () => {
    assert.equal(nextShowcaseIndex(SHOWCASE_TRADES.length - 1), 0)
  })

  it('stays at zero if there is nothing to rotate through', () => {
    assert.equal(nextShowcaseIndex(0, 0), 0)
  })

  it('visits every trade exactly once in a full lap', () => {
    const seen = new Set<number>()
    let i = 0
    for (let n = 0; n < SHOWCASE_TRADES.length; n++) {
      seen.add(i)
      i = nextShowcaseIndex(i)
    }
    assert.equal(seen.size, SHOWCASE_TRADES.length)
    assert.equal(i, 0)
  })
})

describe('SHOWCASE_CYCLE_MS', () => {
  it('is long enough to read a headline and short enough to keep moving', () => {
    assert.ok(SHOWCASE_CYCLE_MS >= 3000)
    assert.ok(SHOWCASE_CYCLE_MS <= 10000)
  })
})

describe('showcaseIndexForTrade', () => {
  it('matches a /websites-for/ page slug to its preview trade', () => {
    assert.equal(showcaseIndexForTrade('roofers'), SHOWCASE_TRADES.findIndex((t) => t.id === 'roofing'))
    assert.equal(
      showcaseIndexForTrade('loft-conversion-companies'),
      SHOWCASE_TRADES.findIndex((t) => t.id === 'lofts'),
    )
    assert.equal(
      showcaseIndexForTrade('driveway-installers'),
      SHOWCASE_TRADES.findIndex((t) => t.id === 'driveways'),
    )
    assert.equal(
      showcaseIndexForTrade('landscapers'),
      SHOWCASE_TRADES.findIndex((t) => t.id === 'landscaping'),
    )
  })

  it('maps the one trade with no dedicated scene to its closest visual match', () => {
    // builders-and-extension-firms has no preview of its own (see lib/showcase.ts) -
    // it should still resolve to something, not fall through to the default rotation.
    const idx = showcaseIndexForTrade('builders-and-extension-firms')
    assert.notEqual(idx, null)
  })

  it('matches the preview\'s own ids directly', () => {
    for (const t of SHOWCASE_TRADES) {
      assert.equal(showcaseIndexForTrade(t.id), SHOWCASE_TRADES.indexOf(t))
    }
  })

  it('is case- and whitespace-insensitive, for a hand-typed link', () => {
    assert.equal(showcaseIndexForTrade(' Roofers '), showcaseIndexForTrade('roofers'))
    assert.equal(showcaseIndexForTrade('ROOFING'), showcaseIndexForTrade('roofing'))
  })

  it('accepts a few plain-English variants of a trade', () => {
    assert.equal(showcaseIndexForTrade('roofer'), showcaseIndexForTrade('roofers'))
    assert.equal(showcaseIndexForTrade('driveway'), showcaseIndexForTrade('driveway-installers'))
    assert.equal(showcaseIndexForTrade('garden'), showcaseIndexForTrade('landscapers'))
  })

  it('returns null for an unrecognised or missing value, so the caller keeps the default', () => {
    assert.equal(showcaseIndexForTrade('plumbers'), null)
    assert.equal(showcaseIndexForTrade(''), null)
    assert.equal(showcaseIndexForTrade(undefined), null)
    assert.equal(showcaseIndexForTrade(null), null)
  })

  it('takes the first value when a query param repeats', () => {
    assert.equal(showcaseIndexForTrade(['roofers', 'lofts']), showcaseIndexForTrade('roofers'))
  })
})

describe('showcaseIdForTradeText', () => {
  it('maps the outreach sheet wording to a scene', () => {
    assert.equal(showcaseIdForTradeText('Roofing'), 'roofing')
    assert.equal(showcaseIdForTradeText('Loft conversions & extensions'), 'lofts')
    assert.equal(showcaseIdForTradeText('Extensions'), 'lofts')
    assert.equal(showcaseIdForTradeText('Driveways & patios'), 'driveways')
    assert.equal(showcaseIdForTradeText('Block paving'), 'driveways')
    assert.equal(showcaseIdForTradeText('Landscaping'), 'landscaping')
  })

  it('every id it can return is a real scene', () => {
    for (const text of ['roof', 'loft', 'drive', 'garden']) {
      const id = showcaseIdForTradeText(text)
      assert.ok(SHOWCASE_TRADES.some((t) => t.id === id), `${text} -> ${id}`)
    }
  })

  it('returns null for an unknown or empty trade', () => {
    assert.equal(showcaseIdForTradeText('Plumbing'), null)
    assert.equal(showcaseIdForTradeText(''), null)
    assert.equal(showcaseIdForTradeText(null), null)
  })
})
