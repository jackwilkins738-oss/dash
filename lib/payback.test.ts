import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { payback } from './payback.ts'

describe('payback', () => {
  it('counts profit, not turnover', () => {
    const p = payback({ jobValue: 4000, marginPercent: 25, extraJobsPerYear: 4, sitePrice: 2500 })
    assert.equal(p.profitPerJob, 1000)
    assert.equal(p.jobsToPayBack, 3) // £2,500 needs three £1,000 profits
    assert.equal(p.firstYear, 1500)
  })

  it('says so when a job makes no profit, and never goes below one job', () => {
    assert.equal(payback({ jobValue: 4000, marginPercent: 0, extraJobsPerYear: 4, sitePrice: 750 }).jobsToPayBack, null)
    assert.equal(payback({ jobValue: 20000, marginPercent: 30, extraJobsPerYear: 1, sitePrice: 750 }).jobsToPayBack, 1)
  })

  it('shrugs off silly input', () => {
    const p = payback({ jobValue: Number.NaN, marginPercent: 250, extraJobsPerYear: -3, sitePrice: 750 })
    assert.equal(p.profitPerJob, 0)
    assert.equal(p.firstYear, -750)
  })
})
