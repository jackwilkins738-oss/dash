import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { CASE_STUDIES, caseStudyProblems, publishable, type CaseStudy } from './case-studies.ts'

const good: CaseStudy = {
  business: 'Kerr Roofing',
  trade: 'Roofer',
  area: 'Guildford',
  launched: '2026-10-01',
  site: 'kerrroofing.co.uk',
  scoreBefore: 31,
  scoreAfter: 98,
  loadBefore: 9.4,
  loadAfter: 1.1,
  fixed: ['No tap-to-call button'],
  permission: true,
}

describe('case studies', () => {
  it('every real entry is valid', () => {
    for (const c of CASE_STUDIES) assert.deepEqual(caseStudyProblems(c), [], c.business)
  })

  it('shows only permitted, valid entries, newest first', () => {
    const older = { ...good, business: 'Older', launched: '2026-09-01' }
    const unpermitted = { ...good, business: 'Not yet', permission: false }
    const broken = { ...good, business: 'Broken', scoreAfter: 140 }
    assert.deepEqual(publishable([older, unpermitted, broken, good]).map((c) => c.business), ['Kerr Roofing', 'Older'])
    assert.deepEqual(publishable([]), [])
  })

  it('catches the mistakes a hand-pasted entry makes', () => {
    assert.deepEqual(caseStudyProblems(good), [])
    assert.equal(caseStudyProblems({ ...good, site: 'https://kerrroofing.co.uk/' }).length, 1)
    assert.equal(caseStudyProblems({ ...good, launched: '01/10/2026' }).length, 1)
    assert.equal(caseStudyProblems({ ...good, scoreBefore: 31.5 }).length, 1)
    assert.equal(caseStudyProblems({ ...good, loadAfter: 0 }).length, 1)
    assert.equal(caseStudyProblems({ ...good, quote: { text: 'Brilliant', name: '' } }).length, 1)
  })
})
