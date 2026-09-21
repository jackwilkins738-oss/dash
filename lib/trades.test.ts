import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { TRADES, TRADE_BY_SLUG } from './trades.ts'

// lib/trades.ts is data, but it is data that generates a page, a sitemap
// entry, a footer link and a set of metadata per trade. A typo in it does
// not fail the build - it ships. These tests pin the properties that would
// quietly hurt search or break a route.

// app/layout.tsx wraps every page title as '%s | Scalar Digital'.
const TITLE_TEMPLATE_LENGTH = ' | Scalar Digital'.length
// Google truncates around 60 characters of title and 155-160 of description.
const MAX_TITLE = 60
const MAX_DESCRIPTION = 160

const REQUIRED_TEXT = [
  'slug',
  'label',
  'audience',
  'metaTitle',
  'metaDescription',
  'eyebrow',
  'h1',
  'lede',
  'intro',
] as const

describe('TRADES', () => {
  it('has at least one trade', () => {
    assert.ok(TRADES.length > 0)
  })

  it('gives every trade a non-empty value for every text field', () => {
    for (const t of TRADES) {
      for (const key of REQUIRED_TEXT) {
        assert.ok(t[key].trim().length > 0, `${t.slug}: ${key} is empty`)
      }
    }
  })

  it('uses unique, URL-safe slugs', () => {
    const slugs = TRADES.map((t) => t.slug)
    assert.equal(new Set(slugs).size, slugs.length, 'duplicate slug')
    for (const slug of slugs) {
      // Lowercase words joined by single hyphens: it becomes a path segment
      // in /websites-for/[trade], the sitemap and the canonical URL.
      assert.match(slug, /^[a-z0-9]+(-[a-z0-9]+)*$/, `${slug} is not URL-safe`)
    }
  })

  it('keeps the rendered <title> within what search results show', () => {
    for (const t of TRADES) {
      const full = t.metaTitle.length + TITLE_TEMPLATE_LENGTH
      assert.ok(full <= MAX_TITLE, `${t.slug}: title is ${full} chars once the site suffix is added (max ${MAX_TITLE})`)
    }
  })

  it('keeps meta descriptions short enough not to be cut off mid-sentence', () => {
    for (const t of TRADES) {
      assert.ok(
        t.metaDescription.length <= MAX_DESCRIPTION,
        `${t.slug}: description is ${t.metaDescription.length} chars (max ${MAX_DESCRIPTION})`,
      )
    }
  })

  it('never repeats a title, description or h1 across trades', () => {
    // Near-identical pages with identical metadata is exactly the pattern
    // search engines fold together, which defeats a page per trade.
    for (const key of ['metaTitle', 'metaDescription', 'h1'] as const) {
      const values = TRADES.map((t) => t[key].trim().toLowerCase())
      assert.equal(new Set(values).size, values.length, `duplicate ${key}`)
    }
  })

  it('gives every trade content to render: must-haves and FAQs', () => {
    for (const t of TRADES) {
      assert.ok(t.mustHave.length > 0, `${t.slug}: no mustHave items`)
      for (const m of t.mustHave) {
        assert.ok(m.title.trim() && m.body.trim(), `${t.slug}: empty mustHave entry`)
      }
      assert.ok(t.faqs.length > 0, `${t.slug}: no FAQs`)
      for (const f of t.faqs) {
        assert.ok(f.q.trim() && f.a.trim(), `${t.slug}: empty FAQ entry`)
      }
    }
  })

  it('does not ask the same FAQ question twice on one page', () => {
    for (const t of TRADES) {
      const qs = t.faqs.map((f) => f.q.trim().toLowerCase())
      assert.equal(new Set(qs).size, qs.length, `${t.slug}: repeated FAQ question`)
    }
  })
})

describe('TRADE_BY_SLUG', () => {
  it('indexes every trade, and only the trades', () => {
    assert.equal(Object.keys(TRADE_BY_SLUG).length, TRADES.length)
  })

  it('returns the same object as the list for each slug', () => {
    for (const t of TRADES) assert.equal(TRADE_BY_SLUG[t.slug], t)
  })

  it('returns undefined for an unknown slug, so the page can 404', () => {
    // app/websites-for/[trade]/page.tsx relies on this to call notFound().
    assert.equal(TRADE_BY_SLUG['not-a-real-trade'], undefined)
  })
})
