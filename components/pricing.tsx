import type { ReactNode } from 'react'
import Link from 'next/link'
import { Check } from 'lucide-react'
import { FoundingOffer } from '@/components/founding-offer'
import { Reveal } from '@/components/reveal'
import { PRICES } from '@/lib/site'

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
    invoices and a customer portal, running under your business name. Hosted free for your first 12 months, then £{PRICES.dashboardMonthly} a month,
    optional
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

        <Reveal className="mt-10">
          <h3 className="font-display text-xl font-bold tracking-tight sm:text-2xl">After launch: optional monthly plans</h3>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-muted-foreground">
            Your site is yours either way. These keep it working for you, and you can stop any month.
          </p>
          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <PlanCard
              name="Care"
              price={PRICES.dashboardMonthly}
              note="Free for your first 12 months with the Scalar build"
              items={[
                'Your private dashboard: enquiries, quotes, jobs and invoices',
                'Your site checked every hour, and fixed if it goes down',
                'Review requests sent to customers automatically after each job',
                'A monthly report: visits, calls, enquiries and work won',
              ]}
            />
            <PlanCard
              name="Growth"
              price={PRICES.growthMonthly}
              note="Everything in Care, plus:"
              items={[
                'Every finished job written up as its own page on your site, from your photos, live once you OK it',
                'A matching post for your Google Business Profile with each one',
                'A ready-to-post reply to any Google review, good or bad, in seconds',
                'Your report shows what the new pages brought in',
              ]}
            />
          </div>
        </Reveal>

        <Reveal className="mt-6">
          <FoundingOffer href="/contact?founding=1" />
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

function PlanCard({ name, price, note, items }: { name: string; price: number; note: string; items: string[] }) {
  return (
    <div className="rounded-2xl border border-border bg-card/40 p-6 sm:p-8">
      <div className="flex items-end justify-between gap-3">
        <span className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">{name}</span>
        <span>
          <span className="text-3xl font-bold tracking-tight">£{price}</span>
          <span className="ml-1 font-mono text-xs uppercase tracking-[0.15em] text-muted-foreground">a month</span>
        </span>
      </div>
      <p className="mt-3 text-sm text-muted-foreground">{note}</p>
      <ul className="mt-4 space-y-3">
        {items.map((f) => (
          <li key={f} className="flex items-start gap-3 text-sm text-foreground/90">
            <Check className="mt-0.5 h-4 w-4 shrink-0 text-blueprint" strokeWidth={2.5} />
            <span>{f}</span>
          </li>
        ))}
      </ul>
    </div>
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
        highlighted ? 'border-blueprint/40 bg-card shadow-[0_30px_80px_-30px_oklch(0.62_0.135_244/0.55)]' : 'border-border bg-card/40'
      }`}
    >
      {highlighted && <div className="price-beam" aria-hidden="true" />}
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
              {/* One child, so a bold phrase inside the text stays inline
                  instead of becoming its own flex column. */}
              <span>{f}</span>
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
