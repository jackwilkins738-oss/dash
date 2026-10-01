import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Breadcrumbs } from '@/components/breadcrumbs'
import { Faq, type QA } from '@/components/faq'
import { JsonLd } from '@/components/json-ld'
import { CtaBand } from '@/components/cta-band'
import { Reveal } from '@/components/reveal'
import { SITE } from '@/lib/site'

const PATH = '/guides/wix-or-hand-coded-website-for-tradesmen'
const PUBLISHED = '2026-10-01'
const TITLE = 'Wix, Squarespace or a Hand-Coded Website? An Honest Guide for Tradespeople'
const DESCRIPTION =
  'Website builders like Wix, Squarespace and GoDaddy against a hand-coded site for a trade business - cost, speed on a phone, who owns it, and when a DIY builder is genuinely the right call.'

export const metadata: Metadata = {
  title: 'Wix vs Hand-Coded Website for Tradesmen',
  description: DESCRIPTION,
  alternates: { canonical: PATH },
  openGraph: { title: `${TITLE} | ${SITE.name}`, description: DESCRIPTION, url: PATH, type: 'article' },
}

// No builder prices quoted: plans change often and differ by tier. The guides/cost page carries the
// broad ranges; this one is about the trade-offs.
const COMPARISON = [
  {
    aspect: 'Who builds it',
    builder: 'You, from a template, in the evenings - or someone you pay to set the template up.',
    coded: 'Someone who does it for a living, built around your services and the areas you cover.',
  },
  {
    aspect: 'How you pay',
    builder: 'A monthly or yearly subscription for as long as the site is live.',
    coded: 'Usually a one-off build. Hosting for a simple site can cost little or nothing.',
  },
  {
    aspect: 'Speed on a phone',
    builder: 'Varies. Templates carry code for features you never use, so many builder sites are slower than they look on a desktop.',
    coded: 'Only the code the page needs, so it is usually fast - test any site yourself with Google’s free speed test.',
  },
  {
    aspect: 'Who owns it',
    builder: 'You own your words and photos, but the site lives on the builder’s platform. Moving usually means rebuilding.',
    coded: 'The code and the domain can be yours outright, and moved to any host.',
  },
  {
    aspect: 'Looking different from the next firm',
    builder: 'Many trade sites start from the same handful of templates.',
    coded: 'Designed around your business, so it does not look like everyone else’s.',
  },
  {
    aspect: 'Making changes',
    builder: 'Easy to edit yourself whenever you like.',
    coded: 'Usually done for you; simple edits can be built in if you want them.',
  },
]

const FAQS: QA[] = [
  {
    q: 'Is Wix good enough for a tradesman?',
    a: 'It can be. If you are starting out, have more time than money and are happy to learn the editor, a builder site is far better than no website at all. Choose a simple template, use your own photos rather than stock ones, put your phone number at the top, and check it on your phone with Google’s free speed test before you rely on it.',
  },
  {
    q: 'Why are some builder sites slow?',
    a: 'A template has to work for every kind of business, so it loads code for galleries, shops, animations and apps whether your page uses them or not. On a desktop with fast broadband you rarely notice; on a phone with one bar of signal on a driveway, it is the difference between a call and someone pressing back.',
  },
  {
    q: 'Can I move my Wix site to another host later?',
    a: 'Generally not as it is: builder platforms run your site on their own systems, so leaving usually means rebuilding the site elsewhere. Your domain name, your words and your photos are yours to take; the design and the way it was put together usually are not.',
  },
  {
    q: 'When is paying for a hand-coded site worth it?',
    a: 'When the website is meant to win work rather than just exist: you want to be found for specific services and towns, you are aiming at better-paid jobs, and you would rather spend your evenings on anything other than a site editor. It is also worth it if you want to own the site outright and stop paying a subscription for it.',
  },
]

