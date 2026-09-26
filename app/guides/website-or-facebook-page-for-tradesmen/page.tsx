import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Breadcrumbs } from '@/components/breadcrumbs'
import { Faq, type QA } from '@/components/faq'
import { JsonLd } from '@/components/json-ld'
import { CtaBand } from '@/components/cta-band'
import { Reveal } from '@/components/reveal'
import { SITE, UPDATED } from '@/lib/site'

const PATH = '/guides/website-or-facebook-page-for-tradesmen'
const TITLE = 'Website or Facebook Page? What Actually Wins Work for UK Tradespeople'
const DESCRIPTION =
  'A straight comparison of running your trade business on a Facebook or Instagram page versus your own website - what each is genuinely good at, and where relying on one alone costs you jobs.'

export const metadata: Metadata = {
  title: 'Website vs Facebook Page for Tradesmen',
  description: DESCRIPTION,
  alternates: { canonical: PATH },
  openGraph: { title: `${TITLE} | ${SITE.name}`, description: DESCRIPTION, url: PATH, type: 'article' },
}

const COMPARISON = [
  {
    aspect: 'Who owns it',
    facebook: 'Meta. Your page, your followers and your reviews all live on their platform, under their rules.',
    website: 'You. The domain and the code are yours, whoever built it.',
  },
  {
    aspect: 'What happens if the platform changes',
    facebook: 'A reach drop, an account flag or a policy change can cut your visibility overnight, with no warning and no one to call.',
    website: 'Nothing changes unless you change it. It works the same way every day.',
  },
  {
    aspect: 'First impression for a new enquiry',
    facebook: 'Your page sits inside a feed built to keep people scrolling past you, competing with ads and other pages.',
    website: 'Nothing to distract from your work, your price and how to reach you.',
  },
  {
    aspect: 'Being found on Google',
    facebook: 'Your page can rank, but it is one generic template competing with millions of others, not built around your services or areas.',
    website: 'Structured around your actual services and the areas you cover, which is what local search results reward.',
  },
  {
    aspect: 'Cost',
    facebook: 'Free to set up. Reach usually needs boosted posts or ads to stay meaningful.',
    website: 'A one-off or ongoing cost to build, then yours to keep.',
  },
  {
    aspect: 'Effort to keep it useful',
    facebook: 'Needs regular posts to stay visible in feeds, or reach quietly fades.',
    website: 'Sits there working with no ongoing posting required, though it is easy to update when your work changes.',
  },
]

const FAQS: QA[] = [
  {
    q: 'Can a Facebook page replace a website completely?',
    a: 'For a very small operation taking a handful of jobs from an existing network, it can be enough for a while. Once you rely on people finding you who have never heard of you, a page inside someone else’s feed is a weaker first impression than a site built around exactly what you do and where you work.',
  },
  {
    q: 'Should I have both a website and a Facebook page?',
    a: 'For most trades, yes. Facebook and Instagram are good for showing finished jobs to people who already follow you and for local groups. A website is what a stranger checks before they decide to call, and it is what Google actually ranks. They do different jobs.',
  },
  {
    q: 'Does Google favour Facebook pages or real websites?',
    a: 'A real website you control gives you far more room to target your specific services and areas, with pages, structured data and speed built around ranking for them. A Facebook page is one profile competing with millions of others on Meta’s domain, not yours.',
  },
  {
    q: 'What if my Facebook page already gets me work?',
    a: 'That is genuinely valuable and worth keeping. The question is what you are missing without a site of your own: people who search Google instead of Facebook, and the version of a first impression that is entirely under your control rather than sitting inside someone else’s platform.',
  },
]

