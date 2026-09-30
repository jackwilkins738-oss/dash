// One place for the facts that identity, metadata and structured data all repeat.
// Keep these consistent with what the site actually says elsewhere.

export const SITE = {
  name: 'Scalar Digital',
  url: 'https://www.scalardigital.co.uk',
  email: 'hello@scalardigital.co.uk',
  phone: '+447401696272',
  linkedin: 'https://www.linkedin.com/in/scalar-digital-868841438/',
  // A 15-minute call, for anyone who'd rather talk than type.
  booking: 'https://cal.com/scalardigital/15min',
  logo: 'https://www.scalardigital.co.uk/brand/logo-square-512.png',
  description:
    'Fast, hand-coded websites for UK roofers, builders, loft conversion, driveway and landscaping firms. Fixed price from £750, and you own it outright.',
} as const

// Last real content change per page. Used by the sitemap so `lastmod` means something
// (a date that changes on every build tells Google to ignore it).
export const UPDATED = '2026-09-24'

export const PRICES = { landing: 750, build: 2500, dashboardMonthly: 39 } as const

// Partners: accountants, bookkeepers, merchants and others who see a lot of trades. Paid once the
// client they sent has paid for their build. Kept here so /partners and the enquiry alert agree.
export const PARTNER = { perBuild: 100, perLanding: 50, clientDiscountPercent: 10 } as const
