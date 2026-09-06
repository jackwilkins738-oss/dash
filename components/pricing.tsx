import Link from 'next/link'
import { Check } from 'lucide-react'
import { Reveal } from '@/components/reveal'

const INCLUDED = [
  'Up to 5 hand-coded pages',
  'Custom design — no templates',
  'Mobile-first, sub-second load times',
  'Local SEO setup for your area',
  'WhatsApp, call and enquiry form',
  'Google Business & reviews wired in',
  'You own the code and domain outright',
  '30 days of tweaks after launch',
]

export function Pricing() {
  return (
    <section id="pricing" className="border-t border-border py-24 sm:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <div className="grid gap-12 lg:grid-cols-2 lg:items-center">
          <Reveal>
            <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Pricing</span>
            <h2 className="mt-4 text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
              One fixed price. No surprises, no monthly rental.
            </h2>
            <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
              You quote fixed prices, so I do too. £2,500 gets you a complete, hand-built website that&apos;s yours
              to keep. Bigger job — more pages, extra features? We&apos;ll agree a fixed number before a single line
              of code is written.
            </p>
            <ul className="mt-8 space-y-3">
              {[
                'No £40/month "maintenance" that never ends',
                'No being locked to my platform',
                'No hidden extras once we start',
              ].map((p) => (
                <li key={p} className="flex items-start gap-3 text-sm text-muted-foreground">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-blueprint" strokeWidth={2.5} />
                  {p}
                </li>
              ))}
            </ul>
          </Reveal>

          <Reveal delay={0.12}>
            <div className="relative overflow-hidden rounded-2xl border border-blueprint/40 bg-card p-8 sm:p-10">
              <div
                className="pointer-events-none absolute inset-0 opacity-70"
                style={{
                  background: 'radial-gradient(80% 60% at 100% 0%, oklch(0.82 0.13 197 / 0.14), transparent 60%)',
                }}
                aria-hidden="true"
              />
              <div className="relative">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
                    The Scalar build
                  </span>
                  <span className="rounded-full border border-blueprint/50 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em] text-blueprint">
                    Fixed
                  </span>
                </div>

                <div className="mt-6 flex items-end gap-2">
                  <span className="text-5xl font-bold tracking-tight sm:text-6xl">£2,500</span>
                  <span className="mb-2 font-mono text-xs uppercase tracking-[0.15em] text-muted-foreground">
                    from · one-off
                  </span>
                </div>

                <div className="my-8 h-px w-full bg-border" />

                <ul className="space-y-3.5">
                  {INCLUDED.map((f) => (
                    <li key={f} className="flex items-start gap-3 text-sm text-foreground/90">
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-blueprint" strokeWidth={2.5} />
                      {f}
                    </li>
                  ))}
                </ul>

                <Link
                  href="/contact"
                  className="group mt-9 inline-flex w-full items-center justify-center gap-2 rounded-full bg-blueprint px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-transform hover:scale-[1.02]"
                >
                  Start your build
                  <span className="transition-transform group-hover:translate-x-1">&rarr;</span>
                </Link>
                <p className="mt-4 text-center font-mono text-[11px] uppercase tracking-[0.15em] text-muted-foreground">
                  Reply within 2 hours · no sales call
                </p>
              </div>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
