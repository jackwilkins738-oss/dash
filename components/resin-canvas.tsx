'use client'

import { useEffect, useRef } from 'react'

type Stone = {
  ox: number
  oy: number
  x: number
  y: number
  vx: number
  vy: number
  r: number
  base: string
  hi: string
}

// Aggregate tones — slate/graphite stones with a couple of lighter chips,
// tuned to sit inside the dark + cyan palette rather than fight it.
const TONES: [string, string][] = [
  ['#39434a', '#59666e'],
  ['#2d363c', '#4a555c'],
  ['#454f56', '#69757d'],
  ['#323b41', '#525d64'],
  ['#5a666d', '#828f97'],
]

export function ResinCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    let width = 0
    let height = 0
    let dpr = Math.min(window.devicePixelRatio || 1, 2)
    let stones: Stone[] = []
    const mouse = { x: -9999, y: -9999, active: false }
    let raf = 0
    let running = true

    const build = () => {
      const parent = canvas.parentElement
      if (!parent) return
      width = parent.clientWidth
      height = parent.clientHeight
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = width * dpr
      canvas.height = height * dpr
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

      // Density scales with area; lighter on small screens.
      const spacing = width < 640 ? 20 : 16
      stones = []
      for (let gx = 0; gx <= width + spacing; gx += spacing) {
        for (let gy = 0; gy <= height + spacing; gy += spacing) {
          const jx = (Math.random() - 0.5) * spacing * 0.9
          const jy = (Math.random() - 0.5) * spacing * 0.9
          const ox = gx + jx
          const oy = gy + jy
          const [base, hi] = TONES[(Math.random() * TONES.length) | 0]
          stones.push({
            ox,
            oy,
            x: ox,
            y: oy,
            vx: 0,
            vy: 0,
            r: spacing * (0.28 + Math.random() * 0.22),
            base,
            hi,
          })
        }
      }
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height)
      const radius = 120

      for (const s of stones) {
        if (mouse.active) {
          const dx = s.x - mouse.x
          const dy = s.y - mouse.y
          const dist = Math.hypot(dx, dy)
          if (dist < radius && dist > 0.001) {
            const force = (1 - dist / radius) * 4.2
            s.vx += (dx / dist) * force
            s.vy += (dy / dist) * force
          }
        }
        // settle back to laid position, like resin smoothing flat
        s.vx += (s.ox - s.x) * 0.05
        s.vy += (s.oy - s.y) * 0.05
        s.vx *= 0.84
        s.vy *= 0.84
        s.x += s.vx
        s.y += s.vy

        // stone body
        ctx.beginPath()
        ctx.fillStyle = s.base
        ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2)
        ctx.fill()
        // top-left highlight for a rounded, wet-look chip
        ctx.beginPath()
        ctx.fillStyle = s.hi
        ctx.arc(s.x - s.r * 0.28, s.y - s.r * 0.3, s.r * 0.5, 0, Math.PI * 2)
        ctx.fill()
      }

      // wet-resin specular glow that follows the trowel
      if (mouse.active) {
        const g = ctx.createRadialGradient(mouse.x, mouse.y, 0, mouse.x, mouse.y, radius * 1.3)
        g.addColorStop(0, 'rgba(150, 220, 235, 0.16)')
        g.addColorStop(0.5, 'rgba(150, 220, 235, 0.05)')
        g.addColorStop(1, 'rgba(150, 220, 235, 0)')
        ctx.globalCompositeOperation = 'lighter'
        ctx.fillStyle = g
        ctx.beginPath()
        ctx.arc(mouse.x, mouse.y, radius * 1.3, 0, Math.PI * 2)
        ctx.fill()
        ctx.globalCompositeOperation = 'source-over'
      }

      raf = requestAnimationFrame(draw)
    }

    const onMove = (e: PointerEvent) => {
      const rect = canvas.getBoundingClientRect()
      mouse.x = e.clientX - rect.left
      mouse.y = e.clientY - rect.top
      mouse.active = true
    }
    const onLeave = () => {
      mouse.active = false
      mouse.x = -9999
      mouse.y = -9999
    }

    build()
    if (prefersReduced) {
      draw()
      cancelAnimationFrame(raf)
      running = false
    } else {
      draw()
      window.addEventListener('pointermove', onMove)
      window.addEventListener('pointerleave', onLeave)
    }

    const onResize = () => {
      build()
      if (!running) {
        cancelAnimationFrame(raf)
        draw()
        cancelAnimationFrame(raf)
      }
    }
    window.addEventListener('resize', onResize)

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerleave', onLeave)
      window.removeEventListener('resize', onResize)
    }
  }, [])

  return <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" aria-hidden="true" />
}
