import type { ReactNode } from 'react'
import { ArrowUpRight } from 'lucide-react'
import { Reveal } from '@/components/reveal'

type Example = {
  slug: string
  label: string
  url: string
  eyebrow: string
  headline: ReactNode
  cta: string
  bg: string
  eyebrowColor: string
  headlineColor: string
  ctaBg: string
  ctaColor: string
}

const EXAMPLES: Example[] = [
  {
    slug: 'northlight',
    label: 'northlight — loft conversions in Surrey',
    url: 'https://northlight-5rq.pages.dev/',
    eyebrow: 'Loft conversions & extensions — Surrey',
    headline: (
      <>
        It is dark
        <br />
        <span style={{ color: '#e9a64a' }}>up there.</span>
      </>
    ),
    cta: 'Estimate your price →',
    bg: 'radial-gradient(120% 90% at 85% 20%, rgba(233,166,74,0.16), transparent 60%), #14110e',
    eyebrowColor: '#e9a64a',
    headlineColor: '#f2ede6',
    ctaBg: '#e9a64a',
    ctaColor: '#14110e',
  },
  {
    slug: 'skyline',
    label: 'skyline — loft conversions in West Yorkshire',
    url: 'https://skyline-8e1.pages.dev/',
    eyebrow: 'Loft conversions — Leeds & West Yorkshire',
    headline: (
      <>
        Your loft has been
        <br />
        <span style={{ color: '#1c7a48' }}>wasted long enough.</span>
      </>
    ),
    cta: 'Get a price range →',
    bg: 'linear-gradient(#d7ded9 1px, transparent 1px) 0 0/20px 20px, linear-gradient(90deg, #d7ded9 1px, transparent 1px) 0 0/20px 20px, #f4f6f5',
    eyebrowColor: '#1c7a48',
    headlineColor: '#0d1310',
    ctaBg: '#2fbf71',
    ctaColor: '#06170d',
  },
  {
    slug: 'aldermere',
    label: 'aldermere — house extensions, Oxfordshire',
    url: 'https://aldermere.pages.dev/',
    eyebrow: 'Bespoke Extensions — Oxfordshire & the Cotswolds',
    headline: (
      <>
        Where the house
        <br />
        <span style={{ color: '#e3ab95', fontStyle: 'italic' }}>should have always ended.</span>
      </>
    ),
    cta: 'Request a Consultation →',
    bg: 'radial-gradient(120% 90% at 85% 15%, rgba(201,138,114,0.18), transparent 60%), #170b12',
    eyebrowColor: '#e3ab95',
    headlineColor: '#f3ece2',
    ctaBg: '#c98a72',
    ctaColor: '#170b12',
  },
]

export function ExampleBuild() {
  return (
    <section className="border-t border-border py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal>
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Example builds</span>
          <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Not mockups. Real, working sites.
          </h2>
          <p className="mt-5 max-w-2xl text-pretty leading-relaxed text-muted-foreground">
            Three full trade-business builds — the same lead-capture flow underneath each one, three entirely
            different designs and price points. That&apos;s deliberate: every build starts from a blank page, not
            a theme, so no two client sites end up looking related.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {EXAMPLES.map((ex, i) => (
            <Reveal key={ex.slug} delay={i * 0.1}>
              <a
                href={ex.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group block overflow-hidden rounded-2xl border border-border transition-colors hover:border-blueprint/40"
              >
                {/* Browser chrome */}
                <div className="flex items-center gap-2 border-b border-border bg-card/60 px-4 py-3">
                  <span className="h-2.5 w-2.5 rounded-full bg-destructive/50" />
                  <span className="h-2.5 w-2.5 rounded-full bg-brass/50" />
                  <span className="h-2.5 w-2.5 rounded-full bg-blueprint/50" />
                  <span className="ml-3 truncate font-mono text-[11px] text-muted-foreground">{ex.label}</span>
                </div>
                {/* Stylised preview, evoking each live site's own palette without claiming to be a screenshot */}
                <div
                  className="relative flex aspect-[4/3] flex-col justify-center gap-3 px-8 sm:aspect-[16/11]"
                  style={{ background: ex.bg }}
                >
                  <span
                    className="font-mono text-[10px] uppercase tracking-[0.3em]"
                    style={{ color: ex.eyebrowColor }}
                  >
                    {ex.eyebrow}
                  </span>
                  <span
                    className="font-display text-2xl font-bold leading-tight sm:text-3xl"
                    style={{ color: ex.headlineColor }}
                  >
                    {ex.headline}
                  </span>
                  <span
                    className="mt-2 inline-flex w-fit items-center gap-2 rounded px-4 py-2 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] transition-transform group-hover:translate-x-1"
                    style={{ background: ex.ctaBg, color: ex.ctaColor }}
                  >
                    {ex.cta}
                  </span>
                </div>
              </a>
              <a
                href={ex.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group mt-4 inline-flex items-center gap-2 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-blueprint transition-colors hover:text-brass"
              >
                Visit the live site
                <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
              </a>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
