import type { ReactNode } from 'react'
import Link from 'next/link'
import { Check } from 'lucide-react'
import { Reveal } from '@/components/reveal'

const LANDING_INCLUDED: ReactNode[] = [
  'One hand-coded page, engineered to convert, not just to exist',
  'Custom design, built for your business — no templates',
  'Mobile-first, built for 90+ on Google’s mobile speed test',
  'Local search foundations built in',
  'WhatsApp, call and enquiry routing built in',
  'You own the code and the domain outright',
  '14 days of support after launch',
]

const BUILD_INCLUDED: ReactNode[] = [
  'Five hand-coded pages, including a gallery and a service-areas page',
  <>
    <strong className="font-semibold text-blueprint">Your own private dashboard</strong> — enquiries, quotes, jobs,
    invoices and a customer portal, running under your business name. Hosted free for your first 12 months
  </>,
  'Custom design, built around how your business actually wins work',
  'Mobile-first, built for 90+ on Google’s mobile speed test',
  "Local SEO built into the site's structure, not bolted on as a meta tag",
  'WhatsApp, call and enquiry routing built in',
  <>
    Google Business and reviews wired in — listings with photos get{' '}
    <strong className="font-semibold text-blueprint">42% more direction requests</strong>
  </>,
  'You own the code and the domain outright',
  '30 days of support after launch',
]

