'use client'

import { useEffect, useRef } from 'react'

type Point = { x: number; y: number; px: number; py: number; pin?: boolean }
type Spark = { x: number; y: number; vx: number; vy: number; life: number; maxLife: number; size: number }

const SEGMENTS = 22
const ITERATIONS = 6

function makeChain(anchorY: number, reach: number, count: number): Point[] {
  const pts: Point[] = []
  for (let i = 0; i < count; i++) {
    const t = i / (count - 1)
    const y = anchorY + (reach - anchorY) * t
    pts.push({ x: 0, y, px: 0, py: y, pin: i === 0 })
  }
  return pts
}

export function ElectricCable() {
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
    let restA = 0
    let restB = 0
    let cx = 0
    let raf = 0
    let t = 0

    // Chain A hangs from the top of the viewport, chain B rises from the
    // bottom - the break sits in the gap between their free ends.
    let chainA: Point[] = []
    let chainB: Point[] = []
    let sparks: Spark[] = []
    let nextSparkAt = 0

    const build = () => {
      width = window.innerWidth
      height = window.innerHeight
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = width * dpr
      canvas.height = height * dpr
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

      cx = width * 0.5
      const breakCenter = height * 0.46
      restA = (breakCenter - height * 0.07 - 0) / (SEGMENTS - 1)
      restB = (height - (breakCenter + height * 0.07)) / (SEGMENTS - 1)

      chainA = makeChain(0, breakCenter - height * 0.07, SEGMENTS).map((p, i) => ({
        ...p,
        x: cx,
        px: cx,
      }))
      chainB = makeChain(height, breakCenter + height * 0.07, SEGMENTS).map((p, i) => ({
        ...p,
        x: cx,
        px: cx,
      }))
      chainB[0].pin = true
    }

    const wind = (idx: number, count: number, seed: number) => {
      const sway = idx / (count - 1)
      const a =
        Math.sin(t * 0.55 + idx * 0.6 + seed) * 14 +
        Math.sin(t * 0.21 + idx * 1.4 + seed * 1.7) * 9 +
        Math.sin(t * 1.05 + idx * 0.33 + seed * 2.3) * 4
      return a * Math.pow(sway, 1.6)
    }

    const relax = (pts: Point[], rest: number, anchorX: number) => {
      for (let i = 0; i < pts.length; i++) {
        const p = pts[i]
        if (p.pin) continue
        const vx = (p.x - p.px) * 0.985
        const vy = (p.y - p.py) * 0.985
        p.px = p.x
        p.py = p.y
        p.x += vx
        p.y += vy
      }
      for (let iter = 0; iter < ITERATIONS; iter++) {
        for (let i = 1; i < pts.length; i++) {
          const a = pts[i - 1]
          const b = pts[i]
          const dx = b.x - a.x
          const dy = b.y - a.y
          const dist = Math.hypot(dx, dy) || 0.0001
          const diff = (dist - rest) / dist
          const ox = dx * 0.5 * diff
          const oy = dy * 0.5 * diff
          if (!a.pin) {
            a.x += ox
            a.y += oy
          }
          if (!b.pin) {
            b.x -= ox
            b.y -= oy
          }
        }
        pts[0].x = anchorX
      }
    }

    const smoothPath = (pts: Point[]) => {
      ctx.moveTo(pts[0].x, pts[0].y)
      for (let i = 1; i < pts.length - 1; i++) {
        const mx = (pts[i].x + pts[i + 1].x) / 2
        const my = (pts[i].y + pts[i + 1].y) / 2
        ctx.quadraticCurveTo(pts[i].x, pts[i].y, mx, my)
      }
      const last = pts[pts.length - 1]
      ctx.lineTo(last.x, last.y)
    }

    const drawCable = (pts: Point[]) => {
      ctx.beginPath()
      smoothPath(pts)
      ctx.strokeStyle = 'rgba(0,0,0,0.45)'
      ctx.lineWidth = 20
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'
      ctx.stroke()

      ctx.beginPath()
      smoothPath(pts)
      const grad = ctx.createLinearGradient(0, 0, width, 0)
      grad.addColorStop(0, '#0c0d10')
      grad.addColorStop(0.5, '#1c1e23')
      grad.addColorStop(1, '#0c0d10')
      ctx.strokeStyle = grad
      ctx.lineWidth = 16
      ctx.stroke()

      ctx.beginPath()
      smoothPath(pts)
      ctx.strokeStyle = 'rgba(255,255,255,0.10)'
      ctx.lineWidth = 4
      ctx.stroke()
    }

    const drawFray = (tip: Point, dirSign: number) => {
      const strands = 5
      for (let i = 0; i < strands; i++) {
        const angle = (i / (strands - 1) - 0.5) * 1.6 + Math.PI / 2 + (dirSign > 0 ? 0 : Math.PI)
        const jitter = Math.sin(t * 3 + i * 5) * 0.15
        const len = 14 + Math.sin(t * 4 + i) * 4
        const ex = tip.x + Math.cos(angle + jitter) * len
        const ey = tip.y + Math.sin(angle + jitter) * len * dirSign
        ctx.beginPath()
        ctx.moveTo(tip.x, tip.y)
        ctx.quadraticCurveTo(tip.x + (ex - tip.x) * 0.4, tip.y + (ey - tip.y) * 0.4, ex, ey)
        ctx.strokeStyle = i % 2 === 0 ? '#e0924a' : '#f0b46a'
        ctx.lineWidth = 1.4
        ctx.shadowColor = '#ffb066'
        ctx.shadowBlur = 6
        ctx.stroke()
      }
      ctx.shadowBlur = 0
    }

    const spawnSparks = (x: number, y: number) => {
      const count = 6 + Math.floor(Math.random() * 6)
      for (let i = 0; i < count; i++) {
        const angle = Math.random() * Math.PI * 2
        const speed = 1.2 + Math.random() * 3.2
        sparks.push({
          x,
          y,
          vx: Math.cos(angle) * speed,
          vy: Math.sin(angle) * speed,
          life: 0,
          maxLife: 18 + Math.random() * 16,
          size: 1 + Math.random() * 1.8,
        })
      }
    }

    const drawArc = (a: Point, b: Point) => {
      ctx.beginPath()
      ctx.moveTo(a.x, a.y)
      const midx = (a.x + b.x) / 2 + (Math.random() - 0.5) * 30
      const midy = (a.y + b.y) / 2 + (Math.random() - 0.5) * 18
      ctx.lineTo(midx, midy)
      ctx.lineTo(b.x, b.y)
      ctx.strokeStyle = '#eaf4ff'
      ctx.lineWidth = 1.6
      ctx.shadowColor = '#8ecbff'
      ctx.shadowBlur = 16
      ctx.stroke()
      ctx.shadowBlur = 0
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height)

      relax(chainA, restA, cx)
      relax(chainB, restB, cx)

      for (let i = 0; i < chainA.length; i++) {
        if (!chainA[i].pin) chainA[i].x += wind(i, chainA.length, 1.1) * 0.02
      }
      for (let i = 0; i < chainB.length; i++) {
        if (!chainB[i].pin) chainB[i].x += wind(i, chainB.length, 4.4) * 0.02
      }

      drawCable(chainA)
      drawCable(chainB)

      const tipA = chainA[chainA.length - 1]
      const tipB = chainB[chainB.length - 1]
      drawFray(tipA, 1)
      drawFray(tipB, -1)

      const gapDist = Math.hypot(tipA.x - tipB.x, tipA.y - tipB.y)

      if (t > nextSparkAt) {
        nextSparkAt = t + 0.03 + Math.random() * 1.6
        spawnSparks((tipA.x + tipB.x) / 2, (tipA.y + tipB.y) / 2)
        if (gapDist < 90) drawArc(tipA, tipB)
      }

      sparks = sparks.filter((s) => s.life < s.maxLife)
      for (const s of sparks) {
        s.life += 1
        s.x += s.vx
        s.y += s.vy
        s.vy += 0.05
        s.vx *= 0.97
        const alpha = 1 - s.life / s.maxLife
        ctx.beginPath()
        ctx.arc(s.x, s.y, s.size, 0, Math.PI * 2)
        ctx.fillStyle = `rgba(255, 220, 170, ${alpha})`
        ctx.shadowColor = '#ffb066'
        ctx.shadowBlur = 8
        ctx.fill()
      }
      ctx.shadowBlur = 0

      t += 1 / 60
      raf = requestAnimationFrame(draw)
    }

    build()
    if (prefersReduced) {
      draw()
      cancelAnimationFrame(raf)
    } else {
      draw()
      window.addEventListener('resize', build)
    }

    return () => {
      cancelAnimationFrame(raf)
      window.removeEventListener('resize', build)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      className="pointer-events-none fixed inset-0 -z-10 h-svh w-full opacity-90"
      aria-hidden="true"
    />
  )
}
