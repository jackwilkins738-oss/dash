import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { PageHeader, HeaderActions } from '@/components/page-header'
import { SiteShowcase } from '@/components/site-showcase'
import { SpeedCheck } from '@/components/speed-check'
import { StartQuote } from '@/components/start-quote'
import { CtaBand } from '@/components/cta-band'
import { BookCallBand } from '@/components/book-call'
import { Reveal } from '@/components/reveal'
import { PreviewBeacon } from '@/components/preview-beacon'
import { PreviewRace } from '@/components/preview-race'
import { MIN_RACE_GAP_MS, SCALAR_BUILD } from '@/lib/speedRace'
import { getProspect, type Prospect } from '@/lib/prospect-api'
import { SHOWCASE_TRADES, showcaseIdForTradeText } from '@/lib/showcase'
import { teardownFindings, teardownPasses, usableFrames } from '@/lib/teardown'
import { PrintButton } from '@/components/print-button'
import { PreviewOptOut } from '@/components/preview-optout'
import { FoundingOffer } from '@/components/founding-offer'
import { Founder } from '@/components/founder'
import { PreviewVideo } from '@/components/preview-video'
import { QuickReply } from '@/components/quick-reply'
import { LoadFilmstrip } from '@/components/load-filmstrip'
import { PRICES } from '@/lib/site'
import { reviewsView, rivalsView, stars, videoSrc } from '@/lib/preview-extras'
import { SITE } from '@/lib/site'

// A private page for one business Scalar is reaching out to: their real
// Google speed score next to a concept of what a Scalar build would look
// like for them, with their name on it. Linked only from the email or
// letter sent to them; the slug carries a hash, the page is noindex, and
// the data comes from the dashboard, not this (public) repo — see
// lib/prospect-api.ts.
//
// Every figure on the page is theirs and measured, or a band Google itself
// publishes. Nothing here claims a result for them.

type Props = { params: Promise<{ slug: string }> }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const p = await getProspect(slug)
  return {
    title: p ? `Prepared for ${p.business_name}` : 'Preview',
    description: p ? `A concept website for ${p.business_name}, and where its current site stands on Google's speed test.` : undefined,
    robots: { index: false, follow: false, googleBot: { index: false, follow: false } },
    alternates: { canonical: `/for/${slug}` },
  }
}

// Google's own published bands: PageSpeed Insights performance score
// (90-100 good, 50-89 needs improvement, 0-49 poor) and Largest Contentful
// Paint (2.5s or less good, over 4s poor).
function scoreBand(score: number) {
  if (score >= 90) return { label: 'Good', note: 'Google’s band for 90–100', tone: 'text-emerald-400' }
  if (score >= 50) return { label: 'Needs improvement', note: 'Google’s band for 50–89', tone: 'text-amber-300' }
  return { label: 'Poor', note: 'Google’s band for 0–49', tone: 'text-destructive' }
}

function lcpNote(lcp: number) {
  if (lcp > 4) return 'Google counts anything over 4 seconds as poor.'
  if (lcp > 2.5) return 'Google counts 2.5 seconds or less as good; this is above it.'
  return 'Inside Google’s 2.5-second “good” line.'
}

function tradePhrase(p: Prospect) {
  const trade = p.trade?.toLowerCase()
  const article = trade && /^[aeiou]/.test(trade) ? 'an' : 'a'
  return [trade ? `${article} ${trade} firm` : 'a trade firm', p.area ? `in ${p.area}` : null].filter(Boolean).join(' ')
}

