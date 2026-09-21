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
