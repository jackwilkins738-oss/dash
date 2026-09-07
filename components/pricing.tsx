import Link from 'next/link'
import { Check } from 'lucide-react'
import { Reveal } from '@/components/reveal'

const LANDING_INCLUDED = [
  '1 hand-coded landing page',
  'Custom design — no templates',
  'Mobile-first, sub-second load times',
  'Basic on-page SEO',
  'WhatsApp, call and enquiry form',
  'You own the code and domain outright',
  '14 days of tweaks after launch',
]

const BUILD_INCLUDED = [
  '5 hand-coded pages, including a Gallery and Service Areas page',
  'Custom design — no templates',
  'Mobile-first, sub-second load times',
  'Local SEO built into the site structure, not just a meta tag',
  'WhatsApp, call and enquiry form',
  'Google Business & reviews wired in',
  'You own the code and domain outright',
  '30 days of tweaks after launch',
]

export function Pricing() {
  return (
    <section id="pricing" className="border-t border-border py-24 sm:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal className="max-w-2xl">
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Pricing</span>
          <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Two fixed prices. No surprises, no monthly rental.
          </h2>
          <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
            You quote fixed prices, so I do too. Need a single strong page or a full site with room to show off past
            work — either way we agree the number before a single line of code is written.
          </p>
        </Reveal>

        <Reveal stagger className="mt-14 grid gap-6 lg:grid-cols-2">
          <PriceCard
            label="Landing Page"
            price="£750"
            included={LANDING_INCLUDED}
            footnote="No hidden extras once we start"
          />
          <PriceCard
            label="The Scalar build"
            price="£2,500"
            included={BUILD_INCLUDED}
            footnote="No hidden extras once we start"
            highlighted
          />
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
  highlighted = false,
}: {
  label: string
  price: string
  included: string[]
  footnote: string
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
          {included.map((f) => (
            <li key={f} className="flex items-start gap-3 text-sm text-foreground/90">
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
        <p className="mt-4 text-center font-mono text-[11px] uppercase tracking-[0.15em] text-muted-foreground">
          {footnote}
        </p>
      </div>
    </div>
  )
}
