import { Reveal } from '@/components/reveal'

// Same trades already named in the hero's opening line and the site's
// metadata keywords - this just makes it scannable instead of buried in
// a sentence, rather than introducing a new claim.
const TRADES = ['Resin driveways', 'Landscaping', 'Loft conversions', 'House extensions', 'Roofing', 'Renovation']

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
            <div key={trade} className="bg-background px-6 py-6 font-mono text-sm text-foreground/90 sm:py-7">
              {trade}
            </div>
          ))}
        </Reveal>

        <p className="mt-8 max-w-xl text-pretty text-sm leading-relaxed text-muted-foreground">
          If your work is premium, your website should look like it.
        </p>
      </div>
    </section>
  )
}
