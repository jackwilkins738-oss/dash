'use client'

import { useEffect } from 'react'
import { usePathname } from 'next/navigation'
import {
  REVEAL_ROOT_MARGIN,
  clearReveal,
  hideForReveal,
  shouldAnimate,
  showRevealed,
} from '@/lib/reveal'

// Performs every <Reveal> on the page (see reveal.tsx) with one shared
// IntersectionObserver.
//
// The animation is a plain fade-and-rise the first time an element scrolls
// into view. It used to be a GSAP ScrollTrigger per instance, then a client
// component per instance; this replaces the ~55 of them with a single
// observer and a single React boundary. The easing, duration, stagger and
// trigger point are unchanged, and the rules for them live in lib/reveal.ts,
// where they are tested.
export function RevealController() {
  // Re-runs on every route change: a client-side navigation brings a whole new
  // page's worth of elements that this effect has not seen.
  const pathname = usePathname()

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const pending = new Set<HTMLElement>()
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue
          const el = entry.target as HTMLElement
          io.unobserve(el)
          pending.delete(el)
          showRevealed(el)
        }
      },
      { rootMargin: REVEAL_ROOT_MARGIN },
    )

    // Read everything first, then write. Measuring an element and then styling
    // it inside one loop makes every following measurement force the browser to
    // redo layout that the previous write just invalidated - for ~25 elements
    // that is ~25 full layouts back to back instead of one, and it measured as
    // a doubling of Total Blocking Time. All the reads happen together (one
    // layout), then all the writes (which the browser batches into the next).
    const elements = Array.from(document.querySelectorAll<HTMLElement>('[data-reveal]'))
    const tops = elements.map((el) => el.getBoundingClientRect().top)
    const viewportHeight = window.innerHeight
    elements.forEach((el, i) => {
      if (!shouldAnimate(tops[i], viewportHeight)) return
      hideForReveal(el)
      pending.add(el)
      io.observe(el)
    })

    return () => {
      io.disconnect()
      for (const el of pending) clearReveal(el)
    }
  }, [pathname])

  return null
}
