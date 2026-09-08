import { Check, X } from 'lucide-react'
import { Reveal } from '@/components/reveal'

const ROWS: [string, string][] = [
  ['A template, styled to look custom', 'Hand-coded from a blank file'],
  ['Generic copy dropped in around stock photos', 'Written around your actual jobs and customers'],
  ['Loads slow enough that people leave first', 'Built to load before they think to hit back'],
  ['Built to exist', 'Built to convert'],
]

export function Comparison() {
  return (
    <section className="border-t border-border py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal className="max-w-2xl">
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">The difference</span>
          <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Your website is either winning the job, or making you look like everyone else.
          </h2>
        </Reveal>

        <Reveal className="mt-14 overflow-hidden rounded-2xl border border-border">
          <div className="grid grid-cols-2 border-b border-border bg-card/60">
            <div className="flex items-center gap-2 px-5 py-4 sm:px-8">
              <X className="h-4 w-4 shrink-0 text-muted-foreground" strokeWidth={2.5} />
              <span className="font-mono text-xs uppercase tracking-[0.15em] text-muted-foreground sm:text-sm">
                Typical trade website
              </span>
            </div>
            <div className="flex items-center gap-2 border-l border-border px-5 py-4 sm:px-8">
              <Check className="h-4 w-4 shrink-0 text-blueprint" strokeWidth={2.5} />
              <span className="font-mono text-xs uppercase tracking-[0.15em] text-blueprint sm:text-sm">
                A Scalar build
              </span>
            </div>
          </div>
          {ROWS.map(([against, forIt], i) => (
            <div key={i} className={`grid grid-cols-2 ${i !== ROWS.length - 1 ? 'border-b border-border' : ''}`}>
              <div className="px-5 py-5 text-sm leading-relaxed text-muted-foreground sm:px-8">{against}</div>
              <div className="border-l border-border bg-blueprint/[0.04] px-5 py-5 text-sm leading-relaxed text-foreground/90 sm:px-8">
                {forIt}
              </div>
            </div>
          ))}
        </Reveal>
      </div>
    </section>
  )
}
