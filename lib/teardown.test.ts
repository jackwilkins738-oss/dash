import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { MAX_FINDINGS, teardownFindings, teardownPasses, type Teardown } from './teardown.ts'

const YEAR = 2026
const t = (over: Partial<Teardown> = {}): Teardown => ({ v: 1, checks: {}, ...over })

describe('teardownFindings', () => {
  it('shows nothing for a missing or clean teardown', () => {
    assert.deepEqual(teardownFindings(null, YEAR), [])
    assert.deepEqual(teardownFindings(t({ checks: { tapToCall: true, https: true } }), YEAR), [])
  })

  it('never turns an unchecked item into a problem', () => {
    // No keys at all = nothing could be checked = nothing to say.
    assert.deepEqual(teardownFindings(t(), YEAR), [])
  })

  it('puts the commercially important findings first', () => {
    const ids = teardownFindings(
      t({ checks: { whatsapp: false, tapToCall: false, localSchema: false, contactForm: false } }),
      YEAR,
    ).map((f) => f.id)
    assert.deepEqual(ids, ['tap-to-call', 'contact-form', 'local-schema', 'whatsapp'])
  })

  it(`caps the list at ${MAX_FINDINGS}`, () => {
    const all = t({
      checks: {
        tapToCall: false,
        contactForm: false,
        readableText: false,
        tapTargets: false,
        localSchema: false,
        metaDescription: false,
        whatsapp: false,
        https: false,
      },
      imageSavingsKb: 2400,
      copyrightYear: 2018,
      seoScore: 60,
      platform: 'wix',
    })
    assert.equal(teardownFindings(all, YEAR).length, MAX_FINDINGS)
  })

  it('only calls a copyright year stale when it is more than a year old', () => {
    assert.equal(teardownFindings(t({ copyrightYear: 2025 }), YEAR).length, 0)
    const [f] = teardownFindings(t({ copyrightYear: 2021 }), YEAR)
    assert.equal(f.title, 'Your footer still says © 2021')
  })

  it('formats image savings and ignores small ones', () => {
    assert.equal(teardownFindings(t({ imageSavingsKb: 300 }), YEAR).length, 0)
    assert.equal(teardownFindings(t({ imageSavingsKb: 2400 }), YEAR)[0].title, 'Images could be 2.4 MB lighter')
    assert.equal(teardownFindings(t({ imageSavingsKb: 640 }), YEAR)[0].title, 'Images could be 640 KB lighter')
  })

  it('names hosted builders, and only mentions WordPress with a heavy plugin count', () => {
    assert.match(teardownFindings(t({ platform: 'squarespace' }), YEAR)[0].title, /Squarespace/)
    assert.equal(teardownFindings(t({ platform: 'wordpress', wpPluginCount: 6 }), YEAR).length, 0)
    assert.match(teardownFindings(t({ platform: 'wordpress', wpPluginCount: 22 }), YEAR)[0].title, /loads 22 WordPress plugins/)
  })

  it('leaves a decent SEO score alone', () => {
    assert.equal(teardownFindings(t({ seoScore: 92 }), YEAR).length, 0)
  })
})

describe('teardownPasses', () => {
  it('counts only checks that came back fine', () => {
    assert.equal(teardownPasses(t({ checks: { tapToCall: true, https: true, whatsapp: false } })), 2)
    assert.equal(teardownPasses(null), 0)
  })
})
