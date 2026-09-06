import Link from 'next/link'
import { Reveal } from '@/components/reveal'

export function CtaBand() {
  return (
    <section className="border-t border-border">
      <div className="mx-auto max-w-6xl px-5 py-24 sm:px-8 sm:py-32">
        <Reveal className="relative overflow-hidden rounded-2xl border border-border bg-card p-8 sm:p-14">
          <div className="blueprint-grid pointer-events-none absolute inset-0 opacity-30" aria-hidden="true" />
          <div
            className="pointer-events-none absolute inset-0"
            style={{ background: 'radial-gradient(70% 120% at 100% 0%, oklch(0.82 0.13 197 / 0.14), transparent 55%)' }}
            aria-hidden="true"
          />
          <div className="relative max-w-2xl">
            <h2 className="text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
              Ready to look like the best firm in town?
            </h2>
            <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
              Tell me about your trade and the jobs you want more of. I&apos;ll come back within 2 hours with a plan
              and a fixed price. No sales call, no jargon.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Link
                href="/contact"
                className="group inline-flex items-center justify-center gap-2 rounded-full bg-blueprint px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-transform hover:scale-[1.03]"
              >
                Start your build
                <span className="transition-transform group-hover:translate-x-1">&rarr;</span>
              </Link>
              <a
                href="https://wa.me/447000000000"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center gap-2 rounded-full border border-border px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] transition-colors hover:border-blueprint hover:text-blueprint"
              >
                Message on WhatsApp
              </a>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
