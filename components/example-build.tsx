import type { CSSProperties, ReactNode } from 'react'
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
  border: string
  glow: string
  eyebrowColor: string
  headlineColor: string
  ctaBg: string
  ctaColor: string
  dotColors: [string, string, string]
  offset: string
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
    cta: 'Estimate your price',
    bg: 'radial-gradient(130% 90% at 85% 15%, rgba(233,166,74,0.18), transparent 60%), repeating-linear-gradient(rgba(233,166,74,0.055) 0 1px, transparent 1px 44px), repeating-linear-gradient(90deg, rgba(233,166,74,0.055) 0 1px, transparent 1px 44px), #14110e',
    border: 'rgba(233,166,74,0.28)',
    glow: 'rgba(233,166,74,0.35)',
    eyebrowColor: '#e9a64a',
    headlineColor: '#f2ede6',
    ctaBg: '#e9a64a',
    ctaColor: '#14110e',
    dotColors: ['#e9a64a', '#c97a2f', '#7a5a3a'],
    offset: 'lg:mt-0',
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
    cta: 'Get a price range',
    bg: 'linear-gradient(rgba(13,19,16,0.09) 1px, transparent 1px) 0 0/22px 22px, linear-gradient(90deg, rgba(13,19,16,0.09) 1px, transparent 1px) 0 0/22px 22px, #f4f6f5',
    border: 'rgba(47,191,113,0.35)',
    glow: 'rgba(47,191,113,0.3)',
    eyebrowColor: '#1c7a48',
    headlineColor: '#0d1310',
    ctaBg: '#2fbf71',
    ctaColor: '#06170d',
    dotColors: ['#2fbf71', '#1c7a48', '#0d1310'],
    offset: 'lg:mt-10',
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
    cta: 'Request a Consultation',
    bg: 'radial-gradient(120% 90% at 85% 10%, rgba(201,138,114,0.22), transparent 60%), radial-gradient(90% 70% at 5% 100%, rgba(147,95,74,0.18), transparent 55%), #170b12',
    border: 'rgba(201,138,114,0.32)',
    glow: 'rgba(201,138,114,0.35)',
    eyebrowColor: '#e3ab95',
    headlineColor: '#f3ece2',
    ctaBg: '#c98a72',
    ctaColor: '#170b12',
    dotColors: ['#c98a72', '#935f4a', '#e3ab95'],
    offset: 'lg:mt-0',
  },
  {
    slug: 'forgeandslate',
    label: 'forge & slate — kitchen fitting, Bristol',
    url: 'https://forgeandslate.pages.dev/',
    eyebrow: 'Bespoke Kitchen Fitting — Bristol & Bath',
    headline: (
      <>
        Built around
        <br />
        <span style={{ color: '#e07f5c' }}>how you actually cook.</span>
      </>
    ),
    cta: 'Book a Design Visit',
    bg: 'radial-gradient(90% 70% at 80% 100%, rgba(193,80,47,0.16), transparent 55%), linear-gradient(135deg, transparent 60%, rgba(240,239,236,0.03) 60%, rgba(240,239,236,0.03) 62%, transparent 62%), #141312',
    border: 'rgba(193,80,47,0.32)',
    glow: 'rgba(193,80,47,0.35)',
    eyebrowColor: '#e07f5c',
    headlineColor: '#f0efec',
    ctaBg: '#c1502f',
    ctaColor: '#150907',
    dotColors: ['#c1502f', '#9aa5a8', '#8a3820'],
    offset: 'lg:mt-14',
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
            Four full trade-business builds — the same lead-capture flow underneath each one, four entirely
            different trades, price points and designs. That&apos;s deliberate: every build starts from a blank
            page, not a theme, so no two client sites end up looking related.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-7 sm:grid-cols-2">
          {EXAMPLES.map((ex, i) => (
            <Reveal key={ex.slug} delay={i * 0.1} className={ex.offset}>
              <a
                href={ex.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group relative block overflow-hidden rounded-2xl border border-border transition-all duration-300 ease-out hover:-translate-y-1.5 hover:[border-color:var(--card-border)] hover:[box-shadow:0_24px_48px_-20px_var(--card-glow)]"
                style={{ '--card-border': ex.border, '--card-glow': ex.glow } as CSSProperties}
              >
                {/* Browser chrome */}
                <div className="flex items-center gap-2 border-b border-border bg-card/60 px-4 py-3">
                  {ex.dotColors.map((c, di) => (
                    <span key={di} className="h-2.5 w-2.5 rounded-full" style={{ background: c, opacity: 0.7 }} />
                  ))}
                  <span className="ml-3 truncate font-mono text-[11px] text-muted-foreground">{ex.label}</span>
                </div>
                {/* Stylised preview, evoking each live site's own palette and texture without claiming to be a screenshot */}
                <div
                  className="relative flex aspect-[4/3] flex-col justify-center gap-3 px-8 sm:aspect-[16/12]"
                  style={{ background: ex.bg }}
                >
                  <span
                    className="font-mono text-[10px] uppercase tracking-[0.3em]"
                    style={{ color: ex.eyebrowColor }}
                  >
                    {ex.eyebrow}
                  </span>
                  <span
                    className="font-display text-[1.7rem] font-bold leading-[1.08] sm:text-[2rem]"
                    style={{ color: ex.headlineColor }}
                  >
                    {ex.headline}
                  </span>
                  <span
                    className="mt-3 inline-flex w-fit items-center gap-2 rounded px-4 py-2 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] transition-transform group-hover:translate-x-1"
                    style={{ background: ex.ctaBg, color: ex.ctaColor }}
                  >
                    {ex.cta}
                    <ArrowUpRight className="h-3 w-3" strokeWidth={2.5} />
                  </span>
                </div>
              </a>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
