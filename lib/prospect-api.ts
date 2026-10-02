// The website's side of the prospect pipeline. Prospects live in the
// dashboard's database (loft-dashboard, migration 041), not in this repo:
// both repos are public, and a prospect list committed here would be
// readable by anyone. The preview pages fetch one prospect at a time,
// server-to-server, with a shared secret that never reaches the browser.
// Only ever import this from server code (pages, route handlers): the
// secret is read from a non-NEXT_PUBLIC env var, so it can't be inlined
// into a client bundle, but there's no reason to ship this file there.
//
// Env (Vercel -> this project -> Settings -> Environment Variables):
//   DASHBOARD_API_URL      https://admin.scalardigital.co.uk
//   PROSPECTS_API_SECRET   the same value as the dashboard's own
//   TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID   already set for the contact form

import type { Teardown } from '@/lib/teardown'

export type Prospect = {
  slug: string
  business_name: string
  trade: string | null
  area: string | null
  website: string | null
  mobile_score: number | null
  lcp_s: number | null
  /** Automated website checks (dashboard migration 042), when they've been run. */
  teardown?: Teardown | null
  teardown_at?: string | null
  updated_at?: string
}

const SLUG_RE = /^[a-z0-9]+(-[a-z0-9]+)*$/

export function isProspectSlug(slug: string): boolean {
  return slug.length <= 80 && SLUG_RE.test(slug)
}

function config() {
  const base = process.env.DASHBOARD_API_URL?.replace(/\/+$/, '')
  const secret = process.env.PROSPECTS_API_SECRET
  return base && secret ? { base, secret } : null
}

/**
 * One prospect's public facts, or null (unknown slug, or not configured).
 *
 * Fetched fresh on every view, never cached: a preview opened before its
 * prospect was pushed must not keep showing "not found" once it has been,
 * and a re-run speed check should show straight away. These pages are
 * private and rarely visited, so the extra dashboard call costs nothing.
 */
export async function getProspect(slug: string): Promise<Prospect | null> {
  const cfg = config()
  if (!cfg || !isProspectSlug(slug)) return null
  try {
    const res = await fetch(`${cfg.base}/api/prospects/${slug}`, {
      headers: { authorization: `Bearer ${cfg.secret}` },
      cache: 'no-store',
    })
    if (!res.ok) return null
    const body = (await res.json()) as { prospect?: Prospect }
    return body.prospect ?? null
  } catch {
    return null
  }
}

/** Records a view in the dashboard and returns the updated row (with view_count), or null. */
export async function recordProspectView(
  slug: string,
): Promise<(Pick<Prospect, 'business_name' | 'trade' | 'area' | 'website' | 'mobile_score'> & { view_count: number }) | null> {
  const cfg = config()
  if (!cfg || !isProspectSlug(slug)) return null
  try {
    const res = await fetch(`${cfg.base}/api/prospects/${slug}/view`, {
      method: 'POST',
      headers: { authorization: `Bearer ${cfg.secret}` },
      cache: 'no-store',
    })
    if (!res.ok) return null
    const body = (await res.json()) as { prospect?: Prospect & { view_count: number } }
    return body.prospect ?? null
  } catch {
    return null
  }
}

/** "Not for us" from their preview: the dashboard marks them lost. Returns the firm's name if it changed, else null. */
export async function recordProspectOptOut(slug: string): Promise<string | null> {
  const cfg = config()
  if (!cfg || !isProspectSlug(slug)) return null
  try {
    const res = await fetch(`${cfg.base}/api/prospects/${slug}/optout`, {
      method: 'POST',
      headers: { authorization: `Bearer ${cfg.secret}` },
      cache: 'no-store',
    })
    if (!res.ok) return null
    const body = (await res.json()) as { business_name?: string; changed?: boolean }
    return body.changed && body.business_name ? body.business_name : null
  } catch {
    return null
  }
}

/** Time on page, scroll depth and sections reached (dashboard migration 059). Fire and forget. */
export async function recordProspectEngagement(
  slug: string,
  e: { seconds: number; scroll: number; reached: string[] },
): Promise<void> {
  const cfg = config()
  if (!cfg || !isProspectSlug(slug)) return
  try {
    await fetch(`${cfg.base}/api/prospects/${slug}/engagement`, {
      method: 'POST',
      headers: { authorization: `Bearer ${cfg.secret}`, 'content-type': 'application/json' },
      body: JSON.stringify(e),
      cache: 'no-store',
    })
  } catch {
    // Engagement is a nice-to-have; a miss never matters.
  }
}

/** A one-tap answer from their preview. Returns the firm (from the dashboard's record), or null. */
export async function recordProspectChoice(
  slug: string,
  choice: string,
): Promise<{ business_name: string; trade: string | null; area: string | null; view_count: number } | null> {
  const cfg = config()
  if (!cfg || !isProspectSlug(slug)) return null
  try {
    const res = await fetch(`${cfg.base}/api/prospects/${slug}/choice`, {
      method: 'POST',
      headers: { authorization: `Bearer ${cfg.secret}`, 'content-type': 'application/json' },
      body: JSON.stringify({ choice }),
      cache: 'no-store',
    })
    if (!res.ok) return null
    const body = (await res.json()) as { prospect?: { business_name: string; trade: string | null; area: string | null; view_count: number } }
    return body.prospect ?? null
  } catch {
    return null
  }
}
