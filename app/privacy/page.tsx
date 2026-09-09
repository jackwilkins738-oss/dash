import type { Metadata } from 'next'
import { PageHeader } from '@/components/page-header'
import { Reveal } from '@/components/reveal'

export const metadata: Metadata = {
  title: 'Privacy Policy — Scalar Digital',
  description: 'What Scalar Digital collects through this site, why, and how to exercise your data rights.',
  alternates: { canonical: '/privacy' },
  robots: { index: true, follow: true },
}

const SECTIONS = [
  {
    title: 'Who this covers',
    body: (
      <>
        This policy covers scalardigital.co.uk, operated by Scalar Digital. It explains what personal data the
        site collects, why, and what rights you have over it. Scalar Digital is the data controller for the
        information described here.
      </>
    ),
  },
  {
    title: 'What’s collected, and why',
    body: (
      <>
        <p>The contact form on this site collects, depending on what you choose to fill in:</p>
        <ul className="mt-3 list-disc space-y-1 pl-5">
          <li>Your name and email address (required)</li>
          <li>Phone number, trade, project type and budget range (optional)</li>
          <li>Whatever you write in the message field</li>
        </ul>
        <p className="mt-3">
          This is used for one purpose: to reply to your enquiry with a plan and a price. It isn&apos;t used for
          marketing, sold, or shared with anyone outside the delivery of that reply.
        </p>
      </>
    ),
  },
  {
    title: 'Where it goes',
    body: (
      <>
        <p>
          When you submit the form, its contents are sent directly to Scalar Digital via Telegram, a messaging
          service used here purely as a private notification channel — not for marketing or any other purpose.
        </p>
        <p className="mt-3">
          Your name, email, phone number and message are also saved as a lead inside Scalar Digital&apos;s own
          dashboard product — the same tool built for trade-business clients — so your enquiry can be tracked and
          followed up on properly. This is an internal business tool operated by Scalar Digital, not a
          third-party marketing platform: nothing in it is sold, shared outside Scalar Digital, or used to
          contact you for anything beyond replying to what you sent.
        </p>
        <p className="mt-3">
          The site is hosted on Vercel, which processes standard web request data (like your IP address) as part
          of serving the page — this is normal for any website and isn&apos;t used to identify you personally.
        </p>
      </>
    ),
  },
  {
    title: 'Analytics',
    body: (
      <>
        <p>
          This site uses Vercel Analytics, a privacy-focused analytics tool that doesn&apos;t use cookies and
          doesn&apos;t track you individually across sites. It reports aggregated, anonymous information — which
          pages get visited, roughly how fast they load — and a small number of anonymous events (such as &quot;a
          contact form was submitted&quot; along with the trade and budget range selected, with no name or
          contact details attached). None of this can be traced back to you as an individual.
        </p>
        <p className="mt-3">
          Separately, Scalar Digital&apos;s own dashboard product (mentioned above) also logs which pages you
          visit against this site specifically, so Scalar Digital can see how its own site performs — the same
          traffic reporting every client of that product gets for their own site. This isn&apos;t shared with
          any third party.
        </p>
      </>
    ),
  },
  {
    title: 'Cookies',
    body: (
      <>
        This site doesn&apos;t use marketing or advertising cookies, and doesn&apos;t run any third-party
        tracking pixels. It has no cookie consent banner because it has nothing that needs your consent to run.
      </>
    ),
  },
  {
    title: 'How long data is kept',
    body: (
      <>
        Enquiry details are kept only for as long as needed to respond to you and, where a project goes ahead, for
        the length of that working relationship plus a reasonable period afterward for basic business
        record-keeping. If you&apos;d like anything deleted sooner, just ask — see below.
      </>
    ),
  },
  {
    title: 'Your rights',
    body: (
      <>
        <p>Under UK GDPR, you can ask to:</p>
        <ul className="mt-3 list-disc space-y-1 pl-5">
          <li>See what personal data is held about you</li>
          <li>Have inaccurate data corrected</li>
          <li>Have your data deleted</li>
          <li>Object to how it&apos;s used</li>
        </ul>
        <p className="mt-3">
          To do any of this, email{' '}
          <a href="mailto:hello@scalardigital.co.uk" className="text-blueprint underline-offset-4 hover:underline">
            hello@scalardigital.co.uk
          </a>
          . You can also complain to the UK&apos;s data protection regulator, the{' '}
          <a
            href="https://ico.org.uk/make-a-complaint/"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blueprint underline-offset-4 hover:underline"
          >
            Information Commissioner&apos;s Office (ICO)
          </a>
          , if you think your data has been mishandled.
        </p>
      </>
    ),
  },
  {
    title: 'Changes to this policy',
    body: (
      <>
        If what this site collects or how it&apos;s used changes, this page will be updated to reflect it. Last
        updated: September 2026.
      </>
    ),
  },
]

export default function PrivacyPage() {
  return (
    <main>
      <PageHeader
        eyebrow="Privacy"
        title="Privacy policy."
        body="Plain terms: what this site collects through the contact form, why, and how to get it changed or removed."
      />

      <section className="py-20 sm:py-24">
        <div className="mx-auto max-w-3xl px-5 sm:px-8">
          <div className="space-y-12">
            {SECTIONS.map((s, i) => (
              <Reveal key={s.title} delay={i * 0.03}>
                <h2 className="font-display text-xl font-semibold sm:text-2xl">{s.title}</h2>
                <div className="mt-3 text-pretty leading-relaxed text-muted-foreground">{s.body}</div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>
    </main>
  )
}
