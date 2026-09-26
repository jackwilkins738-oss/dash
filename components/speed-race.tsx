'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Reveal } from '@/components/reveal'
import { RACE, formatSeconds, progressAt, reached, stageAt, type Stage } from '@/lib/speedRace'

// Two phones load the same page at the same moment, in real time. The
// hand-built one is finished before the other has drawn a single pixel.
// It is the line the site already leads with ("loads before the thumb
// stops scrolling") made into something a visitor watches happen.
//
// Timing runs off a setInterval clock rather than requestAnimationFrame:
// a stopwatch needs wall-clock accuracy, not frame accuracy, and it keeps
// counting correctly in a tab that has been backgrounded.

type Phase = 'idle' | 'running' | 'done'

const TICK_MS = 50

export function SpeedRace() {
  const rootRef = useRef<HTMLDivElement>(null)
  const timer = useRef<number | undefined>(undefined)
  const [t, setT] = useState(0)
  const [phase, setPhase] = useState<Phase>('idle')

  const run = useCallback(() => {
    window.clearInterval(timer.current)
    const total = RACE.slow.done

    // Someone who has asked for less motion gets the result, not the show.
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setT(total)
      setPhase('done')
      return
    }

    const started = Date.now()
    setT(0)
    setPhase('running')
    timer.current = window.setInterval(() => {
      const elapsed = Date.now() - started
      if (elapsed >= total) {
        window.clearInterval(timer.current)
        setT(total)
        setPhase('done')
      } else {
        setT(elapsed)
      }
    }, TICK_MS)
  }, [])

  // Start by itself the first time the race is properly in view.
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

  const slowStage = stageAt(RACE.slow, t)
  const fastStage = stageAt(RACE.fast, t)
  const finished = phase === 'done'

  return (
    <section className="border-t border-border py-24 sm:py-32" aria-labelledby="race-heading">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal className="max-w-2xl">
          <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">The race</span>
          <h2
            id="race-heading"
            className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl"
          >
            Same page. Watch which one keeps your customer waiting.
          </h2>
          <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
            Both phones load the same page on the same connection, and it plays in real time. One is a typical
            page-builder site. The other is built by hand.
          </p>
        </Reveal>

        <div ref={rootRef} className="mt-14">
          <div className="race-grid">
            <RacePhone
              kind="slow"
              stage={slowStage}
              t={t}
              doneAt={RACE.slow.done}
              label="Typical page-builder site"
              finished={finished}
            />
            <span className="race-vs" aria-hidden="true">
              VS
            </span>
            <RacePhone
              kind="fast"
              stage={fastStage}
              t={t}
              doneAt={RACE.fast.done}
              label="Built by hand"
              finished={finished}
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
              {phase === 'running' ? 'Running…' : phase === 'done' ? 'Run it again' : 'Run the test'}
            </button>
            <p className="max-w-xl text-pretty text-xs leading-relaxed text-muted-foreground">
              An illustration, not a live measurement. The slow side reflects the 6+ seconds a typical page-builder
              site takes on a mid-range phone; real results vary by site and connection.
            </p>
          </div>

          <p className="sr-only" aria-live="polite">
            {finished
              ? `Result: the hand-built site finished loading in ${formatSeconds(RACE.fast.done)}. The typical page-builder site took ${formatSeconds(RACE.slow.done)}.`
              : ''}
          </p>
        </div>
      </div>
    </section>
  )
}

function RacePhone({
  kind,
  stage,
  t,
  doneAt,
  label,
  finished,
}: {
  kind: 'slow' | 'fast'
  stage: Stage
  t: number
  doneAt: number
  label: string
  finished: boolean
}) {
  const on = (s: Stage) => reached(stage, s)
  const complete = on('done')
  // A stopwatch that stops when its own page finishes: the fast one freezes
  // at its result while the other carries on counting.
  const shown = Math.min(t, doneAt)

  return (
    <div className="race-col" data-kind={kind}>
      <div className="race-phone" aria-hidden="true">
        <div className="race-bar" style={{ transform: `scaleX(${progressAt(t, doneAt)})` }} />
        <div className="race-screen">
          <span className="race-spinner" data-on={stage === 'blank'} />

          {/* The cookie banner that arrives late and shoves the page down. */}
          <div className="race-banner" data-on={kind === 'slow' && on('banner')}>
            <span>We value your privacy</span>
            <span className="race-banner-btn">Accept all</span>
          </div>

          <div className="race-content" data-shifted={kind === 'slow' && on('banner')}>
            <div className="race-head" data-on={on('header')}>
              <span className="race-mark" />
              <span className="race-name">YOUR FIRM</span>
              <span className="race-burger" />
            </div>

            <div className="race-hero">
              <div className="race-skeleton" data-off={on('hero')}>
                <span />
                <span />
                <span />
              </div>
              <div className="race-copy" data-on={on('hero')}>
                <span className="race-eyebrow">Loft conversions</span>
                <span className="race-h">More room, without the move.</span>
                <span className="race-cta">Book a survey</span>
              </div>
            </div>

            <div className="race-image" data-on={on('images')} />
            <div className="race-rows" data-on={on('images')}>
              <span />
              <span />
            </div>
          </div>
        </div>
      </div>

      <div className="race-readout">
        <span className="race-label">{label}</span>
        <span className="race-time" data-done={complete}>
          {formatSeconds(shown)}
        </span>
        <span className="race-status" data-done={complete}>
          {complete ? 'Loaded' : finished ? '' : 'Loading…'}
        </span>
      </div>
    </div>
  )
}
