'use client'

import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

// Every other number on the site fades up gently with Reveal. This one
// is the single fact the whole "cut the wire" argument hinges on, so it
// gets its own treatment - a real overshoot-and-settle jump, not another
// fade, so it's the one thing on the page that's impossible to skim past.
export function JumpStat({ value, className }: { value: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) return

    gsap.registerPlugin(ScrollTrigger)

    const ctx = gsap.context(() => {
      gsap.set(el, { scale: 0.2, opacity: 0, y: 24, rotate: -6 })
      gsap.to(el, {
        scale: 1,
        opacity: 1,
        y: 0,
        rotate: 0,
        duration: 0.85,
        ease: 'back.out(2.6)',
        scrollTrigger: { trigger: el, start: 'top 85%', once: true },
      })
    }, ref)

    return () => ctx.revert()
  }, [])

  return (
    <span ref={ref} className={className}>
      {value}
    </span>
  )
}