export default function WixVsHandCodedGuidePage() {
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
      <Breadcrumbs items={[{ name: 'Guides', href: '/guides' }, { name: 'Wix vs hand-coded', href: PATH }]} />
      <PageHeader
        compact
        eyebrow="Guide"
        title="Wix, Squarespace or hand-coded?"
        body="When a DIY website builder is genuinely the right choice for a trade business, and when it quietly costs you jobs."
      />

      <article className="py-20 sm:py-24">
        <div className="mx-auto max-w-3xl px-5 sm:px-8">
          <Reveal>
            <div className="rounded-2xl border border-blueprint/40 bg-card p-7">
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">The short answer</span>
              <p className="mt-3 text-pretty leading-relaxed text-foreground/90">
                A builder like Wix, Squarespace or GoDaddy is a good way to get a basic site up yourself for a monthly
                fee, and much better than nothing. A hand-coded site costs more up front, but it is usually faster on a
                phone, built around how your customers actually choose a trade, and yours to keep with no
                subscription. If you are just starting out, a builder is fine. If the website is meant to win you better
                work, it is worth doing properly.
              </p>
            </div>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">Side by side</h2>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              Builder plans change often, so check current prices with each one. For rough costs across every option,
              see{' '}
              <Link href="/guides/how-much-does-a-tradesman-website-cost" className="text-blueprint underline underline-offset-4">
                what a tradesman&apos;s website really costs
              </Link>
              .
            </p>
          </Reveal>

          <div className="mt-8 overflow-x-auto rounded-2xl border border-border">
            <table className="w-full min-w-[640px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-card/60 font-mono text-[11px] uppercase tracking-[0.15em] text-muted-foreground">
                  <th scope="col" className="px-5 py-4 font-medium">What matters</th>
                  <th scope="col" className="px-5 py-4 font-medium">Website builder</th>
                  <th scope="col" className="px-5 py-4 font-medium">Hand-coded site</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border align-top">
                {COMPARISON.map((row) => (
                  <tr key={row.aspect}>
                    <th scope="row" className="px-5 py-4 font-semibold text-foreground">{row.aspect}</th>
                    <td className="px-5 py-4 text-muted-foreground">{row.builder}</td>
                    <td className="px-5 py-4 text-muted-foreground">{row.coded}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">When a builder is the right call</h2>
            <ul className="mt-6 list-disc space-y-3 pl-5 text-pretty leading-relaxed text-muted-foreground marker:text-blueprint">
              <li>You are just starting out and cash matters more than your evenings.</li>
              <li>Most of your work comes from word of mouth, and the site only needs to confirm you are real.</li>
              <li>You enjoy tinkering and want to change things yourself every week.</li>
            </ul>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">Where it quietly costs you work</h2>
            <ul className="mt-6 space-y-4 text-pretty leading-relaxed text-muted-foreground">
              <li>
                <strong className="text-foreground">Slow on the phone in the customer&apos;s hand.</strong> Most people looking
                for a trade search on a mobile, often on a weak signal. A page that takes several seconds to appear loses
                people before they see your work. Run your own site through our{' '}
                <Link href="/speed-test" className="text-blueprint underline underline-offset-4">free speed test</Link> to see
                where you stand.
              </li>
              <li>
                <strong className="text-foreground">Built around the template, not the job.</strong> A good trade site has a
                page for each service people search for and each area you cover, with the call button always in reach.
                Templates are built for every kind of business, so most of that is left to you to work out.
              </li>
              <li>
                <strong className="text-foreground">A subscription that never ends.</strong> Stop paying and the site goes,
                and moving usually means starting again.
              </li>
              <li>
                <strong className="text-foreground">Your evenings.</strong> The hours spent wrestling an editor are hours not
                spent quoting, invoicing or with your family.
              </li>
            </ul>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">If you go with a builder, do these five things</h2>
            <ol className="mt-6 list-decimal space-y-3 pl-5 text-pretty leading-relaxed text-muted-foreground marker:text-blueprint">
              <li>Put your phone number at the top of every page, as a tap-to-call link.</li>
              <li>Use your own photos of finished jobs, not stock images.</li>
              <li>Say the towns you cover in plain words, on the page.</li>
              <li>Link to your Google reviews, and keep asking for new ones.</li>
              <li>Test it on your own phone, on mobile data, and with Google&apos;s speed test.</li>
            </ol>
          </Reveal>

          <Reveal className="mt-14 rounded-2xl border border-border bg-card/40 p-7">
            <h2 className="font-display text-2xl font-bold tracking-tight">When you want it done properly</h2>
            <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
              I build hand-coded websites for UK trades at a fixed price agreed before any work starts, built for 90+ on
              Google&apos;s mobile speed test, and you own the code and the domain outright. No monthly fee on the website.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                href="/work#pricing"
                className="group inline-flex items-center gap-2 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-blueprint transition-colors hover:text-brass"
              >
                See prices and what&apos;s included
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
              <Link
                href="/speed-test"
                className="font-mono text-sm uppercase tracking-[0.15em] text-muted-foreground transition-colors hover:text-blueprint"
              >
                Test your current site
              </Link>
            </div>
          </Reveal>
        </div>
      </article>

      <Faq items={FAQS} title="More questions on website builders" />
      <CtaBand />
    </main>
  )
}
