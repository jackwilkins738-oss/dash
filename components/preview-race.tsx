'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Reveal } from '@/components/reveal'
import { RacePhone } from '@/components/speed-race'
import { formatSeconds, raceSpeedFactor, stageAt, timelineFromLcp } from '@/lib/speedRace'

// The homepage race, made personal: a Scalar build on the left, the
// prospect's own site on the right, each loading at its MEASURED time from
// the same Google mobile test (Largest Contentful Paint). The phones are an
// illustration; the two clocks are the real figures.
//
// Long times (some sites measure 20-30s) play sped up so the race never
// runs past ~8s, and the page says so - the clocks still count the true
// seconds, they just count faster.

type Phase = 'idle' | 'running' | 'done'
const TICK_MS = 50

export function PreviewRace({
  firmName,
  website,
  theirLcpMs,
  scalarLcpMs,
  scalarPage,
  scalarMeasuredOn,
  copy,
}: {
  firmName: string
  website: string
  theirLcpMs: number
  scalarLcpMs: number
  scalarPage: string
  scalarMeasuredOn: string
  /** The trade's own preview copy, so a roofer's phones show roofing. */
  copy?: { eyebrow: string; headline: string; cta: string }
}) {
  const rootRef = useRef<HTMLDivElement>(null)
  const timer = useRef<number | undefined>(undefined)
  const [t, setT] = useState(0)
  const [phase, setPhase] = useState<Phase>('idle')

  const slowest = Math.max(theirLcpMs, scalarLcpMs)
  const factor = raceSpeedFactor(slowest)
  const theirs = timelineFromLcp(theirLcpMs)
  const ours = timelineFromLcp(scalarLcpMs)

  const run = useCallback(() => {
    window.clearInterval(timer.current)
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setT(slowest)
      setPhase('done')
      return
    }
    const started = Date.now()
    setT(0)
    setPhase('running')
    timer.current = window.setInterval(() => {
      // Virtual time: real elapsed time, multiplied up for long races.
      const elapsed = (Date.now() - started) * factor
      if (elapsed >= slowest) {
        window.clearInterval(timer.current)
        setT(slowest)
        setPhase('done')
      } else {
        setT(elapsed)
      }
    }, TICK_MS)
  }, [factor, slowest])

  useEffect(() => {
    const el = rootRef.current
    if (!el) return
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return
        io.disconnect()
        run()
      },
      { threshold: 0.55 },
    )
    io.observe(el)
    return () => {
      io.disconnect()
      window.clearInterval(timer.current)
    }
  }, [run])

  const finished = phase === 'done'
  const name = firmName.toUpperCase()
  const times = Math.round((theirLcpMs / scalarLcpMs) * 10) / 10

  return (
    <section data-print="hide" className="border-t border-border py-20 sm:py-24" aria-labelledby="preview-race-heading">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal className="max-w-2xl">
          <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">
            The race
          </span>
          <h2
            id="preview-race-heading"
            className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl"
          >
            {times >= 2
              ? `Your site keeps customers waiting ${times}× longer than a Scalar build.`
              : 'Watch which one keeps your customer waiting.'}
          </h2>
          <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
            Both clocks are real: the time until the main content appears on a phone, from Google&apos;s own
            mobile test — {website} on the right, a Scalar build on the left.
          </p>
        </Reveal>

        <div ref={rootRef} className="mt-12">
          <div className="race-grid">
            <RacePhone
              kind="fast"
              stage={stageAt(ours, t)}
              t={t}
              doneAt={ours.done!}
              label="A Scalar build"
              finished={finished}
              firmName={name}
              doneLabel="Ready"
              showBanner={false}
              copy={copy}
            />
            <span className="race-vs" aria-hidden="true">
              VS
            </span>
            <RacePhone
              kind="slow"
              stage={stageAt(theirs, t)}
              t={t}
              doneAt={theirs.done!}
              label={`${website} today`}
              finished={finished}
              firmName={name}
              doneLabel="Ready"
              showBanner={false}
              copy={copy}
            />
          </div>

          <div className="mt-10 flex flex-col items-center gap-4 text-center">
            <button
              type="button"
              onClick={run}
              disabled={phase === 'running'}
              data-magnetic
              className="btn-chamfer inline-flex items-center justify-center gap-2 border border-blueprint/50 bg-blueprint/10 px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-foreground transition-colors hover:bg-blueprint hover:text-primary-foreground disabled:cursor-not-allowed disabled:opacity-50"
            >
              {phase === 'running' ? 'Running…' : phase === 'done' ? 'Run it again' : 'Run the race'}
            </button>
            <p className="max-w-xl text-pretty text-xs leading-relaxed text-muted-foreground">
              {factor > 1
                ? `Played at ${factor.toFixed(1)}× speed so it doesn’t take all day — the clocks show the real seconds. `
                : 'Plays in real time. '}
              Both measured with Google PageSpeed Insights on its mobile setting (a mid-range phone on a slow
              connection): {website} when this page was prepared, and {scalarPage} on {scalarMeasuredOn}. The
              phones are an illustration; the times are measured.
            </p>
          </div>

          <p className="sr-only" aria-live="polite">
            {finished
              ? `Result: the Scalar build showed its main content in ${formatSeconds(scalarLcpMs)}. ${website} took ${formatSeconds(theirLcpMs)}.`
              : ''}
          </p>
        </div>
      </div>
    </section>
  )
}
