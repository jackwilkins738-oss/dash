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

const PATH = '/guides/website-not-getting-enquiries'
const PUBLISHED = '2026-10-02'
const TITLE = 'Why Isn’t My Trade Website Getting Enquiries? 9 Things to Check'
const DESCRIPTION =
  'A trade website that gets visits but no calls usually has one of nine problems. How to check each one yourself in a few minutes, and what fixes it.'

export const metadata: Metadata = withSeo(PATH, {
  title: 'Trade Website Not Getting Enquiries? 9 Things to Check',
  description: DESCRIPTION,
  alternates: { canonical: PATH },
  openGraph: { title: `${TITLE} | ${SITE.name}`, description: DESCRIPTION, url: PATH, type: 'article' },
})

// Each one: what's wrong, how to check it yourself, what fixes it. Ordered by how often it's the cause.
const CHECKS: { title: string; check: string; fix: string; link?: { href: string; label: string } }[] = [
  {
    title: 'It is slow on a phone',
    check: 'Run it through a mobile speed test, or open it on your own phone on mobile data, not Wi-Fi. If it takes more than a few seconds to show anything useful, many people leave before it does.',
    fix: 'Usually the platform: heavy themes, page builders and plugins. Smaller photos help a little; a lighter site helps a lot.',
    link: { href: '/speed-test', label: 'Test your site free' },
  },
  {
    title: 'Your phone number is hard to find or tap',
    check: 'On your phone, can you see the number without scrolling, and does tapping it start a call?',
    fix: 'A tap-to-call number at the top of every page, and a call button that stays in reach as people scroll.',
  },
  {
    title: 'Nobody can tell where you work',
    check: 'Would a stranger know, within five seconds, which towns you cover?',
    fix: 'Say your areas in plain words near the top, and give your main towns their own pages so Google can match you to them.',
  },
  {
    title: 'It does not show your actual work',
    check: 'Are the photos yours, of finished jobs? Stock photos of smiling builders tell people nothing.',
    fix: 'Real photos from your own jobs - before and after pairs are the most convincing of all.',
  },
  {
    title: 'There is no proof anyone else trusted you',
    check: 'Can a visitor see reviews, or a link to them, without hunting?',
    fix: 'Show a few genuine reviews and link to your Google reviews. Then keep asking for new ones.',
    link: { href: '/guides/how-to-get-more-google-reviews', label: 'How to get more reviews' },
  },
  {
    title: 'The enquiry form is broken, or too long',
    check: 'Send yourself an enquiry right now. Did it arrive? How many boxes did you have to fill in?',
    fix: 'Name, phone, a line about the job - and a test enquiry every month. A broken form costs jobs silently.',
  },
  {
    title: 'It looks out of date',
    check: 'Is the copyright year old? Is the design from another decade? People read an old site as a firm that might not be around.',
    fix: 'Even a fresh, simple site beats an old elaborate one. Keep the year, photos and services current.',
  },
  {
    title: 'Google cannot find it for what people search',
    check: 'Search for your main service and your town on Google, logged out. Are you anywhere on the first page or in the map?',
    fix: 'A page for each main service, your areas named clearly, and a complete Google Business Profile.',
    link: { href: '/guides/google-business-profile-for-tradesmen', label: 'Google Business Profile guide' },
  },
  {
    title: 'Enquiries arrive, but replies are slow',
    check: 'How long do enquiries wait before you answer? Many customers hire whoever gets back to them first.',
    fix: 'Get every enquiry on your phone the moment it arrives, and reply the same day - even if it is only to book a visit.',
  },
]

