import Image from 'next/image'
import { Reveal } from '@/components/reveal'

const CASES = [
  {
    img: '/work/resin-driveways.png',
    alt: 'Premium resin-bound driveway in front of a modern home at dusk',
    client: 'Meridian Resin',
    trade: 'Resin Driveways · Cheshire',
    metric: '23 enquiries in month one',
    tags: ['5-page site', 'Local SEO', 'WhatsApp'],
  },
  {
    img: '/work/landscaping.png',
    alt: 'Contemporary landscaped garden with porcelain paving lit at twilight',
    client: 'Fold & Field',
    trade: 'Landscaping · Surrey',
    metric: 'Booked out 4 months ahead',
    tags: ['7-page site', 'Gallery', 'SEO'],
  },
  {
    img: '/work/loft-conversion.png',
    alt: 'Modern loft conversion bedroom with skylights and timber beams',
    client: 'Upward Lofts',
    trade: 'Loft Conversions · London',
    metric: '£140k pipeline in 90 days',
    tags: ['6-page site', 'Quote form', 'WhatsApp'],
  },
  {
    img: '/work/extension.png',
    alt: 'Modern glass and brick rear house extension glowing at dusk',
    client: 'Baseline Builds',
    trade: 'Extensions · Manchester',
    metric: 'Cost-per-lead down 71%',
    tags: ['5-page site', 'Local SEO', 'Blog'],
  },
  {
    img: '/work/roofing.png',
    alt: 'Newly installed slate roof on a period property under a dramatic sky',
    client: 'Apex Roofline',
    trade: 'Roofing · Leeds',
    metric: '18 quotes a week, on autopilot',
    tags: ['4-page site', 'Reviews', 'WhatsApp'],
  },
  {
    img: '/work/renovation.png',
    alt: 'Luxury modern open-plan kitchen renovation with marble island',
    client: 'Grainhouse Interiors',
    trade: 'Renovations · Bristol',
    metric: 'Average job value up 40%',
    tags: ['8-page site', 'Gallery', 'SEO'],
  },
]

export function Work() {
  return (
    <section id="work" className="border-t border-border py-24 sm:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal className="max-w-2xl">
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Selected work</span>
          <h2 className="mt-4 text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Sites that paid for themselves in weeks.
          </h2>
          <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
            A few of the trades I&apos;ve built for. Different jobs, same result: a website that quietly out-sells
            everything the competition put up.
          </p>
        </Reveal>

        <Reveal stagger className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {CASES.map((c) => (
            <article
              key={c.client}
              className="group flex flex-col overflow-hidden rounded-xl border border-border bg-card/40 transition-colors hover:border-blueprint/40"
            >
              <div className="relative aspect-[4/3] overflow-hidden">
                <Image
                  src={c.img || '/placeholder.svg'}
                  alt={c.alt}
                  fill
                  sizes="(max-width: 640px) 100vw, (max-width: 1024px) 50vw, 33vw"
                  className="object-cover transition-transform duration-700 group-hover:scale-105"
                />
                <div
                  className="pointer-events-none absolute inset-0 bg-gradient-to-t from-card via-card/10 to-transparent"
                  aria-hidden="true"
                />
                <div className="absolute inset-x-4 bottom-4 flex flex-wrap gap-2">
                  {c.tags.map((t) => (
                    <span
                      key={t}
                      className="rounded-full border border-white/15 bg-background/70 px-2.5 py-1 font-mono text-[10px] uppercase tracking-[0.15em] text-foreground/90 backdrop-blur"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              </div>

              <div className="flex flex-1 flex-col p-6">
                <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                  {c.trade}
                </div>
                <h3 className="mt-2 text-lg font-semibold">{c.client}</h3>
                <div className="mt-auto flex items-baseline gap-2 border-t border-border pt-4">
                  <span className="text-blueprint" aria-hidden="true">
                    &#8599;
                  </span>
                  <span className="text-sm font-medium text-foreground/90">{c.metric}</span>
                </div>
              </div>
            </article>
          ))}
        </Reveal>
      </div>
    </section>
  )
}
