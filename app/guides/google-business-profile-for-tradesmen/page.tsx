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

const PATH = '/guides/google-business-profile-for-tradesmen'
const PUBLISHED = '2026-09-28'
const TITLE = 'How to Get Your Trade Business on Google Maps: a Google Business Profile Guide'
const DESCRIPTION =
  'Setting up and getting the most from a free Google Business Profile as a UK tradesperson: service areas, verification, categories, photos and reviews, and the mistakes that get profiles suspended.'

export const metadata: Metadata = withSeo(PATH, {
  title: 'Google Business Profile for Tradesmen: UK Guide',
  description: DESCRIPTION,
  alternates: { canonical: PATH },
  openGraph: { title: `${TITLE} | ${SITE.name}`, description: DESCRIPTION, url: PATH, type: 'article' },
})

const STEPS = [
  {
    title: 'Claim or create the profile',
    body: 'Go to business.google.com and search for your business name. If a profile already exists (Google sometimes makes one from public information), claim it rather than starting another. Duplicates split your reviews and can get both taken down.',
  },
  {
    title: 'Set yourself up as a service-area business',
    body: 'If you work at customers’ homes rather than having a shop they visit, choose to hide your address and list the towns and areas you cover instead. Only list places you genuinely work. Your profile tends to show best near where you’re based either way.',
  },
  {
    title: 'Pick the most specific primary category',
    body: '“Roofing contractor” beats “Contractor”; “Electrician” beats “Home services”. The primary category is one of the strongest signals Google uses to decide which searches you appear for. Add a few genuinely relevant extra categories, not every one that sounds close.',
  },
  {
    title: 'Verify it',
    body: 'Google chooses the method, and it’s often a short video showing your van, tools, signage or proof of the business. Until you’re verified, your changes may not show. Have the evidence ready before you start the recording.',
  },
  {
    title: 'Fill in everything',
    body: 'Phone number, opening hours, your website, a list of your services and a plain description of what you do and where. A complete profile gives Google more to match against, and gives customers fewer reasons to ring someone else.',
  },
  {
    title: 'Add real photos, and keep adding them',
    body: 'Finished jobs, work in progress, your van, you and your team. Photos taken on your phone of real work do better with customers than stock images, which they can spot a mile off.',
  },
]

const FAQS: QA[] = [
  {
    q: 'Is Google Business Profile free?',
    a: 'Yes. Creating and running the profile costs nothing. Google does sell ads that can appear alongside it, but you don’t need them to have a profile or to show up on the map.',
  },
  {
    q: 'Can I have a profile if I work from home?',
    a: 'Yes. Set it up as a service-area business and hide your home address. Customers see the areas you cover, not where you live.',
  },
  {
    q: 'Should I put keywords in my business name?',
    a: 'No. Your name on the profile should be your real business name as it appears on your van, invoices and signage. Adding extra words such as “Best Roofer Guildford” is against Google’s guidelines and a common reason profiles get suspended.',
  },
  {
    q: 'How does Google decide who shows on the map?',
    a: 'Google says it looks at three things: relevance (how well your profile matches the search), distance (how far you are from the searcher or the place they searched for) and prominence (how well known you are, which includes your reviews and your website). You can’t change distance, so the other two are where the work goes.',
  },
  {
    q: 'Do I still need a website if I have a Google profile?',
    a: 'The profile gets you found; the website is where many customers go next to check you out before they ring. Google also counts your website towards prominence, and a profile with a link to a fast, clear site gives a customer far more reason to choose you.',
  },
]

export default function GoogleBusinessProfileGuide() {
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
      <Breadcrumbs items={[{ name: 'Guides', href: '/guides' }, { name: 'Google Business Profile', href: PATH }]} />
      <PageHeader compact
        eyebrow="Guide · UK 2026"
        title="How to get your trade business on Google Maps."
        body="The free Google Business Profile, set up properly: what to fill in, what to leave out, and what gets profiles suspended."
      />

      <article className="py-20 sm:py-24">
        <div className="mx-auto max-w-3xl px-5 sm:px-8">
          <Reveal>
            <div className="rounded-2xl border border-blueprint/40 bg-card p-7">
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">The short answer</span>
              <p className="mt-3 text-pretty leading-relaxed text-foreground/90">
                Create a free profile at business.google.com, set it up as a service-area business with the towns you
                really cover, choose the most specific category for your trade, verify it, and fill in every field.
                Then keep it alive with real photos and a steady flow of reviews. It’s the single most useful free
                thing a local trade can do online.
              </p>
            </div>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">Setting it up, step by step</h2>
          </Reveal>
          <ol className="mt-8 space-y-6">
            {STEPS.map((s, i) => (
              <li key={s.title} className="flex gap-5">
                <span className="font-mono text-sm text-blueprint">{String(i + 1).padStart(2, '0')}</span>
                <div>
                  <h3 className="font-display text-xl font-semibold">{s.title}</h3>
                  <p className="mt-2 text-pretty leading-relaxed text-muted-foreground">{s.body}</p>
                </div>
              </li>
            ))}
          </ol>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">What gets profiles suspended</h2>
            <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
              Google suspends profiles it thinks break its guidelines, often without much explanation, and getting one
              back can take weeks. Avoid:
            </p>
            <ul className="mt-5 list-disc space-y-3 pl-5 text-pretty leading-relaxed text-muted-foreground marker:text-blueprint">
              <li>Extra keywords or town names added to your business name.</li>
              <li>A virtual office or a mail-forwarding address shown as your location.</li>
              <li>More than one profile for the same business.</li>
              <li>Reviews you’ve written yourself, paid for, or swapped with other firms.</li>
              <li>Changing lots of key details (name, category, address) at once, which can trigger a re-check.</li>
            </ul>
          </Reveal>

          <Reveal className="mt-14">
            <h2 className="font-display text-balance text-3xl font-bold tracking-tight">Keeping it working for you</h2>
            <ul className="mt-6 space-y-4 text-pretty leading-relaxed text-muted-foreground">
              <li>
                <strong className="text-foreground">Ask every customer for a review.</strong> Reviews feed prominence,
                and they’re what people read before they ring.{' '}
                <Link href="/guides/how-to-get-more-google-reviews" className="text-blueprint underline-offset-4 hover:underline">
                  How to get more of them, within the rules
                </Link>
                .
              </li>
              <li>
                <strong className="text-foreground">Reply to every review</strong>, good and bad, briefly and
                politely. Future customers read the replies as much as the reviews.
              </li>
              <li>
                <strong className="text-foreground">Answer the phone number on it.</strong> A profile that sends
                calls to voicemail is sending work to whoever picks up next.
              </li>
              <li>
                <strong className="text-foreground">Link it to a website that loads fast on a phone.</strong> Most
                people who tap through are on mobile data, often standing in the room that needs the work.
              </li>
            </ul>
          </Reveal>

          <Reveal className="mt-14 rounded-2xl border border-border bg-card/40 p-7">
            <h2 className="font-display text-2xl font-bold tracking-tight">Where Scalar Digital fits</h2>
            <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
              Your profile gets you found; your website wins the call. The full build wires your Google profile and
              reviews into the site, and the dashboard behind it can ask each finished customer for a Google review
              automatically, so it happens every time and not just when you remember.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                href="/work"
                className="group inline-flex items-center gap-2 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-blueprint transition-colors hover:text-brass"
              >
                See what&apos;s included
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
            </div>
          </Reveal>
        </div>
      </article>

      <Faq items={FAQS} path={PATH} title="More questions on Google Business Profile" />
      <CtaBand />
    </main>
  )
}
