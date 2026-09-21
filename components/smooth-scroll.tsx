'use client'

import { useEffect } from 'react'
import Lenis from 'lenis'

// Lenis exists to turn desktop's discrete wheel-scroll deltas into eased,
// momentum-like motion. Touch scrolling already has its own native inertia
// from the OS - Lenis adds nothing there and can add input latency by
// intercepting scroll on top of what's already smooth - so it is skipped on
// coarse pointers entirely, and under reduced-motion. Mobile gets native
// scroll.
//
// It runs its own animation loop (autoRaf). It used to be driven off GSAP's
// ticker so that it could feed ScrollTrigger, but nothing on the site uses
// ScrollTrigger any more, and dropping that pairing removed GSAP and its
// plugin from the bundle altogether (~110KB of JavaScript to download and
// evaluate before the page can respond).
export function SmoothScroll() {
  useEffect(() => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) return
    if (window.matchMedia('(pointer: coarse)').matches) return

    const lenis = new Lenis({
      duration: 1.1,
      easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
      smoothWheel: true,
      autoRaf: true,
    })

    // Lenis measures the scrollable height at construction. Anything that
    // changes document height afterwards - web fonts swapping in, images
    // below the fold - leaves its virtual range stale, and the real bottom
    // (the footer) can become unreachable or flicker in and out. Re-sync
    // once at each of the few moments height actually settles. Deliberately
    // NOT on a ResizeObserver: that fed back into itself here.
    let scheduled = false
    const resync = () => {
      if (scheduled) return
      scheduled = true
      queueMicrotask(() => {
        scheduled = false
        lenis.resize()
      })
    }
    window.addEventListener('load', resync)
    document.fonts?.ready.then(resync)
    // Kept clear of the power cable's own init window (see power-cable.tsx):
    // a resize while its ~1.3s of WebGL work runs competes for the same thread.
    const settleTimer = window.setTimeout(resync, 3800)

    return () => {
      window.removeEventListener('load', resync)
      window.clearTimeout(settleTimer)
      lenis.destroy()
    }
  }, [])

  return null
}
