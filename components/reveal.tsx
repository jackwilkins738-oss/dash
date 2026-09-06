'use client'

import { useEffect, useRef, type ElementType, type ReactNode } from 'react'
import { gsap } from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { cn } from '@/lib/utils'

type RevealProps = {
  children: ReactNode
  className?: string
  as?: ElementType
  /** Stagger children direct descendants instead of the element itself */
  stagger?: boolean
  delay?: number
}

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

    gsap.registerPlugin(ScrollTrigger)

    const targets = stagger ? Array.from(el.children) : [el]

    const ctx = gsap.context(() => {
      gsap.set(targets, { opacity: 0, y: 28 })
      gsap.to(targets, {
        opacity: 1,
        y: 0,
        duration: 0.9,
        ease: 'power3.out',
        delay,
        stagger: stagger ? 0.09 : 0,
        scrollTrigger: {
          trigger: el,
          start: 'top 85%',
          once: true,
        },
      })
    }, el)

    return () => ctx.revert()
  }, [stagger, delay])

  return (
    // @ts-expect-error dynamic tag with ref
    <Tag ref={ref} className={cn(className)}>
      {children}
    </Tag>
  )
}
