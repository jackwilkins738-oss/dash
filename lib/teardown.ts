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
      | 'secureAssets'
      | 'showsReviews'
      | 'phoneShown'
      | 'mobileViewport'
      | 'indexable'
      | 'imageAlt'
      | 'businessEmail',
      boolean
    >
  >
  seoScore?: number
  accessibilityScore?: number
  /** 2-3 service names from their own homepage (validated by the dashboard). */
  services?: string[]
  /** Their brand colour, #rrggbb, already dark enough for white text. */
  brandColour?: string
  /** Their logo and up to 4 photos from their own homepage - https jpg/png/webp, checked by the dashboard.
   *  No longer shown on the preview (its "rebuilt" section was removed); kept as data only. */
  logo?: string
  photos?: string[]
  /** Slow sites only: 3 frames of their homepage loading in Google's mobile test (ms from the start,
   *  small JPEG data URIs checked by the dashboard), and how it looks once loaded. Gone after 45 days. */
  frames?: Frame[]
  screenshot?: string
  imageSavingsKb?: number
  pageWeightKb?: number
  /** How long their server took to start answering Google's test, in ms. */
  serverResponseMs?: number
  /** How much the page jumps about while loading (Google's layout shift, x100). */
  layoutShift100?: number
  copyrightYear?: number
  platform?: 'wordpress' | 'wix' | 'squarespace' | 'godaddy' | 'webflow' | 'weebly' | 'duda' | 'shopify'
  wpPluginCount?: number
  /** Their Google rating (checked by the dashboard: 1-5, from a result whose website is theirs). */
  google?: { rating: number; reviews: number }
  /** Top firms on Google Maps for their trade and town, each with Google's mobile score (2-3 of them). */
  rivals?: { query: string; position?: number; checkedAt?: string; items: { name: string; score: number }[] }
}

export type Frame = { t: number; img: string }

const DATA_JPEG = /^data:image\/jpeg;base64,[A-Za-z0-9+/]+={0,2}$/

/** Only an inline base64 JPEG ever reaches an <img> on the page - checked again here, not just by the dashboard. */
export function isDataJpeg(value: unknown): value is string {
  return typeof value === 'string' && value.length <= 40_000 && DATA_JPEG.test(value)
}

/** The three filmstrip frames, or none: a partial or out-of-order strip would tell the wrong story. */
export function usableFrames(frames: unknown): Frame[] {
  if (!Array.isArray(frames) || frames.length !== 3) return []
  const ok = frames.every(
    (f, i) =>
      f && typeof f === 'object' && Number.isFinite(f.t) && f.t >= 0 && isDataJpeg(f.img) && (i === 0 || f.t >= frames[i - 1].t),
  )
  return ok ? (frames as Frame[]) : []
}

export type Finding = { id: string; title: string; detail: string; fix: string }

export const MAX_FINDINGS = 6

// The same thresholds as scripts/findings.py: a homepage over 4 MB, a server slower than 1.8s to
// answer (Google's target is 0.6s), and layout shift past Google's "poor" line (0.25).
export const HEAVY_PAGE_KB = 4000
export const SLOW_SERVER_MS = 1800
export const JUMPY_PAGE = 25

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

  if (c.indexable === false) {
    out.push({
      id: 'noindex',
      title: 'Your homepage tells Google not to list it',
      detail: 'There’s a “noindex” instruction in the page, so Google leaves it out of search results altogether.',
      fix: 'Every page built to be found, checked before launch.',
    })
  }
  if (c.mobileViewport === false) {
    out.push({
      id: 'not-mobile',
      title: 'Your site isn’t set up for phones',
      detail: 'A phone shows the desktop page shrunk down, so visitors have to pinch and zoom to read anything.',
      fix: 'Designed for a phone first, then scaled up for bigger screens.',
    })
  }
  if (c.phoneShown === false) {
    out.push({
      id: 'no-phone',
      title: 'There’s no phone number on your homepage',
      detail: 'Someone ready to ring you has to go looking for how to get in touch.',
      fix: 'Your number on every page, with a call button within thumb’s reach.',
    })
  } else if (c.tapToCall === false) {
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
  // The Google reviews block on the preview already makes this point when there's a rating to show.
  if (c.showsReviews === false && !t.google) {
    out.push({
      id: 'no-reviews',
      title: 'Your homepage doesn’t show any reviews',
      detail: 'Most people check reviews before they ring, and they’ll go looking elsewhere for them.',
      fix: 'Your best reviews next to the call button on every page.',
    })
  }
  if (t.pageWeightKb != null && t.pageWeightKb >= HEAVY_PAGE_KB) {
    out.push({
      id: 'page-weight',
      title: `Your homepage is ${mb(t.pageWeightKb)} to download`,
      detail: 'Google’s test measured it — every visitor on a phone downloads all of it before they can use the page.',
      fix: 'A homepage a fraction of that size, with every image sized for the screen.',
    })
  } else if (t.imageSavingsKb != null && t.imageSavingsKb >= 500) {
    out.push({
      id: 'images',
      title: `Images could be ${mb(t.imageSavingsKb)} lighter`,
      detail: 'Google’s test found that much could be saved on images alone — data every phone has to download first.',
      fix: 'Every image sized and compressed for the screen it’s shown on.',
    })
  }
  if (t.serverResponseMs != null && t.serverResponseMs >= SLOW_SERVER_MS) {
    out.push({
      id: 'slow-server',
      title: `Your server takes ${(t.serverResponseMs / 1000).toFixed(1)}s to start answering`,
      detail: 'That’s before the page even begins to load — Google’s target is under 0.6s. Usually a sign of slow hosting.',
      fix: 'Served from a global network, so the page starts arriving straight away.',
    })
  }
  if (t.layoutShift100 != null && t.layoutShift100 >= JUMPY_PAGE) {
    out.push({
      id: 'layout-shift',
      title: 'The page jumps about while it loads',
      detail: 'Text and buttons move as things load in, so it’s easy to tap the wrong thing — Google rates it “poor”.',
      fix: 'Everything has its space reserved, so nothing moves.',
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
  if (c.imageAlt === false) {
    out.push({
      id: 'image-alt',
      title: 'Your photos have no descriptions',
      detail: 'Google can’t see a photo — without a short description it can’t tell what work it shows, or show it in image search.',
      fix: 'Every photo described: the job, the material, the place.',
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
  if (c.businessEmail === false) {
    out.push({
      id: 'free-email',
      title: 'Your email is a Gmail/Hotmail-style address',
      detail: 'An address at your own web address looks more established, and comes free with your domain.',
      fix: 'Email at your own domain, set up with the site.',
    })
  }
  if (c.localSchema === false) {
    out.push({
      id: 'local-schema',
      title: 'Google can’t read your trade and area from your site',
      detail: 'Your site doesn’t give Google your trade, area and phone in the format it reads for local results.',
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
