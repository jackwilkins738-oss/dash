import type { ElementType, ReactNode } from 'react'

type RevealProps = {
  children: ReactNode
  className?: string
  as?: ElementType
  /** Stagger children direct descendants instead of the element itself */
  stagger?: boolean
  delay?: number
  /** Opt the element in to the cursor-lit glow (see interaction-layer.tsx) */
  spotlight?: boolean
}

// A fade-and-rise-into-view, declared here and performed elsewhere.
//
// This used to be a client component: each of the ~55 instances on the site
// was its own hydration boundary with its own effect and its own
// IntersectionObserver, all to run one small animation. It is now plain
// markup - it only records what it wants (data-reveal, plus a stagger flag and
// a delay) - and a single RevealController (components/reveal-controller.tsx)
// finds every one of them and animates them with one shared observer. Same
// animation, same timings, none of the per-instance React cost, and the class
// merge library that used to come along with it no longer ships to the browser.
export function Reveal({
  children,
  className,
  as: Tag = 'div',
  stagger = false,
  delay = 0,
  spotlight = false,
}: RevealProps) {
  return (
    <Tag
      className={className}
      data-reveal={stagger ? 'stagger' : ''}
      data-reveal-delay={delay ? delay : undefined}
      data-spotlight={spotlight ? '' : undefined}
    >
      {children}
    </Tag>
  )
}
