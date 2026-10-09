// The preview's headline: the single strongest true thing we know about their
// site, in their terms. Picked in order of what moves a business owner most -
// rivals ahead of them on Google Maps, then a slow load on a phone, then the
// problems found - and only ever from measured figures. With none of those, the
// plain "a sharper website" headline stays.

export type PitchInput = {
  business: string
  site: string | null
  score: number | null
  lcp: number | null
  rivalsAhead: number
  findings: number
}

export type Pitch = { title: string; body: string; kind: 'rivals' | 'slow' | 'findings' | 'plain' }

export function heroPitch(p: PitchInput): Pitch {
  const site = p.site ?? 'your website'
  const look = `Below: what a customer sees today, and a concept of the fix, made for ${p.business}. Nothing to sign up for.`
  if (p.rivalsAhead > 0 && p.score != null) {
    return {
      kind: 'rivals',
      title: `${p.rivalsAhead === 1 ? 'A rival' : `${p.rivalsAhead} rivals`} near the top of Google Maps ${p.rivalsAhead === 1 ? 'loads' : 'load'} faster than ${p.business}.`,
      body: `${site} scores ${p.score}/100 on Google’s own phone speed test. When someone nearby searches, the quicker sites get the first look. ${look}`,
    }
  }
  if (p.lcp != null && p.lcp > 4) {
    return {
      kind: 'slow',
      title: `${site} takes ${p.lcp.toFixed(1)}s to show on a phone.`,
      body: `Google counts anything over 4 seconds as poor, and its own research found more than half of visits on a phone are abandoned when a page takes over 3. ${look}`,
    }
  }
  if (p.findings > 0) {
    return {
      kind: 'findings',
      title: `${p.findings === 1 ? 'One thing' : `${p.findings} things`} on ${site} could be losing you enquiries.`,
      body: `We checked it with Google’s own phone test and a look at your homepage. ${look}`,
    }
  }
  return {
    kind: 'plain',
    title: `A sharper website for ${p.business}.`,
    body: `A concept of a Scalar build for ${p.business}${p.site ? `, next to where ${p.site} stands on Google’s own speed test today` : ''}. Nothing to sign up for — have a look around.`,
  }
}

export type Tile = { value: string; label: string; tone: 'bad' | 'warn' | 'ok' }

/** The report card under the headline: their numbers, coloured by Google's own bands. At most four. */
export function reportTiles(p: { score: number | null; lcp: number | null; findings: number; mapsPosition?: number; mapsQuery?: string }): Tile[] {
  const out: Tile[] = []
  if (p.score != null) {
    out.push({ value: `${p.score}/100`, label: 'Google’s phone speed test', tone: p.score >= 90 ? 'ok' : p.score >= 50 ? 'warn' : 'bad' })
  }
  if (p.lcp != null) {
    out.push({ value: `${p.lcp.toFixed(1)}s`, label: 'before it shows on a phone', tone: p.lcp <= 2.5 ? 'ok' : p.lcp <= 4 ? 'warn' : 'bad' })
  }
  if (p.findings > 0) {
    out.push({ value: String(p.findings), label: p.findings === 1 ? 'problem found on your homepage' : 'problems found on your homepage', tone: 'bad' })
  }
  if (p.mapsPosition != null && p.mapsQuery) {
    out.push({ value: `#${p.mapsPosition}`, label: `on Google Maps for “${p.mapsQuery}”`, tone: p.mapsPosition <= 3 ? 'ok' : 'warn' })
  }
  return out.slice(0, 4)
}
