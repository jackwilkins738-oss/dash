// "Will a website pay for itself?" - the sum behind the payback calculator
// (components/payback-calculator.tsx). Profit, not turnover: a £4,000 job at a
// 25% margin is £1,000 towards the site, not £4,000. No promise of how many
// jobs a site brings - the visitor picks that number.

export type PaybackInput = {
  /** Average job value, £ */
  jobValue: number
  /** Profit on a job after materials and labour, % */
  marginPercent: number
  /** Extra jobs a year they think the site brings */
  extraJobsPerYear: number
  /** What the site costs, £ (one-off) */
  sitePrice: number
}

export type Payback = {
  profitPerJob: number
  /** Jobs needed to cover the site, rounded up; null when a job makes no profit */
  jobsToPayBack: number | null
  /** Profit from the extra jobs in a year, minus the site */
  firstYear: number
}

const clamp = (n: number, lo: number, hi: number) => (Number.isFinite(n) ? Math.min(hi, Math.max(lo, n)) : lo)

export function payback(input: PaybackInput): Payback {
  const jobValue = clamp(input.jobValue, 0, 1_000_000)
  const margin = clamp(input.marginPercent, 0, 100)
  const jobs = clamp(Math.round(input.extraJobsPerYear), 0, 1000)
  const price = clamp(input.sitePrice, 0, 1_000_000)
  const profitPerJob = Math.round((jobValue * margin) / 100)
  return {
    profitPerJob,
    jobsToPayBack: profitPerJob > 0 ? Math.max(1, Math.ceil(price / profitPerJob)) : null,
    firstYear: profitPerJob * jobs - price,
  }
}
