// Which market a preview page is for. UK firms are emailed links on scalardigital.co.uk; US firms
// (the outreach-us workspace, scripts/workspace.py) get links on a separate US domain, pointed at
// this same project. The host a page is opened on decides its prices, wording and contact options.
//
// Env (Vercel -> this project -> Settings -> Environment Variables):
//   US_SITE_HOSTS   the US domain(s), comma separated - e.g. "scalardigital.com,www.scalardigital.com"
//
// `?m=us` on a preview link shows the US version on any host, to check it before the domain is live.

import { PRICES } from './site.ts'

export type Market = 'uk' | 'us'

// The outreach-us workspace quotes the same in its emails and replies (scripts/workspace.py).
// dashboardMonthly: the dashboard (Care plan) after its free first 12 months - optional.
export const US_PRICES = { landing: 1500, build: 4500, dashboardMonthly: 59 } as const

export function usHosts(env: string | undefined = process.env.US_SITE_HOSTS): string[] {
  return (env ?? '')
    .split(',')
    .map((h) => h.trim().toLowerCase())
    .filter(Boolean)
}

/** "uk" unless the page was opened on a US host, or asked for with ?m=us. */
export function marketFor(host: string | null | undefined, param?: string | string[] | null, hosts = usHosts()): Market {
  if (param === 'us') return 'us'
  const bare = (host ?? '').toLowerCase().replace(/:\d+$/, '')
  return bare && hosts.includes(bare) ? 'us' : 'uk'
}

export function pricesFor(market: Market): { landing: number; build: number; dashboardMonthly: number } {
  return market === 'us' ? US_PRICES : { landing: PRICES.landing, build: PRICES.build, dashboardMonthly: PRICES.dashboardMonthly }
}

/** "£2,500" or "$4,500". */
export function formatPrice(market: Market, amount: number): string {
  return market === 'us' ? `$${amount.toLocaleString('en-US')}` : `£${amount.toLocaleString('en-GB')}`
}
