'use client'

import { useEffect } from 'react'
import Lenis from 'lenis'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'

export function SmoothScroll() {
  useEffect(() => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) return

    // Lenis exists to turn desktop's discrete wheel-scroll deltas into
    // eased, momentum-like motion. Touch scrolling already has its own
    // native inertia from the OS - Lenis adds nothing there and can add
    // input latency by intercepting scroll on top of what's already
    // smooth. Skipping it (and the per-frame gsap.ticker binding that
    // drives it) on mobile removes real, continuous main-thread cost with
    // no change to desktop's feel at all - mobile just gets native scroll.
    const isMobile = window.matchMedia('(pointer: coarse)').matches

    gsap.registerPlugin(ScrollTrigger)

    const lenis = isMobile
      ? null
      : new Lenis({
          duration: 1.1,
          easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
          smoothWheel: true,
        })

    lenis?.on('scroll', ScrollTrigger.update)

    const raf = (time: number) => {
      lenis?.raf(time * 1000)
    }
    if (lenis) {
      gsap.ticker.add(raf)
      gsap.ticker.lagSmoothing(0)
    }

    // Lenis measures scrollable height once, at construction. Anything
    // that changes document height after that - web fonts swapping in,
    // images below the fold - leaves Lenis's virtual scroll range stale,
    // so the real bottom (the footer) becomes unreachable or flickers in
    // and out depending on load timing. Re-sync once on each of the few
    // moments height actually settles - NOT on a ResizeObserver, which
    // just fed back into itself here (refresh changes ScrollTrigger's
    // pin-spacer heights, which re-fires the observer, forever).
    // ScrollTrigger.refresh() walks and re-measures every trigger on the
    // page (there are a couple dozen Reveal instances alone) and forces a
    // layout each time - real main-thread cost, not just bookkeeping. The
    // 'load' listener and fonts.ready promise routinely settle within a
    // few ms of each other, so a same-tick call is coalesced into a
    // single refresh rather than paying that cost twice back to back.
    let resyncScheduled = false
    const resync = () => {
      if (resyncScheduled) return
      resyncScheduled = true
      queueMicrotask(() => {
        resyncScheduled = false
        lenis?.resize()
        ScrollTrigger.refresh()
      })
    }
    window.addEventListener('load', resync)
    document.fonts?.ready.then(resync)
    // Kept clear of the power-cable's own init window (~2.2s-3.5s, see
    // power-cable.tsx) - firing a refresh while that runs competes for
    // the main thread at the exact moment it's already doing ~1.3s of
    // synchronous WebGL work, and that's the stutter the settle timer
    // was itself supposed to be smoothing over.
    const settleTimer = window.setTimeout(resync, 3800)

    return () => {
      window.removeEventListener('load', resync)
      window.clearTimeout(settleTimer)
      if (lenis) gsap.ticker.remove(raf)
      lenis?.destroy()
    }
  }, [])

  return null
}
