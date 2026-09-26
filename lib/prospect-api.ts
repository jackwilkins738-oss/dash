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

export type Prospect = {
  slug: string
  business_name: string
  trade: string | null
  area: string | null
  website: string | null
  mobile_score: number | null
  lcp_s: number | null
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

/** One prospect's public facts, or null (unknown slug, or not configured). Cached for an hour. */
export async function getProspect(slug: string): Promise<Prospect | null> {
  const cfg = config()
  if (!cfg || !isProspectSlug(slug)) return null
  try {
    const res = await fetch(`${cfg.base}/api/prospects/${slug}`, {
      headers: { authorization: `Bearer ${cfg.secret}` },
      next: { revalidate: 3600 },
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
