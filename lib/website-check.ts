// The free speed test's "send me the full report" form: a tradesperson who asked to hear from us.
// The owner gets it on Telegram with a button the panel's bot answers - "Add to pipeline" builds
// their preview (scripts/inbound.py reads the lines below, so their labels are fixed).

export type InboundLead = {
  name: string
  business: string
  email: string
  phone: string
  website: string
  trade: string
  town: string
  score: number | null
}

const clean = (v: unknown, n: number) => String(v ?? '').replace(/[\r\n\t]+/g, ' ').replace(/\s+/g, ' ').trim().slice(0, n)

export function normalizeWebsite(input: string): string | null {
  const trimmed = input.trim()
  if (!trimmed) return null
  try {
    const u = new URL(/^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`)
    if (!/^https?:$/.test(u.protocol) || !u.hostname.includes('.')) return null
    return `${u.protocol}//${u.hostname}${u.pathname === '/' ? '' : u.pathname}`
  } catch {
    return null
  }
}

export function parseLead(body: Record<string, unknown>): { lead: InboundLead } | { error: string } {
  const name = clean(body.name, 80)
  const business = clean(body.business, 120)
  const email = clean(body.email, 254)
  const phone = clean(body.phone, 30).replace(/[^\d+ ()-]/g, '')
  const website = normalizeWebsite(clean(body.website, 200))
  const trade = clean(body.trade, 60)
  const town = clean(body.town, 60)
  const raw = Number(body.score)
  const score = Number.isInteger(raw) && raw >= 0 && raw <= 100 ? raw : null
  if (name.length < 2) return { error: 'Please enter your name.' }
  if (business.length < 2) return { error: 'Please enter your business name.' }
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return { error: 'Please enter a valid email address.' }
  if (!website) return { error: "That website address doesn't look right." }
  return { lead: { name, business, email, phone, website, trade, town, score } }
}

export function alertText(lead: InboundLead): string {
  return [
    '🔥 Inbound lead - asked for their website report (free speed test)',
    'Reply today: they asked to hear from you.',
    '',
    `Business: ${lead.business}`,
    `Name: ${lead.name}`,
    `Email: ${lead.email}`,
    lead.phone ? `Phone: ${lead.phone}` : null,
    `Website: ${lead.website}`,
    lead.score !== null ? `Score: ${lead.score}/100 on mobile` : null,
    lead.trade ? `Trade: ${lead.trade}` : null,
    lead.town ? `Town: ${lead.town}` : null,
  ]
    .filter((l) => l !== null)
    .join('\n')
}

// Answered by the panel's Telegram bot (scripts/telegram_bot.py, "inbound").
export const INBOUND_BUTTONS = { inline_keyboard: [[{ text: '➕ Add to pipeline & build their preview', callback_data: 'inbound' }]] }
