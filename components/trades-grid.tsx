import Link from 'next/link'
import { Reveal } from '@/components/reveal'

// Same trades already named in the hero's opening line and the site's
// metadata keywords - this just makes it scannable instead of buried in
// a sentence, rather than introducing a new claim.
//
// Set as an editorial index rather than a grid of small links: the trade
// names are the headline here, big enough that a roofer finds "Roofing"
// from across the room, and each row answers hover with a fill, a rule and
// an arrow (app/globals.css, .trade-row).
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
    <section className="border-t border-border py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <div className="grid gap-10 lg:grid-cols-12 lg:gap-16">
          <Reveal className="lg:col-span-4">
            <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Built for</span>
            <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl">
              Trade businesses that have outgrown their website.
            </h2>
            <p className="mt-5 max-w-sm text-pretty leading-relaxed text-muted-foreground">
              If your work is premium, your website should look like it.
            </p>
          </Reveal>

          <Reveal stagger as="ul" className="border-b border-border lg:col-span-8">
            {TRADES.map((trade, i) => (
              <li key={trade.label}>
                <Link href={trade.href} className="trade-row group">
                  <span className="font-mono text-xs text-muted-foreground transition-colors group-hover:text-blueprint">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <span className="trade-name font-display text-3xl font-bold tracking-tight sm:text-5xl">{trade.label}</span>
                  <span className="trade-arrow font-mono text-lg" aria-hidden="true">
                    &rarr;
                  </span>
                </Link>
              </li>
            ))}
          </Reveal>
        </div>
      </div>
    </section>
  )
}
