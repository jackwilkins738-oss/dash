import { Check, X } from 'lucide-react'
import { Reveal } from '@/components/reveal'

const BAD = [
  'Loads in 6+ seconds on mobile',
  'Bloated with 30 plugins that break',
  '£40/month forever, and you never own it',
  'Looks like every other trade site',
  'Buried on page 3 of Google',
  'You wait a week for a text change',
]

const GOOD = [
  'Loads before the thumb stops scrolling',
  'Pure code. Nothing to break or update',
  'Paid once. Yours outright, forever',
  'Custom-built to make you the obvious choice',
  'Structured to rank in your town',
  'Changes done same day, straight from me',
]

export function Transformation() {
  return (
    <section className="border-t border-border py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal className="max-w-2xl">
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">The difference</span>
          <h2 className="mt-4 text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Same trade. Two very different first impressions.
          </h2>
          <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
            Your website is the quote before the quote. Here&apos;s what a typical WordPress build costs you versus a
            site built the way it should be.
          </p>
        </Reveal>

        <div className="mt-14 grid gap-5 lg:grid-cols-2">
          <Reveal className="relative overflow-hidden rounded-xl border border-border bg-card/40 p-7 sm:p-9">
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Typical WordPress site
              </span>
              <span className="rounded-full border border-destructive/40 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em] text-destructive">
                Slow
              </span>
            </div>
            <ul className="mt-7 space-y-4">
              {BAD.map((b) => (
                <li key={b} className="flex items-start gap-3 text-sm text-muted-foreground">
                  <X className="mt-0.5 h-4 w-4 shrink-0 text-destructive" strokeWidth={2.5} aria-hidden="true" />
                  <span>{b}</span>
                </li>
              ))}
            </ul>
          </Reveal>

          <Reveal
            delay={0.12}
            className="relative overflow-hidden rounded-xl border border-blueprint/40 bg-card p-7 sm:p-9"
          >
            <div
              className="pointer-events-none absolute inset-0 opacity-60"
              style={{ background: 'radial-gradient(90% 70% at 100% 0%, oklch(0.82 0.13 197 / 0.10), transparent 60%)' }}
              aria-hidden="true"
            />
            <div className="relative flex items-center justify-between">
              <span className="font-mono text-xs uppercase tracking-[0.2em] text-foreground">
                Scalar pure-code site
              </span>
              <span className="rounded-full border border-blueprint/50 px-3 py-1 font-mono text-[10px] uppercase tracking-[0.2em] text-blueprint">
                Instant
              </span>
            </div>
            <ul className="relative mt-7 space-y-4">
              {GOOD.map((g) => (
                <li key={g} className="flex items-start gap-3 text-sm text-foreground/90">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-blueprint" strokeWidth={2.5} aria-hidden="true" />
                  <span>{g}</span>
                </li>
              ))}
            </ul>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
