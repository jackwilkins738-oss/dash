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

const PATH = '/guides/how-to-get-more-google-reviews'
const PUBLISHED = '2026-09-28'
const TITLE = 'How to Get More Google Reviews as a Tradesperson (Without Breaking the Rules)'
const DESCRIPTION =
  'A practical system for UK trades to get a steady flow of genuine Google reviews: when to ask, what to send, how to reply, and what Google’s rules and UK law say you mustn’t do.'

export const metadata: Metadata = {
  title: 'How to Get More Google Reviews: Trades Guide',
  description: DESCRIPTION,
  alternates: { canonical: PATH },
  openGraph: { title: `${TITLE} | ${SITE.name}`, description: DESCRIPTION, url: PATH, type: 'article' },
}

const FAQS: QA[] = [
  {
    q: 'Can I offer a discount for a review?',
    a: 'No. Google’s rules don’t allow offering anything in return for a review, and it can get reviews removed or your profile restricted. Just ask, and make it easy.',
  },
  {
    q: 'Can I only ask the customers I know were happy?',
    a: 'Google’s rules say you shouldn’t selectively ask only happy customers. Ask everyone the same way. If a job went wrong, sort it out first; a problem you fixed well often turns into one of your best reviews.',
  },
  {
    q: 'Can I get a bad review removed?',
    a: 'Only if it breaks Google’s policies, for example it’s fake, offensive, or about a different business. You can report it from your profile. A review you simply disagree with will usually stay, which is why a calm, factual reply matters so much.',
  },
  {
    q: 'Are fake reviews illegal in the UK?',
    a: 'Yes. Since April 2025, under the Digital Markets, Competition and Consumers Act 2024, it’s unlawful to write, commission or publish fake reviews, or to present reviews in a misleading way. That covers buying reviews and having friends post as customers.',
  },
  {
    q: 'How many reviews do I need?',
    a: 'There’s no magic number. Customers look at how many you have, how recent they are and what they say. A steady flow of recent reviews tends to count for more than a big batch from years ago.',
  },
]

export default function GoogleReviewsGuide() {
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
      <Breadcrumbs items={[{ name: 'Guides', href: '/guides' }, { name: 'Google reviews', href: PATH }]} />
      <PageHeader compact
        eyebrow="Guide · UK 2026"
        title="How to get more Google reviews as a tradesperson."
        body="Most happy customers would leave one. They just need asking at the right moment, with a link that takes ten seconds."
      />

      <article className="py-20 sm:py-24">
        <div className="mx-auto max-w-3xl px-5 sm:px-8">
          <Reveal>
            <div className="rounded-2xl border border-blueprint/40 bg-card p-7">
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">The short answer</span>
              <p className="mt-3 text-pretty leading-relaxed text-foreground/90">
                Ask every customer, every time, a day or two after the job is finished, and send them your direct
                review link so it takes seconds. Send one polite reminder, never more. Reply to every review. Don’t
                offer anything in return and don’t pick and choose who you ask. It’s the system that wins, not the
                wording.
              </p>
            </div>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">1. Get your direct review link</h2>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              In your Google Business Profile, look for <strong className="text-foreground">Ask for reviews</strong>{' '}
              (sometimes shown as &ldquo;Get more reviews&rdquo;). It gives you a short link that opens the review box
              straight away, with your stars ready to tap. Save it somewhere you can paste it from your phone. Asking
              someone to &ldquo;search for us on Google and find the reviews bit&rdquo; loses most of them.
            </p>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">2. Ask at the right moment</h2>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              The best time is shortly after the job is finished and tidied, while the new roof, kitchen or boiler is
              still the best thing that happened to their week. Mention it in person at handover (&ldquo;I’ll send
              you a link. A quick review really helps a small firm like mine&rdquo;), then send the link a day or
              two later.
            </p>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">3. Keep the message short</h2>
            <div className="mt-6 rounded-2xl border border-border bg-card/40 p-6 font-mono text-sm leading-relaxed text-foreground/90">
              Hi Sarah, thanks again for having us. If you’re happy with the new roof, a quick Google review would
              really help us out. It takes about a minute: [your link]. And if anything isn’t right, just tell me and
              I’ll sort it. Dave
            </div>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              Use their name and the actual job. Text or WhatsApp often gets a quicker response than email; email is
              easier to automate. Either works.
            </p>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">4. One reminder, then stop</h2>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              People mean to do it and forget. One friendly nudge about a week later picks up a good share of them.
              More than one starts to feel like pestering, which is the opposite of the impression you want to
              leave.
            </p>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">5. Reply to every review</h2>
            <ul className="mt-6 space-y-4 text-pretty leading-relaxed text-muted-foreground">
              <li>
                <strong className="text-foreground">Good ones:</strong> thank them by name and mention the job. It
                takes thirty seconds and shows the next customer there’s a real person behind the business.
              </li>
              <li>
                <strong className="text-foreground">Bad ones:</strong> stay calm, stick to facts, don’t share
                private details, and offer to sort it out offline. You’re writing for the next hundred people who
                read it, not to win the argument.
              </li>
            </ul>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">What not to do</h2>
            <ul className="mt-5 list-disc space-y-3 pl-5 text-pretty leading-relaxed text-muted-foreground marker:text-blueprint">
              <li>Offer a discount, a prize draw or anything else in return for a review.</li>
              <li>Only ask the customers you’re sure were delighted.</li>
              <li>Write reviews yourself, or have friends and family pose as customers.</li>
              <li>Buy reviews or swap them with other businesses. It’s against Google’s rules and, in the UK, the law.</li>
            </ul>
          </Reveal>

          <Reveal className="mt-14 rounded-2xl border border-border bg-card/40 p-7">
            <h2 className="font-display text-2xl font-bold tracking-tight">Make it happen every time</h2>
            <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
              The hard part isn’t the asking. It’s remembering to do it on a Friday afternoon after a long job. The
              dashboard that comes with a Scalar Digital full build can do it for you: mark the job complete, and
              your customer gets your review link two days later, with one reminder a week after that, and never
              more.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                href="/work"
                className="group inline-flex items-center gap-2 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-blueprint transition-colors hover:text-brass"
              >
                See what&apos;s included
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
              <Link
                href="/guides/google-business-profile-for-tradesmen"
                className="font-mono text-sm uppercase tracking-[0.15em] text-muted-foreground transition-colors hover:text-blueprint"
              >
                Set up your Google profile first
              </Link>
            </div>
          </Reveal>
        </div>
      </article>

      <Faq items={FAQS} title="More questions on Google reviews" />
      <CtaBand />
    </main>
  )
}
