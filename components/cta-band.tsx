import Link from 'next/link'
import { Reveal } from '@/components/reveal'

export function CtaBand() {
  return (
    <section data-hide-action-bar className="border-t border-border">
      <div className="mx-auto max-w-6xl px-5 py-24 sm:px-8 sm:py-32">
        <Reveal spotlight className="relative overflow-hidden rounded-3xl border border-border bg-card px-7 py-12 sm:px-14 sm:py-20 lg:px-20">
          <div className="blueprint-grid pointer-events-none absolute inset-0 opacity-30" aria-hidden="true" />
          <div
            className="pointer-events-none absolute inset-0"
            style={{ background: 'radial-gradient(70% 120% at 100% 0%, oklch(0.62 0.135 244 / 0.18), transparent 55%)' }}
            aria-hidden="true"
          />
          {/* The page's last word, so it gets the page's biggest type. */}
          <div className="relative max-w-4xl">
            <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Ready when you are</span>
            <h2 className="mt-5 font-display text-balance text-4xl font-bold leading-[1.02] tracking-tight sm:text-6xl lg:text-7xl">
              Ready to look like the best firm in town?
            </h2>
            <p className="mt-6 max-w-2xl text-pretty text-base leading-relaxed text-muted-foreground sm:text-lg">
              Tell me about your trade and the jobs you want more of. I&apos;ll come back within 2 hours with a plan
              and a fixed price. No sales call, no jargon.
            </p>
            <div className="mt-10 flex flex-col gap-3 sm:flex-row sm:flex-wrap [&>*]:whitespace-nowrap">
              <Link
                href="/contact"
                data-magnetic
                className="btn-chamfer group inline-flex items-center justify-center gap-2 bg-blueprint px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background"
              >
                Start your build
                <span className="transition-transform group-hover:translate-x-1">&rarr;</span>
              </Link>
              <Link
                href="/contact#book"
                className="btn-chamfer inline-flex items-center justify-center gap-2 border border-blueprint/60 bg-blueprint/10 px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-foreground transition-colors hover:bg-blueprint hover:text-primary-foreground"
              >
                Book a 15-min call
              </Link>
              <a
                href="https://wa.me/66638306449"
                target="_blank"
                rel="noopener noreferrer"
                className="btn-chamfer inline-flex items-center justify-center gap-2 border border-border px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] transition-colors hover:border-blueprint hover:text-blueprint"
              >
                Message on WhatsApp
              </a>
            </div>
            {/* A real constraint, not manufactured urgency - no countdown, no
                "spots left" pressure. It exists to explain *why* the 2-hour
                reply and the fixed price hold up: there's only ever a few
                builds running at once. Keep this genuinely current. */}
            <p className="mt-6 flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.15em] text-muted-foreground">
              <span className="h-1.5 w-1.5 flex-none rounded-full bg-blueprint" aria-hidden="true" />
              Taking on 4 new builds a month — kept small so none of them get rushed
            </p>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
