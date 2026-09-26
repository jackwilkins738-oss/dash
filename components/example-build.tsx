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
  /** Full-width card across the grid, with room for body copy, a sign-up field and a logo mark */
  wide?: boolean
  body?: string
  mark?: string
  signupPlaceholder?: string
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
    offset: 'lg:mt-10',
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
    offset: 'lg:mt-0',
  },
  {
    slug: 'verdigris',
    label: 'verdigris — roofing, Kent & East Sussex',
    // Hosted on this same domain, not a separate pages.dev project - see
    // public/examples/verdigris-roofing/ and the rewrite in next.config.mjs.
    url: '/examples/verdigris-roofing/',
    eyebrow: 'Roofing & flashing — Kent & East Sussex',
    headline: (
      <>
        A roof that outlasts
        <br />
        <span style={{ color: '#8fd6b4' }}>the mortgage.</span>
      </>
    ),
    cta: 'Get a Fixed Price',
    bg: 'radial-gradient(120% 90% at 85% 10%, rgba(95,168,138,0.2), transparent 60%), radial-gradient(90% 70% at 10% 100%, rgba(47,77,63,0.35), transparent 55%), #0e1210',
    border: 'rgba(95,168,138,0.32)',
    glow: 'rgba(95,168,138,0.35)',
    eyebrowColor: '#8fd6b4',
    headlineColor: '#f3f1ea',
    ctaBg: 'linear-gradient(135deg, #8fd6b4, #5fa88a)',
    ctaColor: '#062015',
    dotColors: ['#5fa88a', '#2f4d3f', '#8fd6b4'],
    offset: 'lg:mt-10',
  },
  {
    slug: 'mike',
    label: 'mike — wellbeing app, product site',
    url: 'https://mike-website-c61.pages.dev/',
    eyebrow: 'Wellbeing app — product site',
    headline: (
      <>
        Your whole journey.
        <br />
        <span style={{ color: '#25D9EA' }}>One connected place.</span>
      </>
    ),
    cta: 'Join the Waitlist',
    bg: 'radial-gradient(120% 90% at 82% 8%, rgba(117,103,248,0.34), transparent 60%), radial-gradient(90% 70% at 8% 100%, rgba(37,217,234,0.18), transparent 55%), #061A2B',
    border: 'rgba(37,217,234,0.32)',
    glow: 'rgba(117,103,248,0.4)',
    eyebrowColor: '#25D9EA',
    headlineColor: '#ffffff',
    ctaBg: 'linear-gradient(90deg, #25D9EA, #7567F8)',
    ctaColor: '#061A2B',
    dotColors: ['#25D9EA', '#7567F8', '#E779E8'],
    offset: '',
    wide: true,
    body: 'MIKE helps you talk things through, understand what is affecting you and build better structure across mental wellbeing, physical health, nutrition, sleep, routine, community and life direction.',
    mark: '/examples/mike-mark.png',
    signupPlaceholder: 'you@example.com',
  },
]

export function ExampleBuild() {
  return (
    <section id="work" className="scroll-mt-20 border-t border-border py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal>
          <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Example builds</span>
          <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Not mockups. Real, working sites.
          </h2>
          <p className="mt-5 max-w-2xl text-pretty leading-relaxed text-muted-foreground">
            Five full builds, each started from a blank page rather than a theme — which is why no two look
            related. Verdigris is live on this same domain, so click through and look around properly; Mike is a
            real wellbeing app&apos;s product site; the other three are concept builds for trades.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-7 sm:grid-cols-2">
          {EXAMPLES.map((ex, i) => (
            <Reveal
              key={ex.slug}
              delay={i * 0.1}
              className={ex.wide ? 'sm:col-span-2' : `depth-drift ${ex.offset}`}
            >
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
                  className={
                    ex.wide
                      ? 'relative flex flex-col justify-center gap-8 px-8 py-12 sm:px-12 sm:py-14 lg:flex-row lg:items-center lg:justify-between lg:gap-12'
                      : 'relative flex aspect-[4/3] flex-col justify-center gap-3 px-8 sm:aspect-[16/12]'
                  }
                  style={{ background: ex.bg }}
                >
                  <div className={ex.wide ? 'flex min-w-0 max-w-xl flex-col gap-3' : 'contents'}>
                    <span
                      className="font-mono text-[10px] uppercase tracking-[0.3em]"
                      style={{ color: ex.eyebrowColor }}
                    >
                      {ex.eyebrow}
                    </span>
                    <span
                      className={
                        ex.wide
                          ? 'font-display text-[2rem] font-bold leading-[1.08] sm:text-[2.6rem]'
                          : 'font-display text-[1.7rem] font-bold leading-[1.08] sm:text-[2rem]'
                      }
                      style={{ color: ex.headlineColor }}
                    >
                      {ex.headline}
                    </span>
                    {ex.body && (
                      <span className="mt-1 text-sm leading-relaxed sm:text-base" style={{ color: 'rgba(255,255,255,0.72)' }}>
                        {ex.body}
                      </span>
                    )}
                    {ex.signupPlaceholder ? (
                      <span className="mt-3 flex w-full max-w-md flex-col gap-3 sm:flex-row sm:items-center">
                        <span
                          className="min-w-0 flex-1 truncate rounded-lg border px-4 py-2.5 text-sm"
                          style={{
                            borderColor: 'rgba(255,255,255,0.14)',
                            background: 'rgba(255,255,255,0.05)',
                            color: 'rgba(255,255,255,0.5)',
                          }}
                        >
                          {ex.signupPlaceholder}
                        </span>
                        <span
                          className="inline-flex w-fit items-center justify-center gap-2 rounded-lg px-5 py-2.5 text-sm font-semibold transition-transform group-hover:translate-x-1"
                          style={{ background: ex.ctaBg, color: ex.ctaColor }}
                        >
                          {ex.cta}
                          <ArrowUpRight className="h-3.5 w-3.5" strokeWidth={2.5} />
                        </span>
                      </span>
                    ) : (
                      <span
                        className="mt-3 inline-flex w-fit items-center gap-2 rounded px-4 py-2 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] transition-transform group-hover:translate-x-1"
                        style={{ background: ex.ctaBg, color: ex.ctaColor }}
                      >
                        {ex.cta}
                        <ArrowUpRight className="h-3 w-3" strokeWidth={2.5} />
                      </span>
                    )}
                  </div>
                  {ex.mark && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={ex.mark}
                      alt=""
                      width={300}
                      height={180}
                      loading="lazy"
                      className="order-first h-auto w-36 shrink-0 self-start drop-shadow-[0_12px_40px_rgba(117,103,248,0.45)] sm:w-44 lg:order-last lg:w-72 lg:self-center"
                    />
                  )}
                </div>
              </a>
            </Reveal>
          ))}
        </div>
      </div>
    </section>
  )
}
