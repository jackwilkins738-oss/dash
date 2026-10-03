import type { Metadata } from 'next'
import { Hero } from '@/components/hero'
import { ExampleBuild } from '@/components/example-build'
import { DashShowcase } from '@/components/dash-showcase'
import { CtaBand } from '@/components/cta-band'
import { Reveal } from '@/components/reveal'
import { ReplyClock } from '@/components/reply-clock'
import { Pricing } from '@/components/pricing'
import { TradesGrid } from '@/components/trades-grid'
import { Comparison } from '@/components/comparison'
import { SpeedRace } from '@/components/speed-race'
import { SpeedCheck } from '@/components/speed-check'
import { CaseStudies } from '@/components/case-studies'
import { CutWire } from '@/components/cut-wire'
import { withSeo } from '@/lib/seo'

// The layout's title and description, unless the monthly SEO loop has a better pair (content/seo.json).
export const metadata: Metadata = withSeo('/', {})

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
    title: 'Looked at as a system, not a page',
    body: "Before I design anything, I look at how the enquiry actually gets picked up, quoted and closed. With the full build, the site and the dashboard behind it are built to fix that whole path — not just to exist.",
  },
  {
    n: '04',
    title: 'Owned outright, forever',
    body: 'You pay once. The code, the domain, the lot — it belongs to you. No monthly rental on your website, no being held hostage when you want a change.',
  },
]

export default function HomePage() {
  return (
    <main className="relative isolate">
      {/* The order is the argument. Promise (hero), then proof before anything
          else is claimed (real builds), then "this is for me" (trades), then
          what actually sets the offer apart (the dashboard), then what waiting
          costs, proof the visitor runs themselves (race, their own speed
          test), the contrast, how the work is done, and only then the price
          - by which point it is being weighed against everything above it,
          not read cold. */}
      <Hero />
      <ExampleBuild />
      <CaseStudies />
      <TradesGrid />
      <DashShowcase />
      <section className="relative border-y border-border py-24 sm:py-32">
        <div className="px-5 sm:px-8">
          <CutWire />
        </div>
        <div className="mx-auto max-w-2xl px-5 text-center sm:px-8">
          <Reveal>
            <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">
              It&apos;s called a lead for a reason
            </span>
            <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
              Cut the wire and it&apos;s dead in seconds. Same with an enquiry.
            </h2>
            <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
              The average business takes <strong className="font-semibold text-foreground">42 hours</strong> to
              reply to a website enquiry. Most customers don&apos;t wait that long —{' '}
              <strong className="font-semibold text-foreground">78%</strong> hire whichever company gets back to
              them first, not whoever&apos;s better. Watch what the wait costs.
            </p>
          </Reveal>
          <ReplyClock />
          <Reveal>
            <p className="mx-auto mt-10 max-w-xl text-pretty leading-relaxed text-foreground/90">
              Every site I build puts the enquiry on your phone the second it lands, so the fast reply is the
              easy one.
            </p>
          </Reveal>
        </div>
      </section>
      <SpeedRace />
      <SpeedCheck linkToFullPage />
      <Comparison />
      {/* An editorial spread rather than another card grid: the argument stays
          pinned on the left while the four principles pass on the right, each
          coming up to full strength as it reaches the middle of the screen
          (app/globals.css, .principle). */}
      <section className="border-t border-border py-24 sm:py-32">
        <div className="mx-auto grid max-w-6xl gap-12 px-5 sm:px-8 lg:grid-cols-12 lg:gap-16">
          <div className="lg:col-span-5">
            <Reveal className="lg:sticky lg:top-32">
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">
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
          </div>

          <ol className="lg:col-span-7">
            {PRINCIPLES.map((p) => (
              <li key={p.n} className="principle grid grid-cols-[auto_1fr] gap-x-6 border-t border-border py-9 first:border-t-0 first:pt-0 sm:gap-x-10 sm:py-12">
                <span className="font-mono text-sm text-blueprint sm:pt-2">{p.n}</span>
                <div>
                  <h3 className="font-display text-2xl font-semibold tracking-tight sm:text-3xl">{p.title}</h3>
                  <p className="mt-4 max-w-lg text-pretty text-base leading-relaxed text-muted-foreground">{p.body}</p>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <Pricing />
      <CtaBand />
    </main>
  )
}
