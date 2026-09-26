import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import { PageHeader, HeaderActions } from '@/components/page-header'
import { SiteShowcase } from '@/components/site-showcase'
import { SpeedCheck } from '@/components/speed-check'
import { Pricing } from '@/components/pricing'
import { CtaBand } from '@/components/cta-band'
import { Reveal } from '@/components/reveal'
import { PreviewBeacon } from '@/components/preview-beacon'
import { getProspect, type Prospect } from '@/lib/prospect-api'
import { showcaseIdForTradeText } from '@/lib/showcase'
import { teardownFindings, teardownPasses } from '@/lib/teardown'

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
  return [trade ? `a ${trade} firm` : 'a trade firm', p.area ? `in ${p.area}` : null].filter(Boolean).join(' ')
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
  const checkedOn = checkedAt
    ? new Intl.DateTimeFormat('en-GB', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'Europe/London' }).format(checkedAt)
    : null

  return (
    <main>
      <PreviewBeacon slug={p.slug} />
      <PageHeader
        eyebrow={`Prepared for ${p.business_name}`}
        title={slow ? `A faster, sharper website for ${p.business_name}.` : `A sharper website for ${p.business_name}.`}
        body={`A concept of a Scalar build for ${tradePhrase(p)}${
          p.website ? `, next to where ${p.website} stands on Google’s own speed test today` : ''
        }. Nothing to sign up for — have a look around.`}
        actions={<HeaderActions primaryHref={contactHref} secondary={{ href: '#preview', label: 'See the preview' }} />}
      />

      <section id="preview" className="scroll-mt-20 py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="grid items-center gap-12 xl:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
            <Reveal>
              {p.website && band && p.mobile_score != null ? (
                <div className="rounded-2xl border border-border bg-card/50 p-7 sm:p-9">
                  <p className="font-mono text-xs text-muted-foreground">{p.website} today</p>
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
              <SiteShowcase initialTrade={sceneId} firm={{ name: p.business_name, domain: p.website }} />
              <p className="mt-4 text-center text-xs text-muted-foreground">
                A concept of a Scalar build for {p.business_name} — an illustration, not your live site.
              </p>
            </div>
          </div>
        </div>
      </section>

      {findings.length > 0 && p.website && (
        <section className="border-t border-border py-20 sm:py-24">
          <div className="mx-auto max-w-4xl px-5 sm:px-8">
            <Reveal>
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">
                What we found
              </span>
              <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl">
                {findings.length === 1 ? 'One thing' : `${findings.length} things`} on {p.website} worth fixing.
              </h2>
              <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
                Checked on {checkedOn} with Google&apos;s own mobile test and a look at your public homepage
                {passes > 0 ? ` — ${passes} other check${passes === 1 ? '' : 's'} came back fine` : ''}. Each of these
                is something you can see for yourself.
              </p>
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

      {p.website && <SpeedCheck initialUrl={p.website} />}
      <Pricing />
      <CtaBand />
    </main>
  )
}