export function Pricing() {
  return (
    <section id="pricing" className="border-t border-border py-24 sm:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal className="max-w-2xl">
          <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Pricing</span>
          <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            One number, agreed before any work starts.
          </h2>
          <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
            The price reflects what&apos;s actually being built: a site engineered to win better work, and the
            system behind it that runs your enquiries, quotes and jobs. We agree the figure before a line of code
            is written, and it doesn&apos;t move once we start.
          </p>
        </Reveal>

        <Reveal stagger className="mt-14 grid gap-6 lg:grid-cols-2">
          {/* The full build is read first on purpose. It is the offer the site
              is really about, and it sets the frame the Landing Page is then
              judged in - read the other way round, £2,500 is measured against
              £750 and looks like a jump, rather than £750 being seen for what
              it is: the lighter cut of the same standard. */}
          <PriceCard
            label="The Scalar build"
            price="£2,500"
            included={BUILD_INCLUDED}
            footnote="Fixed at the outset — nothing added later"
            exampleHref="/examples/verdigris-roofing/"
            highlighted
          />
          <PriceCard
            label="Landing Page"
            price="£750"
            included={LANDING_INCLUDED}
            footnote="Fixed at the outset — nothing added later"
            exampleHref="/examples/verdigris-roofing/landing.html"
          />
        </Reveal>

        {/* The first three builds pay for proof with extras, not a discount:
            cutting the price would undo the positioning the rest of this
            section builds. The limit is real - it's the owner's own number,
            set before any client exists - so it's stated plainly, with no
            countdown or "only X left" pressure around it. */}
        <Reveal className="mt-6">
          <div
            data-spotlight
            className="relative overflow-hidden rounded-2xl border border-brass/35 bg-card/60 p-7 sm:p-9"
          >
            <div
              className="pointer-events-none absolute inset-0 opacity-60"
              style={{ background: 'radial-gradient(70% 90% at 0% 0%, oklch(0.78 0.1 80 / 0.12), transparent 60%)' }}
              aria-hidden="true"
            />
            <div className="relative grid gap-8 lg:grid-cols-[1.1fr_1fr] lg:gap-12">
              <div>
                <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-brass">
                  Founding clients &middot; The Scalar build &middot; 3 places
                </span>
                <h3 className="mt-4 font-display text-balance text-2xl font-bold tracking-tight sm:text-3xl">
                  Same price, same standard. More behind it.
                </h3>
                <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
                  The first three Scalar builds get more than anyone after them, in return for helping prove the
                  work: a short case study with your real before-and-after numbers, a 60-second video and a Google
                  review.
                </p>
                <Link
                  href="/contact?founding=1"
                  className="btn-chamfer group mt-7 inline-flex items-center justify-center gap-2 border border-brass/50 px-6 py-3 font-mono text-xs font-semibold uppercase tracking-[0.15em] text-brass transition-colors hover:bg-brass hover:text-background"
                >
                  Ask for a founding place
                  <span className="transition-transform group-hover:translate-x-1">&rarr;</span>
                </Link>
              </div>
              <ul className="space-y-4 self-center">
                {[
                  ['Dashboard hosting free for 24 months', 'Twice the usual 12, before the optional monthly fee.'],
                  [
                    'A speed guarantee',
                    '90+ on Google’s mobile speed test at launch, checked together on the live site, or the balance isn’t due.',
                  ],
                  ['First place in the build queue', 'Scheduled ahead of standard builds booked in the same month.'],
                ].map(([title, body]) => (
                  <li key={title} className="flex items-start gap-3">
                    <Check className="mt-1 h-4 w-4 shrink-0 text-brass" strokeWidth={2.5} />
                    <span>
                      <span className="block text-sm font-semibold text-foreground">{title}</span>
                      <span className="mt-0.5 block text-sm leading-relaxed text-muted-foreground">{body}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </Reveal>

        <Reveal className="mt-8">
          <p className="mx-auto max-w-2xl text-center text-sm leading-relaxed text-muted-foreground">
            Your domain name is registered in your own name and paid for by you directly to the registrar, typically
            under £15 a year. I&apos;ll help you set it up and point it at your site.
          </p>
        </Reveal>
      </div>
    </section>
  )
}

function PriceCard({
  label,
  price,
  included,
  footnote,
  exampleHref,
  highlighted = false,
}: {
  label: string
  price: string
  included: ReactNode[]
  footnote: string
  exampleHref?: string
  highlighted?: boolean
}) {
  return (
    <div
      className={`relative overflow-hidden rounded-2xl border p-8 sm:p-10 ${
        highlighted ? 'border-blueprint/40 bg-card' : 'border-border bg-card/40'
      }`}
    >
      {highlighted && (
        <div
          className="pointer-events-none absolute inset-0 opacity-70"
          style={{
            background: 'radial-gradient(80% 60% at 100% 0%, oklch(0.62 0.135 244 / 0.18), transparent 60%)',
          }}
          aria-hidden="true"
        />
      )}
      <div className="relative">
        <div className="flex items-center justify-between">
          <span className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">{label}</span>
          <span className="rounded-full border border-blueprint/50 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em] text-blueprint">
            Fixed
          </span>
        </div>

        <div className="mt-6 flex items-end gap-2">
          <span className="text-5xl font-bold tracking-tight sm:text-6xl">{price}</span>
          <span className="mb-2 font-mono text-xs uppercase tracking-[0.15em] text-muted-foreground">
            one-off
          </span>
        </div>

        <div className="my-8 h-px w-full bg-border" />

        <ul className="space-y-3.5">
          {included.map((f, i) => (
            <li key={i} className="flex items-start gap-3 text-sm text-foreground/90">
              <Check className="mt-0.5 h-4 w-4 shrink-0 text-blueprint" strokeWidth={2.5} />
              {f}
            </li>
          ))}
        </ul>

        <Link
          href="/contact"
          className={`group mt-9 inline-flex w-full items-center justify-center gap-2 px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] transition-colors ${
            highlighted
              ? 'btn-chamfer bg-blueprint text-primary-foreground hover:bg-brass hover:text-background'
              : 'btn-chamfer border border-border text-foreground hover:border-blueprint hover:text-blueprint'
          }`}
        >
          Start your build
          <span className="transition-transform group-hover:translate-x-1">&rarr;</span>
        </Link>
        {exampleHref && (
          <a
            href={exampleHref}
            target="_blank"
            rel="noopener noreferrer"
            className="mt-3 flex items-center justify-center gap-1.5 text-center text-sm text-blueprint underline-offset-4 hover:underline"
          >
            See a live example at this tier
          </a>
        )}
        <p className="mt-4 text-center font-mono text-[11px] uppercase tracking-[0.15em] text-muted-foreground">
          {footnote}
        </p>
      </div>
    </div>
  )
}
