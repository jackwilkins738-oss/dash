import Link from 'next/link'
import { Reveal } from '@/components/reveal'

// Same trades already named in the hero's opening line and the site's
// metadata keywords - this just makes it scannable instead of buried in
// a sentence, rather than introducing a new claim.
const TRADES = [
  { label: 'Resin driveways', href: '/websites-for/driveway-installers' },
  { label: 'Landscaping', href: '/websites-for/landscapers' },
  { label: 'Loft conversions', href: '/websites-for/loft-conversion-companies' },
  { label: 'House extensions', href: '/websites-for/builders-and-extension-firms' },
  { label: 'Roofing', href: '/websites-for/roofers' },
  { label: 'Renovation', href: '/websites-for/builders-and-extension-firms' },
]

export function TradesGrid() {
  return (
    <section className="border-t border-border py-20 sm:py-24">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal className="max-w-2xl">
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Built for</span>
          <h2 className="mt-4 font-display text-balance text-2xl font-bold tracking-tight sm:text-3xl">
            Trade businesses that have outgrown their website.
          </h2>
        </Reveal>

        <Reveal
          stagger
          className="mt-10 grid grid-cols-2 gap-px overflow-hidden rounded-xl border border-border bg-border sm:grid-cols-3"
        >
          {TRADES.map((trade) => (
            <Link
              key={trade.label}
              href={trade.href}
              className="group flex items-center justify-between bg-background px-6 py-6 font-mono text-sm text-foreground/90 transition-colors hover:bg-card hover:text-blueprint sm:py-7"
            >
              {trade.label}
              <span className="text-muted-foreground transition-transform group-hover:translate-x-1 group-hover:text-blueprint" aria-hidden="true">
                &rarr;
              </span>
            </Link>
          ))}
        </Reveal>

        <p className="mt-8 max-w-xl text-pretty text-sm leading-relaxed text-muted-foreground">
          If your work is premium, your website should look like it.
        </p>
      </div>
    </section>
  )
}
