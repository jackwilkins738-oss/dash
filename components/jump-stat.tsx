'use client'

import { useEffect, useRef } from 'react'

// Every other number on the site fades up gently with Reveal. This one
// is the single fact the whole "cut the wire" argument hinges on, so it
// gets its own treatment - a real overshoot-and-settle jump, not another
// fade, so it's the one thing on the page that's impossible to skim past.
//
// Built on the browser's own Web Animations API and an IntersectionObserver.
// It used to pull in GSAP and its ScrollTrigger plugin for this one effect,
// which was the last reason the site shipped either of them. The curve is a
// cubic-bezier whose second control point sits above 1: that overshoot is
// what makes it land past its mark and settle back, like GSAP's back.out.
const OVERSHOOT = 'cubic-bezier(0.3, 1.9, 0.5, 1)'

export function JumpStat({ value, className }: { value: string; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) return

    // Hidden until it scrolls into view.
    el.style.opacity = '0'
    let animation: Animation | undefined

    // Same trigger point as before: once its top edge is within the bottom 15%.
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return
        io.disconnect()
        animation = el.animate(
          [
            { opacity: 0, transform: 'translateY(24px) scale(0.2) rotate(-6deg)' },
            { opacity: 1, transform: 'translateY(0) scale(1) rotate(0deg)' },
          ],
          { duration: 850, easing: OVERSHOOT, fill: 'forwards' },
        )
      },
      { rootMargin: '0px 0px -15% 0px' },
    )
    io.observe(el)

    return () => {
      io.disconnect()
      animation?.cancel()
      el.style.opacity = ''
    }
  }, [])

  return (
    <span ref={ref} className={className}>
      {value}
    </span>
  )
}
