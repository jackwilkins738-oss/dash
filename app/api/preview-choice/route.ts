import { NextResponse } from 'next/server'
import { getProspect, isProspectSlug, recordProspectChoice } from '@/lib/prospect-api'
import { CHOICES, choiceAlert, cleanPhone, type Choice } from '@/lib/engagement'
import { ownerAlert } from '@/lib/owner-alert'

// A one-tap answer on a prospect's preview page (components/quick-reply.tsx):
// "Yes, give me a ring", "WhatsApp me" or "Maybe later". Recorded in the
// dashboard (migration 059) and texted to the owner straight away. The firm's
// name in the alert comes from the dashboard's record; the only thing taken
// from the request is a phone number, and only if it looks like a UK one -
// it goes into the alert and nowhere else.

const RATE_LIMIT = 10
const WINDOW_MS = 10 * 60 * 1000
const hits = new Map<string, number[]>()

function isRateLimited(ip: string) {
  const now = Date.now()
  const recent = (hits.get(ip) ?? []).filter((t) => now - t < WINDOW_MS)
  recent.push(now)
  hits.set(ip, recent)
  if (hits.size > 5000) hits.clear()
  return recent.length > RATE_LIMIT
}

export async function POST(request: Request) {
  const origin = request.headers.get('origin')
  if (origin && origin !== new URL(request.url).origin) {
    return NextResponse.json({ error: 'Invalid request.' }, { status: 403 })
  }
  const ip =
    request.headers.get('x-vercel-forwarded-for')?.split(',')[0]?.trim() ||
    request.headers.get('x-forwarded-for')?.split(',')[0]?.trim() ||
    'unknown'
  if (isRateLimited(ip)) return NextResponse.json({ ok: true })
  let body: Record<string, unknown>
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'Invalid request.' }, { status: 400 })
  }
  const slug = typeof body.slug === 'string' ? body.slug : ''
  const choice = String(body.choice ?? '') as Choice
  if (!isProspectSlug(slug) || !CHOICES.includes(choice)) return NextResponse.json({ ok: true })
  // If the dashboard can't record it (its update not deployed, or migration 059 not run yet), the
  // owner still hears about it - a "ring me" must never be lost.
  const firm = (await recordProspectChoice(slug, choice)) ?? (await getProspect(slug))
  if (firm) await ownerAlert(choiceAlert(choice, firm, cleanPhone(body.phone)), 'preview-choice')
  // Always the same answer, so the page can't be used to probe slugs.
  return NextResponse.json({ ok: true })
}