export default async function ProspectPreviewPage({ params }: Props) {
  const { slug } = await params
  const p = await getProspect(slug)
  if (!p) notFound()

  const sceneId = showcaseIdForTradeText(p.trade) ?? undefined
  const contactHref = `/contact?firm=${encodeURIComponent(p.business_name)}`
  const band = p.mobile_score != null ? scoreBand(p.mobile_score) : null
  const slow = p.mobile_score != null && p.mobile_score < 90

  // The teardown is judged against the year it was run, not today, so a
  // finding like a stale copyright year can't change meaning as time passes.
  const checkedAt = p.teardown_at ? new Date(p.teardown_at) : null
  const findings = checkedAt ? teardownFindings(p.teardown, checkedAt.getUTCFullYear()) : []
  const passes = teardownPasses(p.teardown)
  const frames = slow ? usableFrames(p.teardown?.frames) : []

  // The personal race only renders on measured figures, and only when it's a
  // clear win: a Scalar build that's been measured, their LCP known, and at
  // least MIN_RACE_GAP_MS slower. Otherwise the section simply isn't there.
  const theirLcpMs = p.lcp_s != null ? Math.round(p.lcp_s * 1000) : null
  const scene = SHOWCASE_TRADES.find((t) => t.id === sceneId)
  const raceCopy = scene ? { eyebrow: scene.eyebrow, headline: scene.headline, cta: scene.cta } : undefined
  const showRace =
    SCALAR_BUILD.lcpMs != null && theirLcpMs != null && p.website != null && theirLcpMs - SCALAR_BUILD.lcpMs >= MIN_RACE_GAP_MS
  // Their Google reviews and the local firms they're up against - each only when it's real and it helps.
  const reviews = reviewsView(p.teardown)
  const rivals = rivalsView(p.teardown, p.mobile_score, p.business_name)
  // Their measured score and findings show even if the dashboard lost the web address - "your website" stands in.
  const siteName = p.website ?? 'your website'
  const video = videoSrc(p.video_url)
  const checkedOn = checkedAt
    ? new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Europe/London' }).format(checkedAt)
    : null

  return (
    <main>
      <PreviewBeacon slug={p.slug} />
      {/* On paper only: whose report this is, and where the live version lives. */}
      <div data-print="only" className="border-b border-border px-5 pb-3 pt-1 text-xs text-muted-foreground">
        <strong className="text-foreground">{SITE.name}</strong> · Prepared for {p.business_name} ·{' '}
        {SITE.url.replace('https://', '')}/for/{p.slug}
      </div>
      <PageHeader
        eyebrow={`Prepared for ${p.business_name}`}
        title={slow ? `A faster, sharper website for ${p.business_name}.` : `A sharper website for ${p.business_name}.`}
        body={`A concept of a Scalar build for ${tradePhrase(p)}${
          p.website ? `, next to where ${p.website} stands on Google’s own speed test today` : ''
        }. Nothing to sign up for — have a look around.`}
        actions={
          <HeaderActions
            primaryHref={contactHref}
            secondary={video ? { href: '#video', label: 'Watch my walkthrough' } : { href: '#preview', label: 'See the preview' }}
          />
        }
      />
      {video && <PreviewVideo src={video} firmName={p.business_name} />}

      <section id="preview" className="scroll-mt-20 py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="grid items-center gap-12 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <Reveal>
              {band && p.mobile_score != null ? (
                <div className="rounded-2xl border border-border bg-card/50 p-7 sm:p-9">
                  <p className="font-mono text-xs text-muted-foreground">{p.website ?? 'Your website'} today</p>
                  <div className="mt-5 flex items-end gap-3">
                    <span className={`font-mono text-6xl font-bold tabular-nums ${band.tone}`}>{p.mobile_score}</span>
                    <span className="mb-2 font-mono text-sm text-muted-foreground">/ 100 on mobile</span>
                  </div>
                  <p className="mt-2 text-sm">
                    <span className="font-semibold text-foreground">{band.label}</span>{' '}
                    <span className="text-muted-foreground">&middot; {band.note}</span>
                  </p>
                  {p.lcp_s != null && (
                    <p className="mt-5 border-t border-border pt-5 text-sm leading-relaxed text-muted-foreground">
                      <span className="font-semibold text-foreground">{p.lcp_s.toFixed(1)}s</span> before the main
                      content appears on a phone. {lcpNote(p.lcp_s)}
                    </p>
                  )}
                  <p className="mt-5 border-t border-border pt-5 text-sm leading-relaxed text-foreground/90">
                    A Scalar build is made for <span className="font-semibold text-blueprint">90+</span> on the same
                    test — and founding clients get that in writing.
                  </p>
                  <p className="mt-4 font-mono text-[10px] uppercase leading-relaxed tracking-[0.12em] text-muted-foreground/70">
                    Measured with Google PageSpeed Insights (mobile) when this page was prepared. Scores move a little
                    from run to run — re-run it yourself below.
                  </p>
                </div>
              ) : (
                <div className="rounded-2xl border border-border bg-card/50 p-7 sm:p-9">
                  <p className="font-display text-2xl font-semibold">Built to win the jobs worth having.</p>
                  <p className="mt-4 leading-relaxed text-muted-foreground">
                    Hand-coded from a blank page for {p.business_name}: fast on a phone, clear about what you do and
                    where, and wired so every enquiry reaches you the moment it lands.
                  </p>
                </div>
              )}
            </Reveal>

            <div>
              <SiteShowcase
                initialTrade={sceneId}
                firm={{
                  name: p.business_name,
                  domain: p.website,
                  services: p.teardown?.services,
                  accent: p.teardown?.brandColour,
                }}
              />
              <p className="mt-4 text-center text-xs text-muted-foreground">
                A concept of a Scalar build for {p.business_name} — an illustration, not your live site.
              </p>
            </div>
          </div>
        </div>
      </section>

      {(rivals || reviews) && (
        <section id="google" className="scroll-mt-20 border-t border-border py-20 sm:py-24">
          <div className="mx-auto max-w-6xl px-5 sm:px-8">
            <Reveal>
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">You on Google</span>
              <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl">
                {rivals
                  ? `${rivals.ahead === 1 ? 'One firm' : `${rivals.ahead} firms`} near the top of Google Maps ${rivals.ahead === 1 ? 'loads' : 'load'} faster than you.`
                  : 'Your reviews are doing half the job.'}
              </h2>
            </Reveal>
            <div className={`mt-10 grid gap-6 ${rivals && reviews ? 'lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]' : ''}`}>
              {rivals && (
                <Reveal className="rounded-2xl border border-border bg-card/50 p-7 sm:p-9">
                  <p className="text-sm text-muted-foreground">
                    Top results on Google Maps for <span className="font-semibold text-foreground">&ldquo;{rivals.query}&rdquo;</span>
                    {rivals.position ? (
                      <>
                        {' '}
                        - you came <span className="font-semibold text-foreground">#{rivals.position}</span>
                      </>
                    ) : null}
                    . Google&apos;s mobile speed score for each:
                  </p>
                  <ul className="mt-6 space-y-4">
                    {rivals.rows.map((r) => (
                      <li key={`${r.name}-${r.you ? 'you' : 'them'}`}>
                        <div className="flex items-baseline justify-between gap-4 text-sm">
                          <span className={r.you ? 'font-semibold text-foreground' : 'text-muted-foreground'}>
                            {r.you ? `${r.name} (you)` : r.name}
                          </span>
                          <span className={`font-mono tabular-nums ${r.you ? 'font-bold text-foreground' : 'text-muted-foreground'}`}>
                            {r.score}
                          </span>
                        </div>
                        <div className="mt-1.5 h-2 rounded-full bg-border/60" aria-hidden="true">
                          <div
                            className={`h-2 rounded-full ${r.you ? 'bg-brass' : 'bg-blueprint/60'}`}
                            style={{ width: `${Math.max(r.score, 3)}%` }}
                          />
                        </div>
                      </li>
                    ))}
                  </ul>
                  <p className="mt-6 border-t border-border pt-5 text-sm leading-relaxed text-foreground/90">
                    When someone nearby searches on their phone, the firms whose sites load first get the first look.
                    A Scalar build is made for <span className="font-semibold text-blueprint">90+</span>.
                  </p>
                  <p className="mt-4 font-mono text-[10px] uppercase leading-relaxed tracking-[0.12em] text-muted-foreground/70">
                    Measured with Google PageSpeed Insights (mobile)
                    {rivals.checkedAt
                      ? ` in ${new Intl.DateTimeFormat('en-GB', { month: 'long', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${rivals.checkedAt}T12:00:00Z`))}`
                      : ''}
                    .
                    Scores move a little from run to run.
                  </p>
                </Reveal>
              )}
              {reviews && (
                <Reveal className="rounded-2xl border border-border bg-card/50 p-7 sm:p-9">
                  <p className="font-mono text-2xl tracking-[0.15em] text-brass" aria-hidden="true">
                    {stars(reviews.rating)}
                  </p>
                  <p className="mt-3 font-display text-3xl font-bold">
                    {reviews.rating.toFixed(1)}{' '}
                    <span className="text-lg font-semibold text-muted-foreground">
                      from {reviews.reviews.toLocaleString('en-GB')} Google reviews
                    </span>
                  </p>
                  <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
                    {reviews.shownOnSite === false
                      ? `That's the strongest thing ${p.business_name} has - and your homepage doesn't show any of it. Most people check reviews before they ring.`
                      : `That's the strongest thing ${p.business_name} has, and most people check reviews before they ring.`}
                  </p>
                  <p className="mt-4 text-sm text-foreground/90">
                    <span className="font-semibold">In a Scalar build:</span> your rating and your best reviews sit on
                    every page, right next to the call button.
                  </p>
                </Reveal>
              )}
            </div>
          </div>
        </section>
      )}

      {frames.length > 0 && p.website && (
        <section id="loading" className="scroll-mt-20 border-t border-border py-20 sm:py-24">
          <div className="mx-auto max-w-4xl px-5 sm:px-8">
            <Reveal className="text-center">
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">What a customer sees</span>
              <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl">
                {p.website}, loading on a phone.
              </h2>
              <p className="mx-auto mt-5 max-w-2xl text-pretty leading-relaxed text-muted-foreground">
                Three moments from Google&apos;s own mobile test{checkedOn ? ` on ${checkedOn}` : ''}. Someone searching for{' '}
                {p.trade ? `a ${p.trade.toLowerCase()}` : 'a tradesman'} on their phone is looking at this while they decide
                whether to wait or try the next result.
              </p>
            </Reveal>
            <Reveal className="mt-10">
              <LoadFilmstrip frames={frames} domain={p.website} />
            </Reveal>
          </div>
        </section>
      )}

      <section id="reply" className="scroll-mt-20 border-t border-border py-16 sm:py-20">
        <div className="mx-auto max-w-3xl px-5 sm:px-8">
          <QuickReply slug={p.slug} firmName={p.business_name} />
        </div>
      </section>

      {showRace && (
        <PreviewRace
          firmName={p.business_name}
          website={p.website!}
          theirLcpMs={theirLcpMs!}
          scalarLcpMs={SCALAR_BUILD.lcpMs!}
          scalarPage={SCALAR_BUILD.page}
          scalarMeasuredOn={SCALAR_BUILD.measuredOn}
          copy={raceCopy}
        />
      )}

      {findings.length > 0 && (
        <section id="findings" className="scroll-mt-20 border-t border-border py-20 sm:py-24">
          <div className="mx-auto max-w-4xl px-5 sm:px-8">
            <Reveal>
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">
                What we found
              </span>
              <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl">
                {findings.length === 1 ? 'One thing' : `${findings.length} things`} on {siteName} worth fixing.
              </h2>
              <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
                Checked on {checkedOn} with Google&apos;s own mobile test and a look at your public homepage
                {passes > 0 ? ` — ${passes} other check${passes === 1 ? '' : 's'} came back fine` : ''}. Each of these
                is something you can see for yourself.
              </p>
              <PrintButton className="mt-4" />
            </Reveal>

            <Reveal stagger className="mt-10 divide-y divide-border border-y border-border">
              {findings.map((f, i) => (
                <div key={f.id} className="grid gap-3 py-7 sm:grid-cols-[3rem_1fr] sm:gap-6">
                  <span className="font-mono text-sm text-blueprint">{String(i + 1).padStart(2, '0')}</span>
                  <div>
                    <h3 className="font-display text-lg font-semibold sm:text-xl">{f.title}</h3>
                    <p className="mt-2 text-pretty leading-relaxed text-muted-foreground">{f.detail}</p>
                    <p className="mt-3 flex items-start gap-2 text-sm text-foreground/90">
                      <span className="mt-0.5 font-mono text-blueprint" aria-hidden="true">
                        &rarr;
                      </span>
                      <span>
                        <span className="font-semibold">In a Scalar build:</span> {f.fix}
                      </span>
                    </p>
                  </div>
                </div>
              ))}
            </Reveal>
          </div>
        </section>
      )}

      {/* Ready to go ahead: the package picked, so the reply is a quote, not a question. */}
      <section id="pricing" className="scroll-mt-20 border-t border-border py-16 sm:py-20">
        <div className="mx-auto max-w-4xl px-5 sm:px-8">
          <Reveal>
            <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Next step</span>
            <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl">
              Want this for {p.business_name}?
            </h2>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              Pick one and your fixed-price quote opens straight away - accept it online whenever you&apos;re ready.
              Nothing is charged until you&apos;ve read it and said yes.
            </p>
            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              <StartQuote
                slug={slug}
                pkg="build"
                businessName={p.business_name}
                className="group rounded-2xl border border-blueprint/50 bg-card p-6 transition-colors hover:border-blueprint"
              >
                <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-blueprint">The Scalar build</span>
                <span className="mt-2 block font-display text-3xl font-bold">£{PRICES.build.toLocaleString('en-GB')}</span>
                <span className="mt-2 block text-sm text-muted-foreground">
                  Five pages plus your own dashboard for enquiries, quotes and invoices.
                </span>
                <span className="mt-4 inline-block font-semibold text-blueprint">See my quote &rarr;</span>
              </StartQuote>
              <StartQuote
                slug={slug}
                pkg="landing"
                businessName={p.business_name}
                className="group rounded-2xl border border-border bg-card/50 p-6 transition-colors hover:border-blueprint"
              >
                <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Landing page</span>
                <span className="mt-2 block font-display text-3xl font-bold">£{PRICES.landing.toLocaleString('en-GB')}</span>
                <span className="mt-2 block text-sm text-muted-foreground">One fast page, built to turn visitors into enquiries.</span>
                <span className="mt-4 inline-block font-semibold text-blueprint">See my quote &rarr;</span>
              </StartQuote>
            </div>
          </Reveal>
          <Reveal className="mt-6">
            <FoundingOffer href={`${contactHref}&founding=1`} />
          </Reveal>
          <Reveal className="mt-12">
            <h3 className="font-display text-2xl font-bold tracking-tight">What happens next</h3>
            <ol className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ['A short call', 'Fifteen minutes on what work you want more of. If it isn’t a fit, I’ll say so.'],
                ['A fixed price in writing', 'Within 2 hours of the call. It doesn’t move once we start.'],
                ['One page of details', 'Your services, areas and some photos of your work. I write the rest.'],
                ['You check it on your phone', 'Nothing goes live until you’ve seen it and said yes. Then it’s yours outright.'],
              ].map(([title, body], i) => (
                <li key={title} className="rounded-2xl border border-border bg-card/50 p-5">
                  <span className="font-mono text-xs text-blueprint">0{i + 1}</span>
                  <span className="mt-2 block font-semibold">{title}</span>
                  <span className="mt-1.5 block text-sm leading-relaxed text-muted-foreground">{body}</span>
                </li>
              ))}
            </ol>
          </Reveal>
          <dl className="mt-12 divide-y divide-border border-y border-border">
            {[
              ['Is the price fixed?', `Yes. £${PRICES.landing.toLocaleString('en-GB')} or £${PRICES.build.toLocaleString('en-GB')}, agreed before anything starts, and it doesn't move. No monthly fee on the website itself.`],
              ['Do I own it?', 'Yes - the code and the domain are yours outright once it’s paid for. No being locked to me to make a change.'],
              ['What do I have to do?', 'A short call, then one page of details and some photos of your work. You check the whole site on your phone before anything goes live.'],
              ['Will my email keep working?', 'Yes. Your email settings are checked and carried over before your domain is pointed at the new site, and your current site stays up until then.'],
              ['What about the dashboard?', `It comes with The Scalar build, free for the first 12 months, then £${PRICES.dashboardMonthly} a month only if you want to keep it. The website works without it.`],
            ].map(([q, a]) => (
              <div key={q} className="py-5">
                <dt className="font-semibold">{q}</dt>
                <dd className="mt-1.5 text-pretty leading-relaxed text-muted-foreground">{a}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-8">
            <PreviewOptOut slug={p.slug} firmName={p.business_name} />
          </div>
        </div>
      </section>

      <Founder />
      <BookCallBand contactHref={contactHref} firmName={p.business_name} />
      {p.website && <SpeedCheck initialUrl={p.website} />}
      <CtaBand />
      <div data-print="only" className="border-t border-border px-5 py-6 text-sm">
        <p className="font-semibold">Questions, or want to go ahead?</p>
        <p className="mt-1 text-muted-foreground">
          {SITE.email} · {SITE.phone.replace('+44', '0').replace(/^(\d{5})(\d+)$/, '$1 $2')} · {SITE.url.replace('https://', '')}
        </p>
      </div>
    </main>
  )
}
