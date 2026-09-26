'use client'

import { useEffect, useRef, useState } from 'react'

// The "cut the wire" argument, made something a visitor does rather than
// reads. They pick how fast they reply today, and 60 enquiries go cold in
// front of them.
//
// Every figure is from one study and nothing is interpolated between its
// published points: Oldroyd, McElheran & Elkington, "The Short Life of Online
// Sales Leads", Harvard Business Review, March 2011 (2,241 US firms audited).
//   - replying within an hour: nearly 7x as likely to qualify the lead as
//     replying an hour later, and 60x as likely as waiting 24 hours or more
//   - the average first reply, among firms that replied at all: 42 hours
// Expressed as whole enquiries out of 60 (60 / 7 ~ 9, 60 / 60 = 1) because
// people read "9 out of 60" far more accurately than "7x less likely".
const STOPS = [
  { key: 'hour', label: 'Within the hour', short: '< 1 hr', live: 60, note: 'The baseline. Every one of these is still a real conversation.' },
  { key: 'two', label: 'A couple of hours', short: '2 hrs', live: 9, note: 'Nearly 7× less likely to turn into a real conversation — for waiting one extra hour.' },
  { key: 'day', label: 'Next day', short: '24 hrs', live: 1, note: '60× less likely. By now they’ve usually booked whoever answered first.' },
  { key: 'avg', label: 'The average firm', short: '42 hrs', live: 1, note: 'The typical first reply. The customer stopped waiting a day and a half ago.' },
] as const

const TOTAL = 60

export function ReplyClock() {
  const [idx, setIdx] = useState(0)
  const [shown, setShown] = useState<number>(TOTAL)
  const shownRef = useRef<number>(TOTAL)
  const rootRef = useRef<HTMLDivElement>(null)
  const touched = useRef(false)
  const stop = STOPS[idx]

  // Count the headline number toward its new value instead of snapping, so
  // the loss registers as something happening, not a label changing.
  useEffect(() => {
    const target = stop.live
    // Reduced motion: the same frame callback, just with no duration, so the
    // number changes in one step.
    const duration = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 700
    let raf = 0
    const from = shownRef.current
    const start = performance.now()
    const tick = (now: number) => {
      const t = duration ? Math.min(1, (now - start) / duration) : 1
      const eased = 1 - Math.pow(1 - t, 3)
      const v = Math.round(from + (target - from) * eased)
      shownRef.current = v
      setShown(v)
      if (t < 1) raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [stop.live])

  // Unprompted, it plays the decay once when it first comes into view - most
  // people won't touch a slider until they've seen that it does something.
  useEffect(() => {
    const el = rootRef.current
    if (!el || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const timers: number[] = []
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return
        io.disconnect()
        ;[1, 2, 3].forEach((i) => {
          timers.push(
            window.setTimeout(() => {
              if (!touched.current) setIdx(i)
            }, 700 + i * 1300),
          )
        })
      },
      { threshold: 0.5 },
    )
    io.observe(el)
    return () => {
      io.disconnect()
      timers.forEach(clearTimeout)
    }
  }, [])

  const choose = (i: number) => {
    touched.current = true
    setIdx(i)
  }

  return (
    <div ref={rootRef} className="rc-root mx-auto mt-12 max-w-2xl text-left">
      <div className="rounded-xl border border-border bg-card/50 p-5 sm:p-8">
        <div className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-2">
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
            How fast do you reply to an enquiry?
          </p>
          <p className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground" aria-hidden="true">
            60 enquiries
          </p>
        </div>

        <div role="radiogroup" aria-label="Your usual reply time" className="mt-5 grid grid-cols-4 gap-1.5 sm:gap-2">
          {STOPS.map((s, i) => (
            <button
              key={s.key}
              type="button"
              role="radio"
              aria-checked={i === idx}
              onClick={() => choose(i)}
              onKeyDown={(e) => {
                if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
                  e.preventDefault()
                  choose(Math.min(STOPS.length - 1, idx + 1))
                } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
                  e.preventDefault()
                  choose(Math.max(0, idx - 1))
                }
              }}
              tabIndex={i === idx ? 0 : -1}
              className={`btn-chamfer-sm border px-1.5 py-2.5 text-center font-mono text-[11px] uppercase tracking-[0.1em] transition-colors sm:text-xs ${
                i === idx
                  ? 'border-blueprint bg-blueprint/15 text-foreground'
                  : 'border-border text-muted-foreground hover:border-blueprint/50 hover:text-foreground'
              }`}
            >
              {s.short}
            </button>
          ))}
        </div>

        {/* 60 enquiries. The ones still worth something stay lit; the rest go
            cold one after another, in reading order, so the eye follows it. */}
        <div className="rc-grid mt-7 grid grid-cols-12 gap-1.5 sm:grid-cols-20 sm:gap-[7px]" aria-hidden="true">
          {Array.from({ length: TOTAL }, (_, i) => (
            <span
              key={i}
              className="rc-dot"
              data-live={i < stop.live ? '' : undefined}
              style={{ ['--d' as string]: `${(TOTAL - 1 - i) * 9}ms` }}
            />
          ))}
        </div>

        <div className="mt-7 flex flex-col gap-4 border-t border-border pt-6 sm:flex-row sm:items-end sm:justify-between">
          <div aria-live="polite">
            <div className="flex items-baseline gap-2">
              <span
                className={`font-mono text-5xl font-bold tabular-nums transition-colors duration-500 sm:text-6xl ${
                  idx === 0 ? 'text-blueprint text-glow' : 'text-foreground'
                }`}
              >
                {shown}
              </span>
              <span className="font-mono text-sm text-muted-foreground">/ 60 still warm</span>
            </div>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-muted-foreground">
              <span className="font-semibold text-foreground">{stop.label}.</span> {stop.note}
            </p>
          </div>
          <p className="max-w-[15rem] font-mono text-[10px] uppercase leading-relaxed tracking-[0.12em] text-muted-foreground/70 sm:text-right">
            Source: Harvard Business Review, &ldquo;The Short Life of Online Sales Leads&rdquo;, 2011 — 2,241 firms
          </p>
        </div>
      </div>
    </div>
  )
}
