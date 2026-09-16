'use client'

import { useEffect, useRef, type ElementType, type ReactNode } from 'react'
import { cn } from '@/lib/utils'

type RevealProps = {
  children: ReactNode
  className?: string
  as?: ElementType
  /** Stagger children direct descendants instead of the element itself */
  stagger?: boolean
  delay?: number
}

// Every one of these (~25 across the site) used to be its own GSAP
// ScrollTrigger instance - real setup cost multiplied by count, plus
// three separate full-page ScrollTrigger.refresh() passes from
// smooth-scroll.tsx re-measuring every one of them. The animation itself
// is a plain fade-and-rise-into-view once, which a plain
// IntersectionObserver + CSS transition reproduces exactly - same easing
// curve, duration and stagger - without GSAP in the loop at all.
const EASE = 'cubic-bezier(0.165, 0.84, 0.44, 1)' // power3.out equivalent
const DURATION = 900

export function Reveal({
  children,
  className,
  as: Tag = 'div',
  stagger = false,
  delay = 0,
}: RevealProps) {
  const ref = useRef<HTMLElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (prefersReduced) return

    const targets = (stagger ? Array.from(el.children) : [el]) as HTMLElement[]

    for (const [i, target] of targets.entries()) {
      const targetDelay = delay + (stagger ? i * 0.09 : 0)
      target.style.opacity = '0'
      target.style.transform = 'translateY(28px)'
      target.style.transition = `opacity ${DURATION}ms ${EASE} ${targetDelay}s, transform ${DURATION}ms ${EASE} ${targetDelay}s`
    }

    // gsap's ScrollTrigger 'top 85%' fires once the element's top edge has
    // scrolled up into the bottom 15% of the viewport - matched here by
    // shrinking the observing root by the same 15% at the bottom.
    const io = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting) return
        for (const target of targets) {
          target.style.opacity = '1'
          target.style.transform = 'translateY(0)'
        }
        io.disconnect()
      },
      { rootMargin: '0px 0px -15% 0px' },
    )
    io.observe(el)

    return () => {
      io.disconnect()
      for (const target of targets) {
        target.style.opacity = ''
        target.style.transform = ''
        target.style.transition = ''
      }
    }
  }, [stagger, delay])

  return (
    <Tag ref={ref} className={cn(className)}>
      {children}
    </Tag>
  )
}
