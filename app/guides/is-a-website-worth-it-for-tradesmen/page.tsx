import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Breadcrumbs } from '@/components/breadcrumbs'
import { Faq, type QA } from '@/components/faq'
import { JsonLd } from '@/components/json-ld'
import { CtaBand } from '@/components/cta-band'
import { Reveal } from '@/components/reveal'
import { PaybackCalculator } from '@/components/payback-calculator'
import { SITE } from '@/lib/site'

const PATH = '/guides/is-a-website-worth-it-for-tradesmen'
const PUBLISHED = '2026-10-02'
const TITLE = 'Is a Website Worth It for a Tradesman? Work It Out With Your Own Numbers'
const DESCRIPTION =
  'Whether a website pays for itself depends on one sum: the profit on a typical job against what the site costs. Put your own numbers in and see how many jobs it takes.'

export const metadata: Metadata = {
  title: 'Is a Website Worth It for a Tradesman?',
  description: DESCRIPTION,
  alternates: { canonical: PATH },
  openGraph: { title: `${TITLE} | ${SITE.name}`, description: DESCRIPTION, url: PATH, type: 'article' },
}

const FAQS: QA[] = [
  {
    q: 'How many jobs does a website bring a tradesman?',
    a: 'Nobody can honestly give you a number. It depends on your trade, your area, how many competitors there are, your reviews and how quickly you reply to enquiries. That is why the calculator asks you rather than assuming: start with a cautious guess, even one or two jobs a year, and see whether the sum still works.',
  },
  {
    q: 'Should I count turnover or profit?',
    a: 'Profit. A £4,000 job where £3,000 goes on materials and labour leaves £1,000, and that is what pays for the site. Using turnover makes any website look like a bargain, which is how people end up disappointed.',
  },
  {
    q: 'What if most of my work already comes from word of mouth?',
    a: 'A website still earns its keep there: most people recommended to you look you up before they ring. A slow site, an old site or no site at all loses some of those referrals quietly - you never hear about the ones who called someone else.',
  },
  {
    q: 'Is a cheaper website better value?',
    a: 'Only if it does the same job. The cost that matters is the price divided by the jobs it brings: a cheap site that is slow on a phone or hard to find on Google can cost more per job than a better one. Run both prices through the calculator with the jobs you honestly expect from each.',
  },
]

export default function WorthItGuidePage() {
  return (
    <main>
      <JsonLd
        data={{
          '@context': 'https://schema.org',
          '@type': 'Article',
          headline: TITLE,
          description: DESCRIPTION,
          datePublished: PUBLISHED,
          dateModified: PUBLISHED,
          inLanguage: 'en-GB',
          mainEntityOfPage: `${SITE.url}${PATH}`,
          author: { '@type': 'Organization', name: SITE.name, url: SITE.url },
          publisher: { '@id': `${SITE.url}/#organization` },
        }}
      />
      <Breadcrumbs items={[{ name: 'Guides', href: '/guides' }, { name: 'Is a website worth it?', href: PATH }]} />
      <PageHeader
        compact
        eyebrow="Guide"
        title="Is a website worth it for a tradesman?"
        body="It comes down to one sum: the profit on a typical job against what the site costs. Here it is, with your own numbers."
      />

      <article className="py-20 sm:py-24">
        <div className="mx-auto max-w-4xl px-5 sm:px-8">
          <Reveal>
            <div className="rounded-2xl border border-blueprint/40 bg-card p-7">
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">The short answer</span>
              <p className="mt-3 text-pretty leading-relaxed text-foreground/90">
                For most trades, yes - and usually after very few jobs, because trade jobs are big. If a typical job
                leaves you £750 or more in profit, a one-off website pays for itself after a handful of extra jobs, and
                everything after that is yours. If your jobs are small and your diary is already full from word of
                mouth, it matters less. Work it out below rather than taking anyone&apos;s word for it, including mine.
              </p>
            </div>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">Put your own numbers in</h2>
            <p className="mt-4 max-w-2xl text-pretty leading-relaxed text-muted-foreground">
              Use profit, not the price of the job, and be cautious about how many extra jobs you expect. The sum only
              helps if it&apos;s honest.
            </p>
          </Reveal>
          <PaybackCalculator />

          <div className="mx-auto max-w-3xl">
            <Reveal className="mt-14">
              <h2 className="font-display text-balance text-3xl font-bold tracking-tight">What the sum leaves out</h2>
              <ul className="mt-6 space-y-4 text-pretty leading-relaxed text-muted-foreground">
                <li>
                  <strong className="text-foreground">Better-paid work, not just more of it.</strong> A site that looks like a
                  firm worth paying properly for changes which jobs you are asked to quote, not only how many.
                </li>
                <li>
                  <strong className="text-foreground">Referrals you would otherwise lose.</strong> People recommended to you
                  check you out first. The ones who found nothing convincing never tell you they went elsewhere.
                </li>
                <li>
                  <strong className="text-foreground">Time.</strong> Answering &ldquo;do you cover my area?&rdquo; and
                  &ldquo;can I see your work?&rdquo; on the phone, again and again, is time a good site saves.
                </li>
              </ul>
            </Reveal>

            <Reveal className="mt-14">
              <h2 className="font-display text-balance text-3xl font-bold tracking-tight">When it genuinely isn&apos;t worth it</h2>
              <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
                If you are booked solid for months from repeat customers and word of mouth, and you have no wish to grow
                or move up to better-paid work, a website will not change much for you yet. Keep your Google Business
                Profile up to date (our{' '}
                <Link href="/guides/google-business-profile-for-tradesmen" className="text-blueprint underline underline-offset-4">
                  guide
                </Link>{' '}
                covers it) and revisit the sum when that changes.
              </p>
            </Reveal>

            <Reveal className="mt-14 rounded-2xl border border-border bg-card/40 p-7">
              <h2 className="font-display text-2xl font-bold tracking-tight">Next: what would it cost you?</h2>
              <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
                The price is fixed and agreed before any work starts, and you own the site outright.
              </p>
              <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
                <Link
                  href="/guides/how-much-does-a-tradesman-website-cost"
                  className="group inline-flex items-center gap-2 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-blueprint transition-colors hover:text-brass"
                >
                  What a website costs
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </Link>
                <Link
                  href="/work#pricing"
                  className="font-mono text-sm uppercase tracking-[0.15em] text-muted-foreground transition-colors hover:text-blueprint"
                >
                  See what&apos;s included
                </Link>
              </div>
            </Reveal>
          </div>
        </div>
      </article>

      <Faq items={FAQS} title="More questions on whether a website pays" />
      <CtaBand />
    </main>
  )
}
