import { ArrowUpRight } from 'lucide-react'
import { Reveal } from '@/components/reveal'

export function ExampleBuild() {
  return (
    <section className="border-t border-border py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <div className="grid gap-10 lg:grid-cols-[1fr_1.1fr] lg:items-center lg:gap-16">
          <Reveal>
            <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Example build</span>
            <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
              Not a mockup. A real, working site.
            </h2>
            <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
              Northlight is a full loft-conversion company build — a live cost calculator, a scroll-driven build
              sequence, a real enquiry flow, the lot. Built the same way yours would be: hand-coded, fast, and
              nothing borrowed from a theme.
            </p>
            <a
              href="https://main.tester-1.pages.dev/"
              target="_blank"
              rel="noopener noreferrer"
              className="group mt-8 inline-flex items-center gap-2 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-blueprint transition-colors hover:text-brass"
            >
              Visit the live site
              <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </a>
          </Reveal>

          <Reveal delay={0.1}>
            <a
              href="https://main.tester-1.pages.dev/"
              target="_blank"
              rel="noopener noreferrer"
              className="group block overflow-hidden rounded-2xl border border-border transition-colors hover:border-blueprint/40"
            >
              {/* Browser chrome */}
              <div className="flex items-center gap-2 border-b border-border bg-card/60 px-4 py-3">
                <span className="h-2.5 w-2.5 rounded-full bg-destructive/50" />
                <span className="h-2.5 w-2.5 rounded-full bg-brass/50" />
                <span className="h-2.5 w-2.5 rounded-full bg-blueprint/50" />
                <span className="ml-3 truncate font-mono text-[11px] text-muted-foreground">
                  northlight — loft conversions in Surrey
                </span>
              </div>
              {/* Stylised preview, evoking the live site's own palette without claiming to be a screenshot */}
              <div
                className="relative flex aspect-[4/3] flex-col justify-center gap-3 px-8 sm:aspect-[16/10]"
                style={{
                  background:
                    'radial-gradient(120% 90% at 85% 20%, rgba(233,166,74,0.16), transparent 60%), #14110e',
                }}
              >
                <span className="font-mono text-[10px] uppercase tracking-[0.3em]" style={{ color: '#e9a64a' }}>
                  Loft conversions &amp; extensions — Surrey
                </span>
                <span
                  className="font-display text-2xl font-bold leading-tight sm:text-4xl"
                  style={{ color: '#f2ede6' }}
                >
                  It is dark
                  <br />
                  <span style={{ color: '#e9a64a' }}>up there.</span>
                </span>
                <span
                  className="mt-2 inline-flex w-fit items-center gap-2 rounded px-4 py-2 font-mono text-[10px] font-semibold uppercase tracking-[0.15em] transition-transform group-hover:translate-x-1"
                  style={{ background: '#e9a64a', color: '#14110e' }}
                >
                  Estimate your price &rarr;
                </span>
              </div>
            </a>
          </Reveal>
        </div>
      </div>
    </section>
  )
}
