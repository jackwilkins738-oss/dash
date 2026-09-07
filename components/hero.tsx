'use client'

import Link from 'next/link'
import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { BlueprintCanvas } from '@/components/blueprint-canvas'
import { TrustBadges } from '@/components/trust-badges'

export function Hero() {
  const root = useRef<HTMLElement>(null)

  useEffect(() => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) return
    // Delay hero intro slightly so it plays as the preloader lifts
    const ctx = gsap.context(() => {
      gsap.from('.hero-stagger > *', {
        opacity: 0,
        y: 34,
        duration: 1,
        ease: 'power3.out',
        stagger: 0.12,
        delay: 2.7,
      })
    }, root)
    return () => ctx.revert()
  }, [])

  return (
    <section ref={root} className="relative flex min-h-svh items-center overflow-hidden">
      {/* Interactive canvas: desktop only for performance */}
      <div className="pointer-events-none absolute inset-0 hidden md:block">
        <BlueprintCanvas />
      </div>
      {/* Static grid fallback for mobile */}
      <div className="blueprint-grid absolute inset-0 opacity-40 md:hidden" aria-hidden="true" />
      {/* Vignette */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(120% 90% at 50% 0%, transparent 40%, var(--background) 100%), radial-gradient(80% 60% at 15% 30%, oklch(0.62 0.135 244 / 0.14), transparent 60%)',
        }}
        aria-hidden="true"
      />

      <div className="relative mx-auto w-full max-w-6xl px-5 pt-28 pb-20 sm:px-8">
        <div className="hero-stagger max-w-3xl">
          <div className="inline-flex items-center gap-2 rounded-full border border-border bg-card/50 px-4 py-1.5 backdrop-blur">
            <span className="h-1.5 w-1.5 rounded-full bg-blueprint" />
            <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground">
              Web design for high-end UK trades
            </span>
          </div>

          <h1 className="mt-7 font-display text-balance text-4xl font-bold leading-[1.05] tracking-tight sm:text-6xl lg:text-7xl">
            Websites that look more expensive than the job you&apos;re quoting.
          </h1>

          <p className="mt-6 max-w-xl text-pretty text-base leading-relaxed text-muted-foreground sm:text-lg">
            I&apos;m a tradesman who learned to code. I build fast, hand-made websites for driveway, landscaping,
            loft and extension firms who are tired of losing quality jobs to a slower, cheaper-looking rival.
          </p>

          <div className="mt-9 flex flex-col gap-3 sm:flex-row sm:items-center">
            <Link
              href="/contact"
              className="btn-chamfer group inline-flex items-center justify-center gap-2 bg-blueprint px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background"
            >
              Start your build
              <span className="transition-transform group-hover:translate-x-1">&rarr;</span>
            </Link>
            <Link
              href="/work"
              className="btn-chamfer inline-flex items-center justify-center gap-2 border border-border px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-foreground transition-colors hover:border-blueprint hover:text-blueprint"
            >
              See the work
            </Link>
          </div>

          <dl className="mt-14 grid max-w-lg grid-cols-3 gap-6 border-t border-border pt-8">
            {[
              { k: '0.4s', v: 'Average load time' },
              { k: '100', v: 'Lighthouse target' },
              { k: '£750', v: 'Fixed from' },
            ].map((s) => (
              <div key={s.v}>
                <dt className="font-mono text-2xl font-bold text-blueprint sm:text-3xl">{s.k}</dt>
                <dd className="mt-1 text-xs leading-snug text-muted-foreground">{s.v}</dd>
              </div>
            ))}
          </dl>

          <TrustBadges className="mt-8" />
        </div>
      </div>

      <div className="pointer-events-none absolute bottom-6 left-1/2 hidden -translate-x-1/2 flex-col items-center gap-2 md:flex">
        <span className="font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">Scroll</span>
        <span className="h-8 w-px bg-gradient-to-b from-blueprint to-transparent" />
      </div>
    </section>
  )
}