export default function FacebookVsWebsiteGuidePage() {
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
      <Breadcrumbs items={[{ name: 'Guides', href: '/guides' }, { name: 'Website vs Facebook', href: PATH }]} />
      <PageHeader
        compact
        eyebrow="Guide"
        title="Website or Facebook page? What actually wins work."
        body="A fair look at what each one is genuinely good at, and where leaning on a Facebook page alone quietly costs you jobs."
      />

      <article className="py-20 sm:py-24">
        <div className="mx-auto max-w-3xl px-5 sm:px-8">
          <Reveal>
            <div className="rounded-2xl border border-blueprint/40 bg-card p-7">
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">The short answer</span>
              <p className="mt-3 text-pretty leading-relaxed text-foreground/90">
                A Facebook or Instagram page is a reasonable way to show finished jobs to people who already know you.
                It is a weaker way to be found by people who do not. Most established trades end up running both: the
                social page for word of mouth and repeat customers, a proper website for anyone searching Google or
                checking you out before they call.
              </p>
            </div>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">Side by side</h2>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              Neither is universally better. What matters is which job you need done.
            </p>
          </Reveal>

          <div className="mt-8 overflow-x-auto rounded-2xl border border-border">
            <table className="w-full min-w-[640px] border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-border bg-card/60 font-mono text-[11px] uppercase tracking-[0.15em] text-muted-foreground">
                  <th scope="col" className="px-5 py-4 font-medium">What matters</th>
                  <th scope="col" className="px-5 py-4 font-medium">Facebook / Instagram page</th>
                  <th scope="col" className="px-5 py-4 font-medium">Your own website</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border align-top">
                {COMPARISON.map((row) => (
                  <tr key={row.aspect}>
                    <th scope="row" className="px-5 py-4 font-semibold text-foreground">{row.aspect}</th>
                    <td className="px-5 py-4 text-muted-foreground">{row.facebook}</td>
                    <td className="px-5 py-4 text-muted-foreground">{row.website}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">
              Where a Facebook page genuinely wins
            </h2>
            <ul className="mt-6 list-disc space-y-3 pl-5 text-pretty leading-relaxed text-muted-foreground marker:text-blueprint">
              <li>It is free and quick to set up, with no build to commission.</li>
              <li>Local Facebook groups are still where a lot of word-of-mouth recommendations actually happen.</li>
              <li>Posting finished jobs is an easy habit, and people who already follow you see them without you doing anything else.</li>
              <li>Reviews from people in your area carry real weight when a neighbour asks &ldquo;anyone used a good roofer round here?&rdquo;</li>
            </ul>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">
              Where it quietly costs you work
            </h2>
            <ul className="mt-6 space-y-4 text-pretty leading-relaxed text-muted-foreground">
              <li>
                <strong className="text-foreground">Someone who has never heard of you searches Google, not Facebook.</strong> A
                page built around your specific services and the towns you cover has far more chance of showing up
                than a generic profile competing with millions of others on Meta&apos;s own domain.
              </li>
              <li>
                <strong className="text-foreground">You do not control what happens to it.</strong> An algorithm change, a
                flagged account or a policy update is entirely out of your hands. A site you own keeps working exactly
                the way you left it.
              </li>
              <li>
                <strong className="text-foreground">It looks the same as everyone else&apos;s.</strong> Every business
                gets the same template, the same layout, the same feed competing for attention. There is nothing that
                says this firm operates at a higher standard than the next one.
              </li>
              <li>
                <strong className="text-foreground">No real home for a quote form, a price guide or a proper gallery.</strong> A
                Facebook post scrolls away. A website page stays exactly where you put it.
              </li>
            </ul>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">The real answer for most trades</h2>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              Keep the Facebook or Instagram page if it already brings you work &mdash; it costs nothing to maintain
              alongside a website, and it is genuinely good at what it does. Add a website as the place a stranger
              lands when they search Google, get referred by someone outside your existing network, or want to check
              you out properly before they pick up the phone. One backs up word of mouth. The other catches everyone
              word of mouth never reaches.
            </p>
          </Reveal>

          <Reveal className="mt-14 rounded-2xl border border-border bg-card/40 p-7">
            <h2 className="font-display text-2xl font-bold tracking-tight">If you are ready for a site of your own</h2>
            <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
              I build hand-coded sites for UK trades at a fixed price agreed before any work starts, built around your
              actual services and the areas you cover &mdash; the structure a Facebook page cannot give you.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                href="/guides/how-much-does-a-tradesman-website-cost"
                className="group inline-flex items-center gap-2 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-blueprint transition-colors hover:text-brass"
              >
                See what it costs
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

      <Faq items={FAQS} title="More questions on Facebook pages and websites" />
      <CtaBand />
    </main>
  )
}
