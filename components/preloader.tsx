'use client'

import { useEffect, useRef, useState } from 'react'
import { gsap } from 'gsap'

export function Preloader() {
  const root = useRef<HTMLDivElement>(null)
  const svgRef = useRef<SVGSVGElement>(null)
  const [count, setCount] = useState(0)
  const [done, setDone] = useState(false)

  useEffect(() => {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    document.body.style.overflow = 'hidden'

    const finish = () => {
      document.body.style.overflow = ''
      setDone(true)
    }

    if (prefersReduced) {
      setCount(100)
      const t = setTimeout(finish, 300)
      return () => clearTimeout(t)
    }

    const ctx = gsap.context(() => {
      // Prime every drawable stroke as "empty"
      const strokes = gsap.utils.toArray<SVGPathElement>('.bp-draw')
      strokes.forEach((el) => {
        el.style.strokeDasharray = '1'
        el.style.strokeDashoffset = '1'
      })
      gsap.set('.bp-node', { scale: 0, transformOrigin: 'center' })
      gsap.set('.bp-dim', { opacity: 0 })
      gsap.set('.bp-fill', { opacity: 0 })

      const state = { value: 0 }
      const tl = gsap.timeline()

      // Same choreography as before, rescaled to ~1.3s total (was ~4.1s) -
      // snappier reads as precise/high-tech rather than as the old
      // sequence just sped up crudely.
      tl.to(
        state,
        {
          value: 100,
          duration: 1.0,
          ease: 'power1.inOut',
          onUpdate: () => setCount(Math.round(state.value)),
        },
        0,
      )

      // 1. Draw the structure, ground up
      tl.to('.bp-ground', { strokeDashoffset: 0, duration: 0.16, ease: 'power2.inOut' }, 0.032)
        .to('.bp-wall', { strokeDashoffset: 0, duration: 0.224, ease: 'power2.inOut', stagger: 0.038 }, 0.112)
        .to('.bp-roof', { strokeDashoffset: 0, duration: 0.192, ease: 'power2.inOut' }, 0.304)
        .to('.bp-detail', { strokeDashoffset: 0, duration: 0.192, ease: 'power2.out', stagger: 0.026 }, 0.432)
        // 2. Snap corner nodes in
        .to('.bp-node', { scale: 1, duration: 0.128, ease: 'back.out(3)', stagger: 0.016 }, 0.48)
        // 3. Dimension lines measure the plan
        .to('.bp-dim', { opacity: 1, duration: 0.16, ease: 'power2.out', stagger: 0.032 }, 0.576)
        // 4. Materialize — blueprint becomes a solid build
        .to('.bp-fill', { opacity: 1, duration: 0.224, ease: 'power2.inOut', stagger: 0.019 }, 0.736)
        .to('.bp-draw', { stroke: 'var(--foreground)', duration: 0.192, ease: 'power2.inOut' }, 0.736)
        .fromTo(
          '.bp-flash',
          { opacity: 0 },
          { opacity: 0.6, duration: 0.064, yoyo: true, repeat: 1, ease: 'power2.in' },
          0.8,
        )
        // 5. Wordmark locks
        .from('.pl-word', { opacity: 0, y: 14, duration: 0.16, ease: 'power3.out' }, 0.832)
        // 6. Curtain lifts to reveal the site
        .to('.pl-panel', { yPercent: -100, duration: 0.288, ease: 'power4.inOut', stagger: 0.019, onComplete: finish }, 1.024)

      return () => tl.kill()
    }, root)

    return () => {
      ctx.revert()
      document.body.style.overflow = ''
    }
  }, [])

  if (done) return null

  return (
    <div ref={root} className="fixed inset-0 z-[100]" aria-hidden="true">
      {/* Split-panel curtain */}
      <div className="pl-panel absolute inset-0 blueprint-grid bg-background" />
      <div className="pl-panel absolute inset-0 bg-background/60" />

      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <svg
          ref={svgRef}
          viewBox="0 0 300 230"
          className="w-[280px] max-w-[76vw] sm:w-[360px]"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {/* Materialized solid fills (revealed at the end) */}
          <g className="bp-fill" fill="var(--blueprint)" opacity="0.14" stroke="none">
            <path d="M70 175 L70 92 L230 92 L230 175 Z" />
          </g>
          <g className="bp-fill" fill="var(--blueprint)" opacity="0.22" stroke="none">
            <path d="M58 92 L150 44 L242 92 Z" />
          </g>

          {/* Ground */}
          <path className="bp-draw bp-ground" d="M18 175 L282 175" stroke="var(--blueprint)" strokeWidth="1.5" />

          {/* Walls */}
          <path className="bp-draw bp-wall" d="M70 175 L70 92" stroke="var(--blueprint)" strokeWidth="1.5" />
          <path className="bp-draw bp-wall" d="M230 175 L230 92" stroke="var(--blueprint)" strokeWidth="1.5" />
          <path className="bp-draw bp-wall" d="M70 92 L230 92" stroke="var(--blueprint)" strokeWidth="1.5" />

          {/* Roof */}
          <path className="bp-draw bp-roof" d="M58 92 L150 44 L242 92" stroke="var(--blueprint)" strokeWidth="1.5" />

          {/* Details: door + windows */}
          <path className="bp-draw bp-detail" d="M135 175 L135 132 L165 132 L165 175" stroke="var(--blueprint)" strokeWidth="1.2" />
          <path className="bp-draw bp-detail" d="M90 112 L116 112 L116 138 L90 138 Z" stroke="var(--blueprint)" strokeWidth="1.2" />
          <path className="bp-draw bp-detail" d="M184 112 L210 112 L210 138 L184 138 Z" stroke="var(--blueprint)" strokeWidth="1.2" />

          {/* Corner nodes */}
          {[
            [70, 92],
            [230, 92],
            [70, 175],
            [230, 175],
            [150, 44],
          ].map(([cx, cy]) => (
            <circle key={`${cx}-${cy}`} className="bp-node" cx={cx} cy={cy} r="3" fill="var(--blueprint)" />
          ))}

          {/* Dimension lines */}
          <g className="bp-dim" stroke="var(--muted-foreground)" strokeWidth="0.75">
            <path d="M70 196 L230 196" />
            <path d="M70 191 L70 201" />
            <path d="M230 191 L230 201" />
          </g>
          <g className="bp-dim" stroke="var(--muted-foreground)" strokeWidth="0.75">
            <path d="M48 92 L48 175" />
            <path d="M43 92 L53 92" />
            <path d="M43 175 L53 175" />
          </g>
          <text className="bp-dim" x="150" y="212" textAnchor="middle" fill="var(--muted-foreground)" fontSize="9" fontFamily="var(--font-mono)">
            SCOPE
          </text>

          {/* Materialize flash */}
          <rect className="bp-flash" x="0" y="0" width="300" height="230" fill="var(--blueprint)" opacity="0" />
        </svg>

        <div className="pl-word mt-6 flex items-center gap-3">
          <span className="font-mono text-2xl font-bold tracking-[0.25em] text-foreground sm:text-3xl">
            S<span className="text-blueprint">·</span>D
          </span>
          <span className="h-4 w-px bg-line" />
          <span className="font-mono text-[11px] uppercase tracking-[0.3em] text-muted-foreground">
            Scalar Digital
          </span>
        </div>

        <div className="mt-6 flex w-60 max-w-[76vw] items-center justify-between font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground">
          <span>Constructing</span>
          <span className="text-blueprint">{String(count).padStart(3, '0')}</span>
        </div>
        <div className="mt-3 h-px w-60 max-w-[76vw] overflow-hidden bg-line">
          <div className="h-full bg-blueprint transition-[width] duration-100" style={{ width: `${count}%` }} />
        </div>
      </div>
    </div>
  )
}
