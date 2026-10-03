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
import { withSeo } from '@/lib/seo'

const PATH = '/guides/checkatrade-or-your-own-website'
const PUBLISHED = '2026-10-01'
const TITLE = 'Checkatrade or Your Own Website? Where Trade Leads Really Come From'
const DESCRIPTION =
  'A fair comparison of trade directories like Checkatrade, MyBuilder and Rated People against a website of your own - what each is good at, what you give up, and why most established trades end up with both.'

export const metadata: Metadata = withSeo(PATH, {
  title: 'Checkatrade vs Your Own Website for Tradesmen',
  description: DESCRIPTION,
  alternates: { canonical: PATH },
  openGraph: { title: `${TITLE} | ${SITE.name}`, description: DESCRIPTION, url: PATH, type: 'article' },
})

// Deliberately no prices for the directories: they change, vary by trade and area, and a wrong figure
// about someone else's business is worse than none. Readers are pointed to the directories themselves.
const COMPARISON = [
  {
    aspect: 'Where the customer finds you',
    directory: 'On the directory, in a list of other firms in your trade and area, usually side by side.',
    website: 'On Google, from a referral, or from your van and cards - on a page with nobody else on it.',
  },
  {
    aspect: 'How you pay',
    directory: 'A membership fee, or a charge per lead or per job you express interest in, depending on the platform.',
    website: 'A one-off build, then whatever you choose to spend keeping it current. No charge per enquiry.',
  },
  {
    aspect: 'Your reviews',
    directory: 'Live on the directory. They count while you are a member and you cannot take them with you.',
    website: 'Your Google reviews follow your business wherever it goes, and your site can show them.',
  },
  {
    aspect: 'Trust with a stranger',
    directory: 'Strong: vetting checks and a recognisable name do some of the convincing for you.',
    website: 'Has to be earned on the page - real photos, real reviews, your registered details, a fast site.',
  },
  {
    aspect: 'Competing on price',
    directory: 'The customer is invited to compare you with the next firm on the list, often on price.',
    website: 'The customer is looking at your work and your standard, not a comparison table.',
  },
  {
    aspect: 'If you stop paying',
    directory: 'The listing, its reviews and its enquiries stop.',
    website: 'It keeps working. You own it.',
  },
]

const FAQS: QA[] = [
  {
    q: 'Is Checkatrade worth it for a new trade business?',
    a: 'It can be. When nobody knows your name yet, a directory with vetting checks and an established brand lends you trust you have not had time to build, and it can fill a diary early on. The thing to watch is what each job costs you once membership or lead fees are counted, and how much of your work depends on a platform you do not control. Check the current terms on the directory itself before signing up - fees vary by trade and area.',
  },
  {
    q: 'Can I have a website and still use Checkatrade?',
    a: 'Yes, and many established firms do: the directory for the reach and trust it brings, a website for people who search for you by name, find you on Google or are referred by a past customer. Many people who find you on a directory also look you up before they ring, so a proper website helps the directory leads convert too.',
  },
  {
    q: 'Do directory reviews help my Google ranking?',
    a: 'Your Google Business Profile reviews are what show up in Google Maps and the local results. Directory reviews mainly help you on the directory itself. If you want reviews that keep working for your business whatever platforms you use, ask happy customers for a Google review as well.',
  },
  {
    q: 'What does a website do that a directory listing cannot?',
    a: 'It is yours: no fee per enquiry, no competitors on the same page, reviews and photos you control, and pages built around exactly the services and towns you want to be found for. It also keeps working if you ever leave a directory.',
  },
]

