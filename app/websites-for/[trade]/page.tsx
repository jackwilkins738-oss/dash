import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ArrowRight, Check } from 'lucide-react'
import { PageHeader, HeaderActions } from '@/components/page-header'
import { ExampleBuild } from '@/components/example-build'
import { ReplyClock } from '@/components/reply-clock'
import { Breadcrumbs } from '@/components/breadcrumbs'
import { Faq } from '@/components/faq'
import { JsonLd } from '@/components/json-ld'
import { CtaBand } from '@/components/cta-band'
import { Reveal } from '@/components/reveal'
import { TRADES, TRADE_BY_SLUG } from '@/lib/trades'
import { PRICES, SITE } from '@/lib/site'

type Props = { params: Promise<{ trade: string }> }

export const dynamicParams = false

export function generateStaticParams() {
  return TRADES.map((t) => ({ trade: t.slug }))
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { trade } = await params
  const t = TRADE_BY_SLUG[trade]
  if (!t) return {}
  return {
    title: t.metaTitle,
    description: t.metaDescription,
    alternates: { canonical: `/websites-for/${t.slug}` },
    openGraph: { title: `${t.metaTitle} | ${SITE.name}`, description: t.metaDescription, url: `/websites-for/${t.slug}`, type: 'website' },
  }
}

export default async function TradePage({ params }: Props) {
  const { trade } = await params
  const t = TRADE_BY_SLUG[trade]
  if (!t) notFound()
  const others = TRADES.filter((x) => x.slug !== t.slug)

  return (
    <main>
      <JsonLd
        data={{
          '@context': 'https://schema.org',
          '@type': 'Service',
          name: t.metaTitle,
          serviceType: `Website design for ${t.audience}`,
          description: t.metaDescription,
          url: `${SITE.url}/websites-for/${t.slug}`,
          areaServed: { '@type': 'Country', name: 'United Kingdom' },
          provider: { '@id': `${SITE.url}/#organization` },
          offers: [
            {
              '@type': 'Offer',
              name: 'Landing page',
              price: PRICES.landing,
              priceCurrency: 'GBP',
              description: 'One hand-coded, mobile-first landing page.',
            },
            {
              '@type': 'Offer',
              name: 'The Scalar build',
              price: PRICES.build,
              priceCurrency: 'GBP',
              description: 'Five hand-coded pages plus a private dashboard for enquiries, quotes, jobs and invoices.',
            },
          ],
        }}
      />
      <Breadcrumbs items={[{ name: 'Websites for trades', href: '/work' }, { name: t.label, href: `/websites-for/${t.slug}` }]} />
      <PageHeader
        compact
        eyebrow={t.eyebrow}
        title={t.h1}
        body={t.lede}
        actions={<HeaderActions secondary={{ href: '#work', label: 'See real builds' }} />}
      />

      <section className="py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <Reveal className="max-w-3xl">
            <p className="text-pretty text-lg leading-relaxed text-foreground/90">{t.intro}</p>
          </Reveal>

          <Reveal className="mt-14 max-w-2xl">
            <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">What it needs</span>
            <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl">
              What a website for {t.audience} has to do.
            </h2>
          </Reveal>

          <Reveal stagger className="mt-10 grid gap-5 md:grid-cols-2">
            {t.mustHave.map((m, i) => (
              <div
                key={m.title}
                data-spotlight
                className="rounded-2xl border border-border bg-card/40 p-7 transition-colors hover:border-blueprint/40"
              >
                <span className="font-mono text-sm text-blueprint">{String(i + 1).padStart(2, '0')}</span>
                <h3 className="mt-3 font-display text-xl font-semibold">{m.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{m.body}</p>
              </div>
            ))}
          </Reveal>
        </div>
      </section>

      {/* Proof, then what waiting costs, then the offer: the same order the
          homepage argues in, because a trade page is usually where a cold
          visitor lands first. */}
      <ExampleBuild />

      <section data-wire-section className="border-t border-border py-20 sm:py-24">
        <div className="mx-auto max-w-2xl px-5 text-center sm:px-8">
          <Reveal>
            <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">
              Whoever answers first
            </span>
            <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl">
              The job usually goes to the first firm that replies.
            </h2>
            <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
              Plenty of {t.audience} lose work they never hear about, simply by replying tomorrow instead of now.
              Pick how fast you usually get back to people.
            </p>
          </Reveal>
          <ReplyClock />
        </div>
      </section>

      <section className="border-t border-border py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="grid gap-10 lg:grid-cols-[1.2fr_1fr] lg:gap-16">
            <Reveal>
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">How I build it</span>
              <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl">
                Hand-coded, fast, and a fixed price.
              </h2>
              <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
                Every site is written from scratch: no page-builder, no theme, no plugins to break. You get a fixed price
                before any work starts, and you own the code and the domain outright.
              </p>
              <div className="mt-8 flex flex-col gap-3 sm:flex-row">
                <Link
                  href="/contact"
                  className="btn-chamfer group inline-flex items-center justify-center gap-2 bg-blueprint px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background"
                >
                  Start your build
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </Link>
                <Link
                  href="/work#pricing"
                  className="btn-chamfer inline-flex items-center justify-center border border-border px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-foreground transition-colors hover:border-blueprint hover:text-blueprint"
                >
                  See the prices
                </Link>
              </div>
            </Reveal>

            <Reveal delay={0.1}>
              <ul className="space-y-4">
                {[
                  `The full build £${PRICES.build.toLocaleString('en-GB')}, with a private dashboard`,
                  `Or a single landing page from £${PRICES.landing}`,
                  'Mobile-first and quick on a weak signal',
                  'WhatsApp, call and enquiry form built in',
                  'You own the code and domain outright',
                ].map((line) => (
                  <li key={line} className="flex items-start gap-3 text-sm text-foreground/90">
                    <Check className="mt-0.5 h-4 w-4 flex-none text-blueprint" strokeWidth={2.5} />
                    {line}
                  </li>
                ))}
              </ul>
            </Reveal>
          </div>
        </div>
      </section>

      <Faq items={t.faqs} title={`Questions from ${t.audience}`} />

      <section className="border-t border-border py-16 sm:py-20">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <h2 className="font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground">Also for other trades</h2>
          <ul className="mt-5 flex flex-wrap gap-3">
            {others.map((o) => (
              <li key={o.slug}>
                <Link
                  href={`/websites-for/${o.slug}`}
                  className="inline-flex items-center rounded-full border border-border px-4 py-2 text-sm text-foreground/80 transition-colors hover:border-blueprint hover:text-blueprint"
                >
                  {o.label}
                </Link>
              </li>
            ))}
            <li>
              <Link
                href="/guides/how-much-does-a-tradesman-website-cost"
                className="inline-flex items-center rounded-full border border-blueprint/40 px-4 py-2 text-sm text-blueprint transition-colors hover:bg-blueprint/10"
              >
                What does a tradesman&apos;s website cost?
              </Link>
            </li>
          </ul>
        </div>
      </section>

      <CtaBand />
    </main>
  )
}
