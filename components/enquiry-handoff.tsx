'use client'

import { useEffect, useRef, useState } from 'react'
import { Bell, Mail } from 'lucide-react'

/*
 * The one line the dash section leads with - "the site brings the lead in,
 * the dash runs the job after" - made into something a visitor watches
 * happen instead of just reads. A dot leaves the contact-form icon, travels
 * to the dashboard icon, and a real-looking "new enquiry" toast lands the
 * moment it arrives. Loops quietly while in view; stops when scrolled away.
 *
 * CSS transitions driven by a small state machine (same pattern as
 * SpeedRace), not GSAP or a JS animation loop - cheap enough to leave
 * running, and respects prefers-reduced-motion by settling on the
 * end state instead of looping.
 */

type Phase = 'form' | 'traveling' | 'arrived'

const TRAVEL_MS = 1400
const HOLD_MS = 2200
const PAUSE_MS = 900

export function EnquiryHandoff() {
  const rootRef = useRef<HTMLDivElement>(null)
  const [phase, setPhase] = useState<Phase>('form')
  const [reduced, setReduced] = useState(false)
  const timers = useRef<number[]>([])

  useEffect(() => {
    const el = rootRef.current
    if (!el) return

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    setReduced(prefersReduced)
    if (prefersReduced) {
      setPhase('arrived')
      return
    }

    const clear = () => {
      timers.current.forEach((t) => window.clearTimeout(t))
      timers.current = []
    }

    const loop = () => {
      setPhase('form')
      timers.current.push(
        window.setTimeout(() => {
          setPhase('traveling')
          timers.current.push(
            window.setTimeout(() => {
              setPhase('arrived')
              timers.current.push(window.setTimeout(loop, HOLD_MS))
            }, TRAVEL_MS),
          )
        }, PAUSE_MS),
      )
    }

    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          if (timers.current.length === 0) loop()
        } else {
          clear()
        }
      },
      { threshold: 0.4 },
    )
    io.observe(el)

    return () => {
      io.disconnect()
      clear()
    }
  }, [])

  const traveling = phase === 'traveling' || phase === 'arrived'
  const arrived = phase === 'arrived'

  return (
    <div
      ref={rootRef}
      className="relative overflow-hidden rounded-2xl border border-[#e8935e]/25 bg-card/30 px-6 py-8 sm:px-10"
      aria-hidden="true"
    >
      <div className="relative mx-auto flex max-w-md items-center justify-between">
        {/* Contact form node */}
        <div className="flex flex-col items-center gap-2">
          <span
            className={`flex h-11 w-11 items-center justify-center rounded-lg border transition-colors duration-300 ${
              phase === 'form' ? 'border-[#e8935e] bg-[#e8935e]/15 text-[#e8935e]' : 'border-border text-muted-foreground'
            }`}
          >
            <Mail className="h-5 w-5" strokeWidth={1.75} />
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">Contact form</span>
        </div>

        {/* Travel line */}
        <div className="relative mx-4 h-px flex-1 bg-border sm:mx-6">
          <span
            className="absolute top-1/2 h-2 w-2 -translate-y-1/2 rounded-full bg-[#e8935e] shadow-[0_0_8px_2px_rgba(232,147,94,0.55)] transition-[left] ease-in-out"
            style={{
              left: traveling ? 'calc(100% - 4px)' : '0%',
              transitionDuration: `${TRAVEL_MS}ms`,
              opacity: phase === 'form' ? 0 : 1,
            }}
          />
        </div>

        {/* Dashboard node */}
        <div className="relative flex flex-col items-center gap-2">
          <span
            className={`relative flex h-11 w-11 items-center justify-center rounded-lg border transition-colors duration-300 ${
              arrived ? 'border-[#e8935e] bg-[#e8935e]/15 text-[#e8935e]' : 'border-border text-muted-foreground'
            }`}
          >
            <Bell className="h-5 w-5" strokeWidth={1.75} />
            <span
              className="absolute -right-1.5 -top-1.5 flex h-4 w-4 items-center justify-center rounded-full bg-[#e8935e] font-mono text-[9px] font-bold text-[#1a0f08] transition-transform duration-300"
              style={{ transform: arrived ? 'scale(1)' : 'scale(0)' }}
            >
              1
            </span>
          </span>
          <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground">Your dashboard</span>

          {/* Toast */}
          <span
            className="absolute -top-11 left-1/2 -translate-x-1/2 whitespace-nowrap rounded-md border border-[#e8935e]/40 bg-[#171c24] px-2.5 py-1 font-mono text-[10px] text-[#f5f1e6] shadow-lg transition-all duration-300"
            style={{
              opacity: arrived ? 1 : 0,
              transform: `translate(-50%, ${arrived ? '0' : '4px'})`,
            }}
          >
            New enquiry &middot; just now
          </span>
        </div>
      </div>

      {!reduced && (
        <p className="relative mt-6 text-center text-xs text-muted-foreground">
          Not a mockup&apos;s idea of it &mdash; this is exactly what happens the moment someone submits your site&apos;s form.
        </p>
      )}
    </div>
  )
}