export default function CheckatradeVsWebsiteGuidePage() {
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
      <Breadcrumbs items={[{ name: 'Guides', href: '/guides' }, { name: 'Checkatrade vs your own website', href: PATH }]} />
      <PageHeader
        compact
        eyebrow="Guide"
        title="Checkatrade or your own website?"
        body="What trade directories are genuinely good at, what you give up by relying on one, and how most established firms use both."
      />

      <article className="py-20 sm:py-24">
        <div className="mx-auto max-w-3xl px-5 sm:px-8">
          <Reveal>
            <div className="rounded-2xl border border-blueprint/40 bg-card p-7">
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">The short answer</span>
              <p className="mt-3 text-pretty leading-relaxed text-foreground/90">
                A directory like Checkatrade, MyBuilder or Rated People rents you reach and borrowed trust: useful,
                especially early on, but every enquiry comes with a fee and a list of competitors beside you. A
                website of your own is the opposite trade-off: you have to earn the trust on the page, but the
                enquiries cost nothing extra and nobody else is on it. Most established trades end up with both.
              </p>
            </div>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">Side by side</h2>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              Each platform works a little differently and changes its terms from time to time, so check the current
              details with the directory itself. The broad trade-offs hold across all of them.
            </p>
          </Reveal>

          <div className="mt-8 overflow-x-auto rounded-2xl border border-border">
            <table className="w-full min-w-[640px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-card/60 font-mono text-[11px] uppercase tracking-[0.15em] text-muted-foreground">
                  <th scope="col" className="px-5 py-4 font-medium">What matters</th>
                  <th scope="col" className="px-5 py-4 font-medium">Trade directory</th>
                  <th scope="col" className="px-5 py-4 font-medium">Your own website</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border align-top">
                {COMPARISON.map((row) => (
                  <tr key={row.aspect}>
                    <th scope="row" className="px-5 py-4 font-semibold text-foreground">{row.aspect}</th>
                    <td className="px-5 py-4 text-muted-foreground">{row.directory}</td>
                    <td className="px-5 py-4 text-muted-foreground">{row.website}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">Where a directory genuinely helps</h2>
            <ul className="mt-6 list-disc space-y-3 pl-5 text-pretty leading-relaxed text-muted-foreground marker:text-blueprint">
              <li>When you are new and nobody knows your name, its vetting and brand vouch for you.</li>
              <li>It brings people who are actively looking for a trade right now, not just browsing.</li>
              <li>There is nothing to build: you can be listed and taking enquiries quickly.</li>
              <li>A steady stream of reviews in one place is reassuring to customers who use that directory.</li>
            </ul>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">What relying on one alone costs you</h2>
            <ul className="mt-6 space-y-4 text-pretty leading-relaxed text-muted-foreground">
              <li>
                <strong className="text-foreground">Every enquiry has a price on it.</strong> Whether it is a membership or a
                fee per lead, work through what each job actually cost you once you include the enquiries that came to
                nothing.
              </li>
              <li>
                <strong className="text-foreground">You are one name in a list.</strong> The customer is invited to compare you
                with the next firm, and the easiest thing to compare is price. The firm worth more has the hardest time
                showing it.
              </li>
              <li>
                <strong className="text-foreground">The reviews are not yours to keep.</strong> Years of good feedback stay on
                the platform if you ever leave.
              </li>
              <li>
                <strong className="text-foreground">Your work depends on their rules.</strong> Fee changes, ranking changes or
                a dispute about one job are all out of your hands.
              </li>
            </ul>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">The sensible way to use both</h2>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              Treat a directory as a way to fill the diary, not the foundation of the business. Alongside it, build
              the things that are yours: a website that shows your real work and the areas you cover, and a Google
              Business Profile with reviews from happy customers (our{' '}
              <Link href="/guides/how-to-get-more-google-reviews" className="text-blueprint underline underline-offset-4">
                guide to getting more Google reviews
              </Link>{' '}
              covers how). Over time, more of your work arrives directly, at no cost per enquiry, and the directory
              becomes a top-up you can take or leave rather than a bill you cannot stop paying.
            </p>
          </Reveal>

          <Reveal className="mt-14 rounded-2xl border border-border bg-card/40 p-7">
            <h2 className="font-display text-2xl font-bold tracking-tight">A site that works alongside the directories</h2>
            <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
              I build hand-coded websites for UK trades at a fixed price agreed before any work starts, and you own
              them outright: no fee per enquiry, ever. Directory customers who look you up before they ring find a
              site that backs up everything your listing says.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                href="/guides/how-much-does-a-tradesman-website-cost"
                className="group inline-flex items-center gap-2 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-blueprint transition-colors hover:text-brass"
              >
                See what a website costs
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

      <Faq items={FAQS} path={PATH} title="More questions on directories and websites" />
      <CtaBand />
    </main>
  )
}
