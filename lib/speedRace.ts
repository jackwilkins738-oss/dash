// The timeline behind the "speed race" section (components/speed-race.tsx):
// two phones load the same page side by side, in real time.
//
// It is an illustration, and the section says so on the page. The slow side
// models the figure the site already quotes ("loads in 6+ seconds on
// mobile"); the fast side models a hand-built page that ships almost nothing.
// Keeping the numbers here, as data, means the staging logic is plain
// functions that can be tested, and the component only has to draw.

export type Stage = 'blank' | 'header' | 'hero' | 'banner' | 'images' | 'done'

/** Order in which a page can reach each stage. */
export const STAGE_ORDER: readonly Stage[] = ['blank', 'header', 'hero', 'banner', 'images', 'done']

/** Milliseconds at which a site reaches each stage. A missing stage is skipped. */
export type Timeline = Partial<Record<Stage, number>>

export const RACE = {
  // A typical page-builder site on a mid-range phone: nothing for the best
  // part of a second, text before images, then a cookie banner that shoves
  // the page down and images that arrive without reserved space, so the
  // layout jumps twice.
  slow: { header: 900, hero: 2400, banner: 3900, images: 5200, done: 6400 } satisfies Timeline,
  // A hand-built page: no banner to inject, space reserved for its image.
  fast: { header: 120, hero: 300, images: 450, done: 600 } satisfies Timeline,
} as const

/** The furthest stage a timeline has reached by time `t` (ms). */
export function stageAt(timeline: Timeline, t: number): Stage {
  let current: Stage = 'blank'
  for (const stage of STAGE_ORDER) {
    const at = timeline[stage]
    if (at !== undefined && t >= at) current = stage
  }
  return current
}

/** Has `stage` reached `needed` (or gone past it)? */
export function reached(stage: Stage, needed: Stage): boolean {
  return STAGE_ORDER.indexOf(stage) >= STAGE_ORDER.indexOf(needed)
}

/** Load progress, 0 to 1, clamped. */
export function progressAt(t: number, doneAt: number): number {
  if (doneAt <= 0) return 1
  return Math.min(1, Math.max(0, t / doneAt))
}

/** 600 -> "0.6s". Rounded to a tenth, as a stopwatch would show it. */
export function formatSeconds(ms: number): string {
  return `${(Math.round(Math.max(0, ms) / 100) / 10).toFixed(1)}s`
}

// ---------------------------------------------------------------------
// The personal race on a prospect's preview page (app/for/[slug]): a
// Scalar build against their own site, both on MEASURED figures from the
// same Google PageSpeed mobile test - Largest Contentful Paint, the moment
// the main content appears.
// ---------------------------------------------------------------------

/**
 * A real Scalar build, measured on Google's mobile test. `lcpMs` stays null
 * until it has actually been measured, and the personal race doesn't render
 * while it's null - so no unmeasured number can ever appear on a page.
 * Re-measure (median of 3 runs) whenever the example build changes.
 */
export const SCALAR_BUILD: { lcpMs: number | null; page: string; measuredOn: string } = {
  // Google PageSpeed Insights, mobile, 27 Sep 2026: 1.1s on all 3 runs.
  lcpMs: 1100,
  page: 'the Verdigris Roofing example build',
  measuredOn: '27 September 2026',
}

/** Only race when it's a clear win - a near-tie would work against the page. */
export const MIN_RACE_GAP_MS = 1000

/**
 * A load timeline shaped around one measured figure (LCP): the header
 * shows partway, and the main content and images land at LCP. No cookie
 * banner - that's only in the homepage's illustration, never assumed
 * about a real prospect's site.
 */
export function timelineFromLcp(lcpMs: number): Timeline {
  const lcp = Math.max(100, Math.round(lcpMs))
  return { header: Math.round(lcp * 0.4), hero: lcp, images: lcp, done: lcp }
}

/**
 * How much faster than real time to play the race so it never runs longer
 * than `capMs`. 1 = real time. The clocks always show the true seconds.
 */
export function raceSpeedFactor(slowestMs: number, capMs = 8000): number {
  return slowestMs > capMs ? slowestMs / capMs : 1
}
