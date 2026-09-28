// Real launches only, and only once the client has said yes to being named.
// The launch report (scripts/launch_report.py) prints each launch ready to
// paste in here with `permission: false`. Flip it to true once they've agreed
// in writing (an email or WhatsApp is enough). Until at least one entry is
// publishable, the section doesn't render at all: an empty "results" block
// looks worse than none.

export type CaseStudy = {
  business: string
  trade: string
  area: string
  /** YYYY-MM-DD */
  launched: string
  /** Their new site, e.g. kerrroofing.co.uk */
  site: string
  /** Google PageSpeed mobile score, 0-100, measured the same way before and after */
  scoreBefore: number
  scoreAfter: number
  /** Seconds until the main content shows on a phone (LCP) */
  loadBefore: number
  loadAfter: number
  /** Problems the old site had that the new one fixed, in plain words */
  fixed: string[]
  /** Their own words, exactly as they said them, if they gave any */
  quote?: { text: string; name: string }
  /** They agreed to be named on this site */
  permission: boolean
}

export const CASE_STUDIES: CaseStudy[] = []

/** Why an entry can't be shown as it stands. Empty means it's fine. */
export function caseStudyProblems(c: CaseStudy): string[] {
  const problems: string[] = []
  if (!c.business.trim() || !c.trade.trim() || !c.area.trim()) problems.push('business, trade and area are all needed')
  if (!/^\d{4}-\d{2}-\d{2}$/.test(c.launched) || Number.isNaN(Date.parse(c.launched))) problems.push('launched must be YYYY-MM-DD')
  if (!/^[a-z0-9.-]+\.[a-z]{2,}$/.test(c.site)) problems.push('site must be a bare domain, e.g. kerrroofing.co.uk')
  for (const [name, v] of [['scoreBefore', c.scoreBefore], ['scoreAfter', c.scoreAfter]] as const) {
    if (!Number.isInteger(v) || v < 0 || v > 100) problems.push(`${name} must be a whole number 0-100`)
  }
  for (const [name, v] of [['loadBefore', c.loadBefore], ['loadAfter', c.loadAfter]] as const) {
    if (!(v > 0 && v < 120)) problems.push(`${name} must be seconds, above 0`)
  }
  if (c.quote && (!c.quote.text.trim() || !c.quote.name.trim())) problems.push('a quote needs both the words and who said them')
  return problems
}

/** The entries that can go on the site: permitted and valid, newest first. */
export function publishable(list: CaseStudy[] = CASE_STUDIES): CaseStudy[] {
  return list
    .filter((c) => c.permission && caseStudyProblems(c).length === 0)
    .sort((a, b) => b.launched.localeCompare(a.launched))
}
