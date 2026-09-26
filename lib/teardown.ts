// Turns a prospect's stored website checks (dashboard migration 042,
// gathered by scripts/push_prospects.py --teardown) into the short list
// shown on their preview page: "What we found on smithroofing.co.uk".
//
// Rules the wording holds to, because the reader is the business owner:
//   - only failed checks become findings; an unchecked item (absent) is
//     never guessed at, and never shown as a problem
//   - every finding is something they can see for themselves, from
//     Google's own test or their own homepage - an observation, not a verdict
//   - no invented statistics, no security claims, nothing that reads as an insult
//   - at most MAX_FINDINGS, most commercially important first

export type Teardown = {
  v: 1
  checks: Partial<
    Record<
      | 'tapToCall'
      | 'whatsapp'
      | 'contactForm'
      | 'localSchema'
      | 'readableText'
      | 'tapTargets'
      | 'pageTitle'
      | 'metaDescription'
      | 'https'
      | 'secureAssets',
      boolean
    >
  >
  seoScore?: number
  accessibilityScore?: number
  imageSavingsKb?: number
  pageWeightKb?: number
  copyrightYear?: number
  platform?: 'wordpress' | 'wix' | 'squarespace' | 'godaddy' | 'webflow' | 'weebly' | 'duda' | 'shopify'
  wpPluginCount?: number
}

export type Finding = { id: string; title: string; detail: string; fix: string }

export const MAX_FINDINGS = 6

const PLATFORM_NAMES: Record<NonNullable<Teardown['platform']>, string> = {
  wordpress: 'WordPress',
  wix: 'Wix',
  squarespace: 'Squarespace',
  godaddy: 'GoDaddy’s website builder',
  webflow: 'Webflow',
  weebly: 'Weebly',
  duda: 'Duda',
  shopify: 'Shopify',
}

const HOSTED_BUILDERS = new Set(['wix', 'squarespace', 'godaddy', 'weebly', 'duda'])

function mb(kb: number) {
  return kb >= 1000 ? `${(kb / 1000).toFixed(1)} MB` : `${Math.round(kb)} KB`
}

/** The findings to show, most important first, capped at MAX_FINDINGS. */
export function teardownFindings(t: Teardown | null | undefined, currentYear: number): Finding[] {
  if (!t) return []
  const c = t.checks
  const out: Finding[] = []

  if (c.tapToCall === false) {
    out.push({
      id: 'tap-to-call',
      title: 'Your phone number isn’t tap-to-call',
      detail: 'On a phone, a customer has to copy the number out by hand to ring you.',
      fix: 'A call button that stays within thumb’s reach on every page.',
    })
  }
  if (c.contactForm === false) {
    out.push({
      id: 'contact-form',
      title: 'There’s no enquiry form on your homepage',
      detail: 'Someone who’d rather not ring has to go looking for a way to get in touch.',
      fix: 'A 30-second quote form that lands on your phone the moment it’s sent.',
    })
  }
  if (t.imageSavingsKb != null && t.imageSavingsKb >= 500) {
    out.push({
      id: 'images',
      title: `Images could be ${mb(t.imageSavingsKb)} lighter`,
      detail: 'Google’s test found that much could be saved on images alone — data every phone has to download first.',
      fix: 'Every image sized and compressed for the screen it’s shown on.',
    })
  }
  if (c.readableText === false) {
    out.push({
      id: 'text-size',
      title: 'Some text is too small to read on a phone',
      detail: 'Google’s mobile test flags it: visitors have to pinch and zoom to read it.',
      fix: 'Type set for a phone first, then scaled up for bigger screens.',
    })
  }
  if (c.tapTargets === false) {
    out.push({
      id: 'tap-targets',
      title: 'Buttons and links are too small or close together',
      detail: 'Google’s test flags them as hard to tap accurately with a thumb.',
      fix: 'Buttons sized and spaced for a thumb, not a mouse.',
    })
  }
  if (t.copyrightYear != null && t.copyrightYear < currentYear - 1) {
    out.push({
      id: 'copyright',
      title: `Your footer still says © ${t.copyrightYear}`,
      detail: 'Small, but visitors notice it, and it can make a busy business look quiet.',
      fix: 'Dates that keep themselves current.',
    })
  }
  if (c.localSchema === false) {
    out.push({
      id: 'local-schema',
      title: 'Google can’t read your business details',
      detail: 'There’s no structured information — trade, area, phone — for Google to use in local results.',
      fix: 'Local business details built into every page, the way Google asks for them.',
    })
  }
  if (c.metaDescription === false || c.pageTitle === false) {
    out.push({
      id: 'search-text',
      title:
        c.pageTitle === false ? 'Your homepage has no proper title for Google' : 'There’s no description for Google to show',
      detail: 'So Google writes its own snippet for your search listing, from whatever it finds on the page.',
      fix: 'A title and description written for the searches your customers actually make.',
    })
  }
  if (t.seoScore != null && t.seoScore < 80) {
    out.push({
      id: 'seo-score',
      title: `Google’s own SEO check scores it ${t.seoScore}/100`,
      detail: 'That’s Google’s basic checklist for how well a page can be found and understood.',
      fix: 'Built to pass Google’s checklist from the first line of code.',
    })
  }
  if (t.platform && HOSTED_BUILDERS.has(t.platform)) {
    out.push({
      id: 'platform',
      title: `It’s built on ${PLATFORM_NAMES[t.platform]}`,
      detail: 'A monthly subscription you don’t own — leave the platform and the site can’t come with you.',
      fix: 'Hand-coded, paid once, and yours outright: code and domain.',
    })
  } else if (t.platform === 'wordpress' && t.wpPluginCount != null && t.wpPluginCount >= 10) {
    // Counted from the plugin files the homepage itself loads - the total
    // installed can only be higher, so this undercounts rather than guesses.
    out.push({
      id: 'plugins',
      title: `Your homepage loads ${t.wpPluginCount} WordPress plugins`,
      detail: 'Each one is more code for a phone to load, and one more thing to keep updated.',
      fix: 'No plugins at all — nothing to update, nothing waiting to break.',
    })
  }
  if (c.whatsapp === false) {
    out.push({
      id: 'whatsapp',
      title: 'There’s no WhatsApp link',
      detail: 'Plenty of homeowners would rather send a photo of the job than make a call.',
      fix: 'One tap opens WhatsApp with a message already started.',
    })
  }
  if (c.secureAssets === false && c.https !== false) {
    out.push({
      id: 'insecure-files',
      title: 'Your homepage loads files over an insecure connection',
      detail:
        'It asks for some of its files over plain http://, which browsers block or rewrite on a secure page — so whatever they power may not work as intended.',
      fix: 'Every file served securely, and tested in a real browser before launch.',
    })
  }
  if (c.https === false) {
    out.push({
      id: 'https',
      title: 'Browsers show your site as “Not secure”',
      detail: 'The page isn’t served over HTTPS, and browsers label it that way next to the address.',
      fix: 'HTTPS on every page, as standard.',
    })
  }

  return out.slice(0, MAX_FINDINGS)
}

/** How many checks came back fine - shown alongside the findings, so it's a fair picture. */
export function teardownPasses(t: Teardown | null | undefined): number {
  if (!t) return 0
  return Object.values(t.checks).filter((v) => v === true).length
}
