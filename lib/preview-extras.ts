// The "you on Google" section of a prospect's preview: their Google reviews, and their speed next to
// the firms that come top for their trade and town. Pure, so the rules for when each is shown are tested.
// Shown only when it's true and it helps them: a good rating they're not making the most of, and a
// comparison where they're behind at least one rival. Never a made-up or flattering-to-us number.
import type { Teardown } from '@/lib/teardown'

export const MIN_RATING = 4
export const MIN_REVIEWS = 5

export type ReviewsView = { rating: number; reviews: number; shownOnSite: boolean | undefined }
export type RivalRow = { name: string; score: number; you?: true }
export type RivalsView = { query: string; position?: number; checkedAt?: string; rows: RivalRow[]; ahead: number }

export function reviewsView(t: Teardown | null | undefined): ReviewsView | null {
  const g = t?.google
  if (!g || g.rating < MIN_RATING || g.reviews < MIN_REVIEWS) return null
  return { rating: g.rating, reviews: g.reviews, shownOnSite: t?.checks.showsReviews }
}

export function rivalsView(t: Teardown | null | undefined, theirScore: number | null, theirName: string): RivalsView | null {
  const r = t?.rivals
  if (!r || theirScore == null || r.items.length < 2) return null
  const ahead = r.items.filter((i) => i.score > theirScore).length
  if (ahead === 0) return null // they're the quickest - no story here
  const you: RivalRow = { name: theirName, score: theirScore, you: true }
  const rows: RivalRow[] = [...r.items, you].sort((a: RivalRow, b: RivalRow) => b.score - a.score || (a.you ? 1 : 0) - (b.you ? 1 : 0))
  return { query: r.query, position: r.position, checkedAt: r.checkedAt, rows, ahead }
}

export function stars(rating: number): string {
  const full = Math.round(rating)
  return '★'.repeat(full) + '☆'.repeat(5 - full)
}

// The personal video on a preview: only the three players the dashboard stores (migration 062),
// checked again here so nothing else is ever framed on the page. The panel's automatic recordings
// (.mp4s in the dashboard's storage, migration 063) were dropped - pages that still have one show no
// video at all.
const VIDEO = /^https:\/\/(www\.loom\.com\/embed\/[a-f0-9]{32}|www\.youtube-nocookie\.com\/embed\/[A-Za-z0-9_-]{11}|player\.vimeo\.com\/video\/[0-9]{6,12})$/

export function videoSrc(url: string | null | undefined): string | null {
  return typeof url === 'string' && VIDEO.test(url) ? url : null
}
