import { PRICES } from './site.ts'

// The owner's alert when a prospect opens their quote from their own preview - with a warning if the
// quote's price isn't the one their preview page showed them.
export function startAlert(
  quote: { business_name: string; quote_number: string; total_pence: number; reused: boolean },
  pkg: 'build' | 'landing',
): string {
  const label = pkg === 'build' ? 'The Scalar build' : 'Landing page'
  const total = quote.total_pence / 100
  const lines = [
    quote.reused
      ? `🛒 ${quote.business_name} reopened their quote (${quote.quote_number}) from their preview.`
      : `🛒 ${quote.business_name} asked for their quote from their preview: ${label}, ${quote.quote_number}, £${total.toLocaleString('en-GB')} total.`,
    'They can accept, sign and pay the deposit on it now - give them a ring while they are looking.',
  ]
  if (!quote.reused && Math.round(total) !== PRICES[pkg]) {
    lines.push(
      `⚠️ The preview page shows £${PRICES[pkg].toLocaleString('en-GB')} but the quote is £${total.toLocaleString('en-GB')} - make the panel's quote prices match the website's (or it's VAT).`,
    )
  }
  return lines.join('\n')
}
