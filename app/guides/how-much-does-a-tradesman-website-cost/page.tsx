import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Breadcrumbs } from '@/components/breadcrumbs'
import { Faq, type QA } from '@/components/faq'
import { JsonLd } from '@/components/json-ld'
import { CtaBand } from '@/components/cta-band'
import { Reveal } from '@/components/reveal'
import { PRICES, SITE, UPDATED } from '@/lib/site'

const PATH = '/guides/how-much-does-a-tradesman-website-cost'
const TITLE = 'How Much Does a Website Cost for a Tradesman? (UK 2026 Guide)'
const DESCRIPTION =
  'What a tradesman’s website costs in the UK: DIY, freelancer, agency and fixed-price options compared, plus hidden costs and the questions to ask first.'

export const metadata: Metadata = {
  title: 'Tradesman Website Cost: UK 2026 Guide',
  description: DESCRIPTION,
  alternates: { canonical: PATH },
  openGraph: { title: `${TITLE} | ${SITE.name}`, description: DESCRIPTION, url: PATH, type: 'article' },
}

const OPTIONS = [
  {
    option: 'DIY website builder',
    cost: 'Roughly £10 to £30 a month, plus your own time',
    good: 'A very small budget and you are happy to build it yourself.',
    watch: 'Templates look like everyone else’s, pages can be slow, and you rent it: stop paying and it goes.',
  },
  {
    option: 'Freelance designer (often WordPress)',
    cost: 'Commonly £500 to £3,000 one-off, plus hosting',
    good: 'A custom look for a modest spend.',
    watch: 'Plugins need updating, hosting and renewals add up, and quality varies a lot between people.',
  },
  {
    option: 'Web agency',
    cost: 'Often £3,000 to £10,000 or more',
    good: 'Larger firms with bigger, more complex needs.',
    watch: 'High cost, and some agencies tie you to a monthly retainer.',
  },
  {
    option: 'Fixed-price, hand-coded build',
    cost: `From £${PRICES.landing} for a landing page, £${PRICES.build.toLocaleString('en-GB')} for a five-page site with a dashboard`,
    good: 'A fast, custom site you own outright, for a price agreed before work starts.',
    watch: 'Built to a fixed scope, so it suits most trade sites but not shops or sites with dozens of pages.',
  },
]

const FAQS: QA[] = [
  {
    q: 'Can I build my own trade website for free?',
    a: 'You can, using a free tier of a website builder, and for some very small firms that is enough to start. The trade-offs are usually a builder’s branding or address on the site, limited control, slower pages and a template look. If the website is meant to win you work, most tradespeople find a proper site worth paying for.',
  },
  {
    q: 'Do I have to pay monthly for a website?',
    a: 'Not necessarily. Website builders and some agencies charge monthly, which means you stop having a site if you stop paying. Other options are a one-off price with you owning the site, where the only ongoing costs are your domain and hosting. Always ask what happens if you stop paying.',
  },
  {
    q: 'Do I really need a website if I get work by word of mouth?',
    a: 'Many people who are recommended to you will look you up before they ring. A clear, fast website that shows your work reassures them, and it catches customers who never heard of you. It does not replace word of mouth. It backs it up.',
  },
  {
    q: 'What should a basic trade website include?',
    a: 'Your services, the areas you cover, photos of real work, how to contact you (a phone number that can be tapped, plus a short form), and any guarantees or accreditations you genuinely hold. It must also load quickly on a phone.',
  },
]

