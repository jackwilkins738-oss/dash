// Content for the hero's interactive website preview (components/site-showcase.tsx).
//
// Everything in here is deliberately generic. The preview is an illustration
// of what a site built for a trade looks like - "YOUR FIRM" is a placeholder,
// there are no client names, no results, no review scores, no counts of jobs
// done. That is the same rule lib/trades.ts holds itself to: nothing here
// claims a result, client or credential the business doesn't have.

export type ShowcaseArt = 'blocks' | 'roofline' | 'slate' | 'hills'

export type ShowcaseTrade = {
  id: string
  /** Label on the switcher tab */
  tab: string
  /** The placeholder firm's descriptor line under "YOUR FIRM" */
  descriptor: string
  eyebrow: string
  headline: string
  sub: string
  cta: string
  /** The brand colour the previewed site is built around (readable behind white text) */
  accent: string
  /** The same hue, lifted for use on this page's dark background */
  accentUi: string
  art: ShowcaseArt
  /** Three service categories shown as work tiles. Categories, not claims. */
  tiles: [string, string, string]
  /** What the dashboard notification says - a job type, nothing more specific */
  enquiry: string
}

export const SHOWCASE_TRADES: ShowcaseTrade[] = [
  {
    id: 'driveways',
    tab: 'Driveways',
    descriptor: 'Resin & block paving',
    eyebrow: 'Driveways & patios',
    headline: 'Driveways that make the street look twice.',
    sub: 'Free written quotes. Clear, fixed prices.',
    cta: 'Get a free quote',
    accent: 'oklch(0.52 0.14 244)',
    accentUi: 'oklch(0.72 0.13 244)',
    art: 'blocks',
    tiles: ['Resin', 'Block paving', 'Imprinted'],
    enquiry: 'Resin driveway',
  },
  {
    id: 'lofts',
    tab: 'Lofts',
    descriptor: 'Loft conversions',
    eyebrow: 'Loft conversions',
    headline: 'More room, without the move.',
    sub: 'Plans, permissions and build, handled.',
    cta: 'Book a survey',
    accent: 'oklch(0.55 0.12 62)',
    accentUi: 'oklch(0.78 0.11 75)',
    art: 'roofline',
    tiles: ['Dormer', 'Hip to gable', 'Rooflight'],
    enquiry: 'Dormer loft conversion',
  },
  {
    id: 'roofing',
    tab: 'Roofing',
    descriptor: 'Roofing & repairs',
    eyebrow: 'Roofing',
    headline: 'Roofing done right, first time.',
    sub: 'Repairs, re-roofs and flat roofs.',
    cta: 'Request a callback',
    accent: 'oklch(0.5 0.16 27)',
    accentUi: 'oklch(0.72 0.15 35)',
    art: 'slate',
    tiles: ['Slate', 'Flat roof', 'Repairs'],
    enquiry: 'Roof repair',
  },
  {
    id: 'landscaping',
    tab: 'Landscaping',
    descriptor: 'Garden design & build',
    eyebrow: 'Landscaping',
    headline: 'Gardens designed to be lived in.',
    sub: 'Design, build and planting in one.',
    cta: 'Plan my garden',
    accent: 'oklch(0.5 0.11 155)',
    accentUi: 'oklch(0.75 0.13 155)',
    art: 'hills',
    tiles: ['Patios', 'Planting', 'Lighting'],
    enquiry: 'Garden redesign',
  },
]

/** How long each trade is shown before the preview moves on by itself, in ms. */
export const SHOWCASE_CYCLE_MS = 5600

/** Next index in the rotation, wrapping. Pure, so the rotation is testable. */
export function nextShowcaseIndex(current: number, count: number = SHOWCASE_TRADES.length): number {
  if (count <= 0) return 0
  return (current + 1) % count
}

// The five trade pages (lib/trades.ts) and this four-trade preview use
// different id schemes - the pages are named after the audience
// ("driveway-installers"), this preview after the work ("driveways"). A
// visitor arriving from a trade-specific outreach batch or a trade page's
// link should land on the matching preview rather than whatever the
// rotation happens to be showing. There's no dedicated builders/extensions
// scene yet, so that one maps to the closest visual (loft conversions,
// the other "bigger structural job") rather than being left unmatched.
const TRADE_ALIASES: Record<string, ShowcaseTrade['id']> = {
  // /websites-for/ page slugs
  'roofers': 'roofing',
  'loft-conversion-companies': 'lofts',
  'driveway-installers': 'driveways',
  'landscapers': 'landscaping',
  'builders-and-extension-firms': 'lofts',
  // common singular/plain variants, in case a link is written by hand
  'roofer': 'roofing',
  'roof': 'roofing',
  'loft': 'lofts',
  'loft-conversion': 'lofts',
  'driveway': 'driveways',
  'landscaper': 'landscaping',
  'landscape': 'landscaping',
  'garden': 'landscaping',
  'builder': 'lofts',
  'extension': 'lofts',
  'extensions': 'lofts',
}

/**
 * Resolve a `?trade=` value (or similar) from a URL to a SHOWCASE_TRADES
 * index, so the hero preview can open on the right trade instead of always
 * starting from the first tab. Accepts the trade-page slugs, this preview's
 * own ids, and a few plain-English variants; anything unrecognised falls
 * back to the default rotation. Case/whitespace-insensitive since it's
 * meant to tolerate a hand-typed or slightly-off link, not just a generated one.
 */
export function showcaseIndexForTrade(query?: string | string[] | null): number | null {
  const value = Array.isArray(query) ? query[0] : query
  if (!value) return null
  const key = value.trim().toLowerCase()
  const id = SHOWCASE_TRADES.some((t) => t.id === key) ? (key as ShowcaseTrade['id']) : TRADE_ALIASES[key]
  if (!id) return null
  const idx = SHOWCASE_TRADES.findIndex((t) => t.id === id)
  return idx === -1 ? null : idx
}

/**
 * Map a free-text trade description - the wording in the outreach sheet,
 * e.g. "Loft conversions & extensions" or "Driveways & patios" - to a
 * preview scene id. Used by the prospect preview pages (app/for/[slug]).
 * Order matters: the first match wins, so a mixed trade lands on the more
 * specific scene. Unknown trades get null and the caller keeps its default.
 */
export function showcaseIdForTradeText(text: string | null | undefined): ShowcaseTrade['id'] | null {
  const t = (text ?? '').toLowerCase()
  if (!t.trim()) return null
  if (/roof/.test(t)) return 'roofing'
  if (/loft|extension|build|renovat/.test(t)) return 'lofts'
  if (/drive|paving|patio|resin/.test(t)) return 'driveways'
  if (/landscap|garden|groundwork/.test(t)) return 'landscaping'
  return null
}
