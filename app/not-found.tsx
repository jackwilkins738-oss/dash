import type { Metadata } from 'next'
import Link from 'next/link'
import { PageHeader, HeaderActions } from '@/components/page-header'
import { SpeedCheck } from '@/components/speed-check'

export const metadata: Metadata = {
  title: 'Page not found',
  robots: { index: false },
}

const PLACES = [
  { href: '/work', label: 'Services & prices', note: 'What you get, from £750, fixed before we start' },
  { href: '/process', label: 'How it works', note: 'From first call to live site' },
  { href: '/guides', label: 'Guides', note: 'Costs, Google Maps, reviews, Facebook vs a website' },
  { href: '/contact', label: 'Get in touch', note: 'A reply within 2 hours in working hours' },
]

// Most people who land here followed an old or mistyped link (often an expired preview link from an
// email), so the page doesn't just apologise: it points to where they were probably heading, and
// offers the one thing on the site worth doing cold - testing their own site's speed.
export default function NotFound() {
  return (
    <main>
      <PageHeader
        eyebrow="404"
        title="That page isn't here."
        body="The link may be old or mistyped. If you were sent a preview of your new website, just reply to the email and I'll send a fresh link."
        actions={<HeaderActions secondary={{ href: '/', label: 'Back to the homepage' }} />}
      />

      <section className="border-b border-border py-14">
        <ul className="mx-auto grid max-w-6xl gap-4 px-5 sm:grid-cols-2 sm:px-8 lg:grid-cols-4">
          {PLACES.map((p) => (
            <li key={p.href}>
              <Link
                href={p.href}
                className="block h-full border border-border p-5 transition-colors hover:border-blueprint"
              >
                <span className="font-display text-lg font-semibold">{p.label}</span>
                <span className="mt-1 block text-sm text-muted-foreground">{p.note}</span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <SpeedCheck linkToFullPage />
    </main>
  )
}
