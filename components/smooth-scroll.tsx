'use client'

import { useEffect } from 'react'
import Lenis from 'lenis'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

export function SmoothScroll() {
  useEffect(() => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) return

    gsap.registerPlugin(ScrollTrigger)

    const lenis = new Lenis({
      duration: 1.1,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
    })

    lenis.on('scroll', ScrollTrigger.update)

    const raf = (time: number) => {
      lenis.raf(time * 1000)
    }
    gsap.ticker.add(raf)
    gsap.ticker.lagSmoothing(0)

    // Lenis measures scrollable height once, at construction. Anything
    // that changes document height after that - web fonts swapping in,
    // images below the fold - leaves Lenis's virtual scroll range stale,
    // so the real bottom (the footer) becomes unreachable or flickers in
    // and out depending on load timing. Re-sync once on each of the few
    // moments height actually settles - NOT on a ResizeObserver, which
    // just fed back into itself here (refresh changes ScrollTrigger's
    // pin-spacer heights, which re-fires the observer, forever).
    const resync = () => {
      lenis.resize()
      ScrollTrigger.refresh()
    }
    window.addEventListener('load', resync)
    document.fonts?.ready.then(resync)
    const settleTimer = window.setTimeout(resync, 2500)

    return () => {
      window.removeEventListener('load', resync)
      window.clearTimeout(settleTimer)
      gsap.ticker.remove(raf)
      lenis.destroy()
    }
  }, [])

  return null
}
