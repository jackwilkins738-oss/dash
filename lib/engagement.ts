// What a prospect did on their preview page, cleaned up before it leaves the
// website: who counts as a person, what a typed phone number may look like,
// and the wording of the owner's alert for a one-tap answer. Pure, so it's tested
// on its own (lib/engagement.test.ts).

export const SECTIONS = ['loading', 'rebuilt', 'race', 'findings', 'pricing', 'reply'] as const
export type Section = (typeof SECTIONS)[number]
export const CHOICES = ['call', 'whatsapp', 'not_now'] as const
export type Choice = (typeof CHOICES)[number]

// Email security scanners that open links in a real browser to check them, and the usual crawlers.
// They'd otherwise show as "viewed" - often 2-3 times within a minute of sending.
const BOT_UA =
  /headlesschrome|phantomjs|puppeteer|playwright|selenium|(?:^|[^a-z])bot\b|[a-z]bot\/|crawler|spider|slurp|facebookexternalhit|preview|scanner|proofpoint|mimecast|barracuda|safelinks|python-requests|curl\/|wget/i

export function isBotUserAgent(ua: string | null | undefined): boolean {
  return !ua || BOT_UA.test(ua)
}

/** A UK phone number they typed for "ring me", tidied - or '' if it doesn't look like one. */
export function cleanPhone(raw: unknown): string {
  const digits = String(raw ?? '').replace(/[^\d+]/g, '')
  const national = digits.startsWith('+44') ? '0' + digits.slice(3) : digits.startsWith('44') ? '0' + digits.slice(2) : digits
  return /^0\d{9,10}$/.test(national) ? national : ''
}

export function clampEngagement(body: Record<string, unknown>): { seconds: number; scroll: number; reached: Section[] } {
  const int = (v: unknown, max: number) => Math.min(max, Math.max(0, Math.round(Number(v) || 0)))
  const reached = Array.isArray(body.reached)
    ? [...new Set(body.reached.map(String))].filter((s): s is Section => (SECTIONS as readonly string[]).includes(s))
    : []
  return { seconds: int(body.seconds, 1800), scroll: int(body.scroll, 100), reached }
}

/** The owner's Telegram text for a one-tap answer. The firm's details come from the dashboard's record. */
export function choiceAlert(
  choice: Choice,
  firm: { business_name: string; trade?: string | null; area?: string | null; view_count?: number | null },
  phone: string,
): string {
  const where = [firm.trade, firm.area].filter(Boolean).join(', ')
  const visits = firm.view_count && firm.view_count > 1 ? ` (visit ${firm.view_count})` : ''
  const head = {
    call: `📞 ${firm.business_name} tapped "Yes, give me a ring" on their preview${visits}.`,
    whatsapp: `💬 ${firm.business_name} tapped "WhatsApp me" on their preview${visits} - a message to you should follow.`,
    not_now: `${firm.business_name} tapped "Maybe later" on their preview. Follow-up emails stop; a call back in 3 months is worth it.`,
  }[choice]
  const number =
    choice === 'call' ? (phone ? `Number they gave: ${phone}` : 'They left the number blank - ring the one on your list.') : null
  return [head, where || null, number, choice === 'call' ? 'Ring them now, while it is fresh.' : null].filter(Boolean).join('\n')
}