export default function CostGuidePage() {
  return (
    <main>
      <JsonLd
        data={{
          '@context': 'https://schema.org',
          '@type': 'Article',
          headline: TITLE,
          description: DESCRIPTION,
          datePublished: UPDATED,
          dateModified: UPDATED,
          inLanguage: 'en-GB',
          mainEntityOfPage: `${SITE.url}${PATH}`,
          author: { '@type': 'Organization', name: SITE.name, url: SITE.url },
          publisher: { '@id': `${SITE.url}/#organization` },
        }}
      />
      <Breadcrumbs items={[{ name: 'Guides', href: '/guides' }, { name: 'Website cost', href: PATH }]} />
      <PageHeader compact
        eyebrow="Guide · UK 2026"
        title="How much does a website cost for a tradesman?"
        body="A straight answer, what changes the price, and what to check before you pay anyone."
      />

      <article className="py-20 sm:py-24">
        <div className="mx-auto max-w-3xl px-5 sm:px-8">
          <Reveal>
            <div className="rounded-2xl border border-blueprint/40 bg-card p-7">
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">The short answer</span>
              <p className="mt-3 text-pretty leading-relaxed text-foreground/90">
                Most UK tradespeople pay somewhere between a few hundred pounds a year for a do-it-yourself builder and
                several thousand pounds for an agency. What you pay depends on how many pages you need, whether the
                design is made for you, and whether you rent the site monthly or own it outright. A fixed-price,
                hand-coded site from a solo builder usually sits between the two. Prices vary widely, so get two or
                three quotes.
              </p>
            </div>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">
              Four ways to get a trade website, compared
            </h2>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              These are typical UK ranges, not quotes. Your own price will depend on your needs.
            </p>
          </Reveal>

          <div className="mt-8 overflow-x-auto rounded-2xl border border-border">
            <table className="w-full min-w-[640px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-card/60 font-mono text-[11px] uppercase tracking-[0.15em] text-muted-foreground">
                  <th scope="col" className="px-5 py-4 font-medium">Option</th>
                  <th scope="col" className="px-5 py-4 font-medium">Typical cost</th>
                  <th scope="col" className="px-5 py-4 font-medium">Good for</th>
                  <th scope="col" className="px-5 py-4 font-medium">Watch out for</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border align-top">
                {OPTIONS.map((o) => (
                  <tr key={o.option}>
                    <th scope="row" className="px-5 py-4 font-semibold text-foreground">{o.option}</th>
                    <td className="px-5 py-4 text-foreground/85">{o.cost}</td>
                    <td className="px-5 py-4 text-muted-foreground">{o.good}</td>
                    <td className="px-5 py-4 text-muted-foreground">{o.watch}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">What actually changes the price</h2>
            <ul className="mt-6 space-y-4 text-pretty leading-relaxed text-muted-foreground">
              <li>
                <strong className="text-foreground">Number of pages.</strong> A single landing page costs far less than
                a site with separate pages for every service and area.
              </li>
              <li>
                <strong className="text-foreground">Custom design or a template.</strong> A design made for your firm
                takes more work than a template with your logo on it, and looks different for it.
              </li>
              <li>
                <strong className="text-foreground">Features.</strong> A gallery, a quote form, WhatsApp and call
                buttons, booking or a customer dashboard each add scope.
              </li>
              <li>
                <strong className="text-foreground">Who writes the words and takes the photos.</strong> If you supply
                good photos and clear notes, it is cheaper and quicker than commissioning them.
              </li>
              <li>
                <strong className="text-foreground">Speed.</strong> Sites built quickly, and built lightly, tend to
                load faster too, which matters for customers searching on a phone.
              </li>
            </ul>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">Costs people forget</h2>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              The build price is rarely the whole bill. Ask about all of these before you agree anything:
            </p>
            <ul className="mt-5 list-disc space-y-3 pl-5 text-pretty leading-relaxed text-muted-foreground marker:text-blueprint">
              <li>Your domain name, which is usually an annual renewal.</li>
              <li>Hosting, and whether it is included or billed separately.</li>
              <li>Email addresses that match your domain.</li>
              <li>Updates and security maintenance, especially for plugin-based sites.</li>
              <li>Monthly plans, and what happens to your site if you stop paying.</li>
              <li>Photography, if you do not have good pictures of your own work.</li>
            </ul>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">
              Questions to ask before you pay anyone
            </h2>
            <ol className="mt-6 list-decimal space-y-3 pl-5 text-pretty leading-relaxed text-muted-foreground marker:font-mono marker:text-blueprint">
              <li>Do I own the site and the domain outright when it is finished?</li>
              <li>Is the price fixed, and what could make it change?</li>
              <li>What is included after launch, and for how long?</li>
              <li>How fast will it load on a phone? Can you show me a speed test?</li>
              <li>Can I see examples of what you have built, and be told honestly which are for real clients?</li>
              <li>What happens if I want a change in six months?</li>
            </ol>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">Is a website worth paying for?</h2>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              A simple test: if a good website brings you one extra job you would not otherwise have had, and that job
              is worth more than the site cost, it has paid for itself. For most trades a single decent job does
              that, so the real question is less &ldquo;can I afford one&rdquo; and more &ldquo;will it be fast and
              clear enough to win the customer once they find me&rdquo;.
            </p>
          </Reveal>

          <Reveal className="mt-14 rounded-2xl border border-border bg-card/40 p-7">
            <h2 className="font-display text-2xl font-bold tracking-tight">How Scalar Digital prices it</h2>
            <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
              I build hand-coded sites for UK trades at a fixed price agreed before any work starts. A single landing
              page is £{PRICES.landing}. The full build is £{PRICES.build.toLocaleString('en-GB')}: five pages plus a
              private dashboard for enquiries, quotes, jobs and invoices, hosted free for your first 12 months. You own
              the code and the domain outright either way.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                href="/work#estimate"
                className="group inline-flex items-center gap-2 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-blueprint transition-colors hover:text-brass"
              >
                Estimate your price
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
      </article>

      <Faq items={FAQS} title="More questions on website costs" />
      <CtaBand />
    </main>
  )
}
