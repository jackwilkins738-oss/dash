'use client'

import { Suspense } from 'react'
import dynamic from 'next/dynamic'
import { Reveal } from '@/components/reveal'

const BuildScene = dynamic(() => import('@/components/build-scene'), {
  ssr: false,
  loading: () => <div className="absolute inset-0 blueprint-grid opacity-40" />,
})

const SPECS = [
  { k: 'Foundation', v: 'Semantic HTML, zero bloat' },
  { k: 'Structure', v: 'Hand-written components' },
  { k: 'Finish', v: 'Sub-second load, 100 Lighthouse' },
]

export function BuildShowcase() {
  return (
    <section className="relative overflow-hidden border-y border-border py-24 sm:py-32">
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-5 sm:px-8 lg:grid-cols-2 lg:gap-14">
        <Reveal>
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">
            Assembled, not installed
          </span>
          <h2 className="mt-4 text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Every site is built like a structure, not dropped from a template.
          </h2>
          <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
            Drag or move your cursor to turn the model. This is how I think about your website — a proper build
            with foundations, load-bearing structure and a clean finish. Nothing bolted on that you didn&apos;t ask
            for, nothing left to rattle loose in six months.
          </p>

          <dl className="mt-10 space-y-4 border-t border-border pt-8">
            {SPECS.map((s) => (
              <div key={s.k} className="flex items-baseline justify-between gap-4">
                <dt className="font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground">
                  {s.k}
                </dt>
                <dd className="text-right text-sm text-foreground">{s.v}</dd>
              </div>
            ))}
          </dl>
        </Reveal>

        <div className="relative order-first h-[360px] w-full sm:h-[460px] lg:order-last lg:h-[520px]">
          <Suspense fallback={<div className="absolute inset-0 blueprint-grid opacity-40" />}>
            <BuildScene />
          </Suspense>
          <div className="pointer-events-none absolute bottom-3 left-1/2 -translate-x-1/2 font-mono text-[10px] uppercase tracking-[0.3em] text-muted-foreground">
            Live 3D · WebGL
          </div>
        </div>
      </div>
    </section>
  )
}