const FAQS: QA[] = [
  {
    q: 'How do I know if people are visiting my site at all?',
    a: 'Free tools show it: Google Search Console tells you how often you appear in searches and how many people click through, and most website platforms have simple visitor stats. If lots of people visit but nobody calls, the problem is on the page. If nobody visits, it is being found that needs work.',
  },
  {
    q: 'Should I just pay for Google Ads?',
    a: 'Ads can bring visitors quickly, but they send people to the same page. If that page is slow, unconvincing or hard to call from, ads make the problem more expensive rather than fixing it. Fix the page first.',
  },
  {
    q: 'How long before changes bring more enquiries?',
    a: 'Fixes on the page itself - speed, a clear call button, real photos and reviews - help straight away, because they work on visitors you already have. Being found more on Google takes longer, usually weeks to months.',
  },
  {
    q: 'Is it worth fixing my old site or starting again?',
    a: 'If the site is quick, you can edit it and most of the problems above are content, fix it. If it is slow because of the platform or theme it is built on, more content will not fix that, and a new, lighter site is usually cheaper than patching an old one for years.',
  },
]

export default function NoEnquiriesGuidePage() {
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
      <Breadcrumbs items={[{ name: 'Guides', href: '/guides' }, { name: 'Website not getting enquiries', href: PATH }]} />
      <PageHeader
        compact
        eyebrow="Guide"
        title="Why isn't my website getting enquiries?"
        body="Nine things that stop a trade website turning visits into calls, how to check each one yourself in a few minutes, and what fixes it."
      />

      <article className="py-20 sm:py-24">
        <div className="mx-auto max-w-3xl px-5 sm:px-8">
          <Reveal>
            <div className="rounded-2xl border border-blueprint/40 bg-card p-7">
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">The short answer</span>
              <p className="mt-3 text-pretty leading-relaxed text-foreground/90">
                It is almost always one of two things: people are not finding the site, or they find it and leave before
                calling. The second is more common and quicker to fix - a slow page on a phone, a number that is hard to
                tap, or nothing that proves you do good work. Go through the checks below on your own phone; most take a
                minute.
              </p>
            </div>
          </Reveal>

          <ol className="mt-14 space-y-6">
            {CHECKS.map((c, i) => (
              <li key={c.title}>
                <Reveal className="rounded-2xl border border-border bg-card/40 p-6 sm:p-7">
                  <div className="flex items-start gap-4">
                    <span className="font-mono text-sm text-blueprint">{String(i + 1).padStart(2, '0')}</span>
                    <div>
                      <h2 className="font-display text-xl font-bold tracking-tight sm:text-2xl">{c.title}</h2>
                      <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
                        <strong className="text-foreground">Check: </strong>
                        {c.check}
                      </p>
                      <p className="mt-2 text-pretty leading-relaxed text-muted-foreground">
                        <strong className="text-foreground">Fix: </strong>
                        {c.fix}
                      </p>
                      {c.link && (
                        <Link
                          href={c.link.href}
                          className="mt-3 inline-flex items-center gap-2 font-mono text-xs font-semibold uppercase tracking-[0.15em] text-blueprint hover:text-brass"
                        >
                          {c.link.label}
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Link>
                      )}
                    </div>
                  </div>
                </Reveal>
              </li>
            ))}
          </ol>

          <Reveal className="mt-14 rounded-2xl border border-border bg-card/40 p-7">
            <h2 className="font-display text-2xl font-bold tracking-tight">Want a second pair of eyes?</h2>
            <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
              Run the free speed test first - it checks the most common cause in under a minute. If you would like me to
              look at the rest, get in touch and I&apos;ll tell you honestly whether your site needs fixing or replacing.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                href="/speed-test"
                className="group inline-flex items-center gap-2 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-blueprint transition-colors hover:text-brass"
              >
                Run the speed test
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
              <Link
                href="/contact"
                className="font-mono text-sm uppercase tracking-[0.15em] text-muted-foreground transition-colors hover:text-blueprint"
              >
                Ask me to look
              </Link>
            </div>
          </Reveal>
        </div>
      </article>

      <Faq items={FAQS} path={PATH} title="More questions on getting enquiries" />
      <CtaBand />
    </main>
  )
}
