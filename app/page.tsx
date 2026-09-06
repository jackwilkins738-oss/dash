import { Hero } from '@/components/hero'
import { TrustMarquee } from '@/components/trust-marquee'
import { Transformation } from '@/components/transformation'
import { CtaBand } from '@/components/cta-band'
import { Reveal } from '@/components/reveal'

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
    <main>
      <Hero />
      <TrustMarquee />

      <section className="py-24 sm:py-32">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <Reveal className="max-w-2xl">
            <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">
              How I work
            </span>
            <h2 className="mt-4 text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
              I treat your website like you treat a job well done.
            </h2>
            <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
              Measure twice, build once, leave it right. The same standards you hold on site, applied to the thing
              that brings the next customer through the door.
            </p>
          </Reveal>

          <Reveal stagger className="mt-14 grid gap-5 md:grid-cols-3">
            {PRINCIPLES.map((p) => (
              <div
                key={p.n}
                className="group rounded-xl border border-border bg-card/40 p-7 transition-colors hover:border-blueprint/40"
              >
                <span className="font-mono text-sm text-blueprint">{p.n}</span>
                <h3 className="mt-5 text-lg font-semibold">{p.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">{p.body}</p>
              </div>
            ))}
          </Reveal>
        </div>
      </section>

      <Transformation />
      <CtaBand />
    </main>
  )
}
