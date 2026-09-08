import { Hero } from '@/components/hero'
import { TrustMarquee } from '@/components/trust-marquee'
import { PowerCable } from '@/components/power-cable-loader'
import { Transformation } from '@/components/transformation'
import { ExampleBuild } from '@/components/example-build'
import { CtaBand } from '@/components/cta-band'
import { Reveal } from '@/components/reveal'
import { JumpStat } from '@/components/jump-stat'
import { TradesGrid } from '@/components/trades-grid'
import { Comparison } from '@/components/comparison'

const PRINCIPLES = [
  {
    n: '01',
    title: 'Built by hand, line by line',
    body: 'No page-builders, no themes, no plugins waiting to break. Every site is written from scratch so it does exactly what your customers need and nothing that slows them down.',
  },
  {
    n: '02',
    title: 'Made to win the good jobs',
    body: 'Anyone can get a lead. The point is to look like the firm worth £8k, not the one worth £800. Your site is engineered to make the right customer stop scrolling and call you.',
  },
  {
    n: '03',
    title: 'Owned outright, forever',
    body: 'You pay once. The code, the domain, the lot — it belongs to you. No monthly rental, no being held hostage when you want a change.',
  },
]

export default function HomePage() {
  return (
    <main className="relative isolate">
      <PowerCable />
      <Hero />
      <TrustMarquee />
      <TradesGrid />

      <section className="py-24 sm:py-32">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <Reveal className="max-w-2xl">
            <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">
              How I work
            </span>
            <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
              I treat your website like you treat a job well done.
            </h2>
            <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
              Measure twice, build once, leave it right. The same standards you hold on site, applied to the thing
              that brings the next customer through the door.
            </p>
          </Reveal>

          {/* Asymmetric - the founding principle gets real weight, not
              equal billing with a uniform 3-up card grid. */}
          <Reveal stagger className="mt-14 grid gap-5 md:grid-cols-2">
            <div className="group rounded-xl border border-border bg-card/40 p-8 transition-colors hover:border-blueprint/40 md:p-10">
              <span className="font-mono text-sm text-blueprint">{PRINCIPLES[0].n}</span>
              <h3 className="mt-5 font-display text-2xl font-semibold sm:text-3xl">{PRINCIPLES[0].title}</h3>
              <p className="mt-4 max-w-md text-base leading-relaxed text-muted-foreground">{PRINCIPLES[0].body}</p>
            </div>
            <div className="flex flex-col gap-5">
              {PRINCIPLES.slice(1).map((p) => (
                <div
                  key={p.n}
                  className="group rounded-xl border border-border bg-card/40 p-6 transition-colors hover:border-blueprint/40"
                >
                  <span className="font-mono text-sm text-blueprint">{p.n}</span>
                  <h3 className="mt-4 font-display text-lg font-semibold">{p.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{p.body}</p>
                </div>
              ))}
            </div>
          </Reveal>
        </div>
      </section>

      <section data-wire-section className="relative border-y border-border py-24 sm:py-32">
        <div className="mx-auto max-w-2xl px-5 text-center sm:px-8">
          <Reveal>
            <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">
              It&apos;s called a lead for a reason
            </span>
            <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
              Cut the wire and it&apos;s dead in seconds. Same with an enquiry.
            </h2>
            <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
              The average business takes <strong className="font-semibold text-foreground">42 hours</strong> to
              reply to a website enquiry. Most customers don&apos;t wait that long —{' '}
              <strong className="font-semibold text-foreground">78%</strong> hire whichever company gets back to
              them first, not whoever&apos;s better. Every site I build gets your enquiries to you the second they
              land, so that&apos;s never the job you lose.
            </p>

            <div className="mx-auto mt-12 flex max-w-lg items-center justify-center gap-6 border-t border-border pt-10 sm:gap-10">
              <div className="text-center">
                <div className="font-mono text-3xl font-bold text-muted-foreground/50 line-through decoration-2 sm:text-4xl">
                  42 hrs
                </div>
                <div className="mt-2 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  Average business
                </div>
              </div>
              <span className="text-2xl text-muted-foreground/40" aria-hidden="true">
                &rarr;
              </span>
              <div className="text-center">
                <JumpStat
                  value="<2 hrs"
                  className="inline-block font-mono text-4xl font-bold text-blueprint text-glow sm:text-5xl"
                />
                <div className="mt-2 font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                  Every site I build
                </div>
              </div>
            </div>
          </Reveal>
        </div>
      </section>
      <Comparison />
      <Transformation />
      <ExampleBuild />
      <CtaBand />
    </main>
  )
}
