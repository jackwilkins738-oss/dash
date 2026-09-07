'use client'

import { useEffect, useRef } from 'react'

type Node = { baseX: number; x: number; y: number; vx: number; vy: number }
type Pt = { x: number; y: number }
type Anchor = { x: number; y: number }

const SPACING = 34
const CABLE_WIDTH = 25
const CORE_WIDTH = 5
const MOUSE_RADIUS = 150
const LEG_HEIGHT = 640
const RENDER_BUFFER = 260
const GAP = 5

const BLUE = { core: '#4a9fd4', glow: '#3d8fd4', bright: '#dcefff', spark: '#7fc4ff' }
const BRASS = '#c9a15a'

export function PowerCable() {
  const wrapRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const wrap = wrapRef.current
    const canvas = canvasRef.current
    if (!wrap || !canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    let width = 0
    let height = 0
    let dpr = 1
    let nodes: Node[] = []
    let breaks: [number, number][] = []
    let raf = 0
    let t = 0
    let wirePulse = 0
    let visible = true
    const mouse = { x: -9999, y: -9999, active: false }
    const normals: Pt[] = []

    const measure = () => {
      const footer = document.querySelector('footer')
      const rect = wrap.getBoundingClientRect()
      width = rect.width
      const footerY = footer
        ? footer.getBoundingClientRect().top + window.scrollY
        : document.documentElement.scrollHeight
      height = Math.max(0, footerY - (rect.top + window.scrollY))
      dpr = Math.min(window.devicePixelRatio || 1, 2)

      canvas.width = width * dpr
      canvas.height = height * dpr
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      wrap.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

      const startX = 20
      const endX = Math.max(startX, width - 34)

      // Zig-zag anchors, left/right/left..., forced to land on the right
      // at the very bottom - a literal routed run, not a smooth spiral.
      let legCount = Math.max(2, Math.round(height / LEG_HEIGHT))
      if (legCount % 2 === 0) legCount += 1
      const anchors: Anchor[] = []
      for (let k = 0; k <= legCount; k++) {
        anchors.push({ x: k % 2 === 0 ? startX : endX, y: (k / legCount) * height })
      }

      const count = Math.ceil(height / SPACING) + 1
      const prevNodes = nodes
      nodes = []
      for (let i = 0; i < count; i++) {
        const y = Math.min(i * SPACING, height)
        let leg = Math.min(legCount - 1, Math.floor((y / height) * legCount) || 0)
        if (!isFinite(leg)) leg = 0
        const a = anchors[leg]
        const b = anchors[leg + 1]
        const span = b.y - a.y || 1
        const u = Math.max(0, Math.min(1, (y - a.y) / span))
        const eased = u * u * (3 - 2 * u)
        const wiggle = Math.sin(i * 0.7) * 4.5 + Math.cos(i * 0.33) * 2.2
        const baseX = a.x + (b.x - a.x) * eased + wiggle
        const prev = prevNodes[i]
        nodes.push({
          baseX,
          x: prev ? prev.x : baseX,
          y,
          vx: prev ? prev.vx : 0,
          vy: prev ? prev.vy : 0,
        })
      }

      breaks = [
        [Math.floor(count * 0.34), Math.floor(count * 0.34) + GAP],
        [Math.floor(count * 0.71), Math.floor(count * 0.71) + GAP],
      ]
    }

    const updateWirePulse = () => {
      const wireSection = document.querySelector('[data-wire-section]')
      if (!wireSection) {
        wirePulse *= 0.92
        return
      }
      const rect = wireSection.getBoundingClientRect()
      const vh = window.innerHeight
      const center = rect.top + rect.height / 2
      const dist = Math.abs(center - vh / 2)
      const proximity = Math.max(0, 1 - dist / (vh * 0.65))
      wirePulse += (proximity - wirePulse) * 0.06
    }

    const computeNormals = (lo: number, hi: number) => {
      for (let i = lo; i <= hi; i++) {
        const a = nodes[Math.max(0, i - 1)]
        const b = nodes[Math.min(nodes.length - 1, i + 1)]
        const dx = b.x - a.x
        const dy = b.y - a.y
        const len = Math.hypot(dx, dy) || 1
        normals[i] = { x: -dy / len, y: dx / len }
      }
    }

    const smoothPathFrom = (pts: Pt[]) => {
      ctx.beginPath()
      ctx.moveTo(pts[0].x, pts[0].y)
      for (let i = 1; i < pts.length - 1; i++) {
        const mx = (pts[i].x + pts[i + 1].x) / 2
        const my = (pts[i].y + pts[i + 1].y) / 2
        ctx.quadraticCurveTo(pts[i].x, pts[i].y, mx, my)
      }
      const last = pts[pts.length - 1]
      ctx.lineTo(last.x, last.y)
    }

    const runPoints = (lo: number, hi: number, offset = 0) => {
      const pts: Pt[] = []
      for (let i = lo; i <= hi; i++) {
        const n = nodes[i]
        if (offset === 0) pts.push({ x: n.x, y: n.y })
        else pts.push({ x: n.x + normals[i].x * offset, y: n.y + normals[i].y * offset })
      }
      return pts
    }

    // Organic diameter - a real extruded jacket is never perfectly
    // cylindrical along its length.
    const radiusScale = (i: number) => 1 + Math.sin(i * 0.13) * 0.05 + Math.sin(i * 0.037 + 1.2) * 0.035

    const runPointsScaled = (lo: number, hi: number, frac: number) => {
      const pts: Pt[] = []
      for (let i = lo; i <= hi; i++) {
        const n = nodes[i]
        const off = frac * CABLE_WIDTH * radiusScale(i)
        pts.push({ x: n.x + normals[i].x * off, y: n.y + normals[i].y * off })
      }
      return pts
    }

    // The cross-section shading, as a stack of offset strokes from one
    // jacket edge to the other - a cheap but convincing stand-in for a
    // true perpendicular gradient on a curved canvas stroke.
    const JACKET_BANDS: [frac: number, color: string, width: number][] = [
      [-0.52, 'rgba(0,0,0,0.6)', 3],
      [-0.4, '#040405', 5],
      [-0.28, '#15171b', 6],
      [-0.18, '#2b2e35', 6],
      [-0.09, '#454a54', 5],
      [0.02, '#57606d', 3.4],
      [0.1, '#3a3f48', 5],
      [0.24, '#1c1e23', 6],
      [0.38, '#0a0b0d', 5.5],
      [0.52, 'rgba(0,0,0,0.62)', 3],
    ]

    const drawJacketBands = (lo: number, hi: number) => {
      for (const [frac, color, w] of JACKET_BANDS) {
        smoothPathFrom(runPointsScaled(lo, hi, frac))
        ctx.strokeStyle = color
        ctx.lineWidth = w
        ctx.stroke()
      }
      // Soft wide sheen - the subsurface glow rubber gets under light
      smoothPathFrom(runPointsScaled(lo, hi, -0.12))
      ctx.strokeStyle = 'rgba(180,200,220,0.1)'
      ctx.lineWidth = 9
      ctx.filter = 'blur(2.5px)'
      ctx.stroke()
      ctx.filter = 'none'
      // Sharp glint on top
      smoothPathFrom(runPointsScaled(lo, hi, -0.1))
      ctx.strokeStyle = 'rgba(255,255,255,0.55)'
      ctx.lineWidth = 1.1
      ctx.stroke()
    }

    const drawGrain = (lo: number, hi: number) => {
      ctx.save()
      ctx.fillStyle = 'rgba(0,0,0,0.35)'
      for (let i = lo; i < hi; i++) {
        const hash = Math.sin(i * 12.9898) * 43758.5453
        const frac = (hash - Math.floor(hash)) * 2 - 1
        if (Math.abs(frac) > 0.72) continue
        const n = nodes[i]
        const nrm = normals[i]
        const off = frac * CABLE_WIDTH * 0.42
        ctx.beginPath()
        ctx.arc(n.x + nrm.x * off, n.y + nrm.y * off, 0.6, 0, Math.PI * 2)
        ctx.fill()
      }
      ctx.restore()
    }

    // Split [lo,hi] into runs that exclude any break gaps they overlap
    const runsInRange = (lo: number, hi: number): [number, number][] => {
      const out: [number, number][] = []
      let cursor = lo
      for (const [bs, be] of breaks) {
        if (be < lo || bs > hi) continue
        if (bs > cursor) out.push([cursor, Math.min(bs - 1, hi)])
        cursor = Math.max(cursor, be + 1)
      }
      if (cursor <= hi) out.push([cursor, hi])
      return out.filter(([a, b]) => b - a >= 1)
    }

    const drawTie = (i: number) => {
      const n = nodes[i]
      const a = nodes[Math.max(0, i - 1)]
      const b = nodes[Math.min(nodes.length - 1, i + 1)]
      const angle = Math.atan2(b.x - a.x, b.y - a.y)
      ctx.save()
      ctx.translate(n.x, n.y)
      ctx.rotate(angle)
      ctx.fillStyle = 'rgba(0,0,0,0.38)'
      ctx.fillRect(-CABLE_WIDTH * 0.72 + 1.5, -2.5, CABLE_WIDTH * 1.44, 6)
      const g = ctx.createLinearGradient(0, -4, 0, 4)
      g.addColorStop(0, '#525860')
      g.addColorStop(0.5, '#2c3038')
      g.addColorStop(1, '#121418')
      ctx.fillStyle = g
      ctx.fillRect(-CABLE_WIDTH * 0.74, -4, CABLE_WIDTH * 1.48, 8)
      ctx.fillStyle = '#0d0e11'
      ctx.beginPath()
      ctx.arc(-CABLE_WIDTH * 0.5, 0, 1.6, 0, Math.PI * 2)
      ctx.arc(CABLE_WIDTH * 0.5, 0, 1.6, 0, Math.PI * 2)
      ctx.fill()
      ctx.restore()
    }

    const drawFrayedEnd = (i: number, forward: 1 | -1) => {
      const n = nodes[i]
      const nb = nodes[i - forward] ?? n
      const angle = Math.atan2(n.x - nb.x, n.y - nb.y)
      ctx.save()
      ctx.translate(n.x, n.y)
      ctx.rotate(angle)
      for (let s = 0; s < 4; s++) {
        const spread = (s / 3 - 0.5) * 1.3
        const len = 10 + Math.sin(t * 3 + s) * 3
        ctx.beginPath()
        ctx.moveTo(0, 0)
        ctx.quadraticCurveTo(Math.sin(spread) * len * 0.6, len * 0.6, Math.sin(spread) * len, len)
        ctx.strokeStyle = s % 2 === 0 ? '#e0924a' : '#f0b46a'
        ctx.lineWidth = 1.3
        ctx.shadowColor = '#ffb066'
        ctx.shadowBlur = 5
        ctx.stroke()
      }
      ctx.shadowBlur = 0
      ctx.restore()
    }

    const drawSparkGap = (bs: number, be: number) => {
      const a = nodes[bs - 1]
      const b = nodes[be + 1]
      if (!a || !b) return
      drawFrayedEnd(bs - 1, 1)
      drawFrayedEnd(be + 1, -1)

      const cycle = (t * 1.1 + bs) % 3
      if (cycle > 2.55) {
        const flicker = (cycle - 2.55) / 0.45
        ctx.save()
        ctx.strokeStyle = `rgba(220,240,255,${0.5 + flicker * 0.4})`
        ctx.lineWidth = 1.6
        ctx.shadowColor = BLUE.spark
        ctx.shadowBlur = 14
        ctx.beginPath()
        ctx.moveTo(a.x, a.y)
        const midx = (a.x + b.x) / 2 + (Math.sin(t * 30) ) * 10
        const midy = (a.y + b.y) / 2 + (Math.cos(t * 26)) * 6
        ctx.lineTo(midx, midy)
        ctx.lineTo(b.x, b.y)
        ctx.stroke()
        ctx.shadowBlur = 0
        ctx.restore()
      }
    }

    const drawEndCap = (index: number, direction: 1 | -1) => {
      const n = nodes[index]
      const neighbour = nodes[index - direction] ?? n
      const angle = Math.atan2(n.x - neighbour.x, n.y - neighbour.y)
      ctx.save()
      ctx.translate(n.x, n.y)
      ctx.rotate(angle)

      const bootLen = 16
      const bootGrad = ctx.createLinearGradient(-CABLE_WIDTH / 2, 0, CABLE_WIDTH / 2, 0)
      bootGrad.addColorStop(0, '#050506')
      bootGrad.addColorStop(0.4, '#1d1f24')
      bootGrad.addColorStop(0.5, '#2a2d33')
      bootGrad.addColorStop(0.6, '#1d1f24')
      bootGrad.addColorStop(1, '#050506')
      ctx.fillStyle = bootGrad
      ctx.beginPath()
      ctx.moveTo(-CABLE_WIDTH / 2, 0)
      ctx.lineTo(CABLE_WIDTH / 2, 0)
      ctx.quadraticCurveTo(CABLE_WIDTH / 2, bootLen, 0, bootLen)
      ctx.quadraticCurveTo(-CABLE_WIDTH / 2, bootLen, -CABLE_WIDTH / 2, 0)
      ctx.fill()

      const ferrule = ctx.createLinearGradient(-CABLE_WIDTH / 2, 0, CABLE_WIDTH / 2, 0)
      ferrule.addColorStop(0, '#4c515a')
      ferrule.addColorStop(0.3, '#c7ccd3')
      ferrule.addColorStop(0.5, '#eef1f4')
      ferrule.addColorStop(0.7, '#9ba1aa')
      ferrule.addColorStop(1, '#33363c')
      ctx.fillStyle = ferrule
      ctx.fillRect(-CABLE_WIDTH * 0.52, -2, CABLE_WIDTH * 1.04, 5)

      ctx.fillStyle = BLUE.spark
      ctx.shadowColor = BLUE.glow
      ctx.shadowBlur = 6 + wirePulse * 14
      ctx.beginPath()
      ctx.arc(0, bootLen * 0.5, 2.4, 0, Math.PI * 2)
      ctx.fill()
      ctx.shadowBlur = 0
      ctx.restore()
    }

    // Draw one unbroken stretch of cable: shadow, jacket, texture, core.
    const drawRun = (lo: number, hi: number) => {
      if (hi - lo < 1) return
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'

      // Cast shadow - plain offset stroke, no blur (blur across a long
      // path is the single most expensive op canvas offers)
      ctx.save()
      ctx.translate(6, 8)
      smoothPathFrom(runPoints(lo, hi))
      ctx.strokeStyle = 'rgba(0,0,0,0.32)'
      ctx.lineWidth = CABLE_WIDTH
      ctx.stroke()
      ctx.restore()

      // Rubber jacket - layered cross-section bands instead of a flat fill
      drawJacketBands(lo, hi)
      drawGrain(lo, hi)

      // Molded ribbing - one path, one stroke call
      ctx.save()
      ctx.strokeStyle = 'rgba(0,0,0,0.22)'
      ctx.lineWidth = 1
      ctx.beginPath()
      for (let i = lo; i < hi; i += 2) {
        const n = nodes[i]
        const nrm = normals[i]
        const twist = Math.sin(i * 0.5 + t * 0.35) * 0.5 + 0.5
        const half = CABLE_WIDTH * 0.42 * (0.55 + twist * 0.45)
        ctx.moveTo(n.x - nrm.x * half, n.y - nrm.y * half)
        ctx.lineTo(n.x + nrm.x * half, n.y + nrm.y * half)
      }
      ctx.stroke()
      ctx.restore()

      // Helical brass tracer - front-facing arcs only
      ctx.save()
      ctx.strokeStyle = BRASS
      ctx.globalAlpha = 0.5
      ctx.lineWidth = 1.6
      let segStart = -1
      for (let i = lo; i <= hi; i++) {
        const front = Math.sin(i * 0.5 + t * 0.35) > 0
        if (front && segStart < 0) segStart = i
        if ((!front || i === hi) && segStart >= 0) {
          const end = front ? i : i - 1
          if (end > segStart) {
            ctx.beginPath()
            for (let j = segStart; j <= end; j++) {
              const twist = Math.sin(j * 0.5 + t * 0.35) * CABLE_WIDTH * 0.36
              const nrm = normals[j]
              const px = nodes[j].x + nrm.x * twist
              const py = nodes[j].y + nrm.y * twist
              if (j === segStart) ctx.moveTo(px, py)
              else ctx.lineTo(px, py)
            }
            ctx.stroke()
          }
          segStart = -1
        }
      }
      ctx.restore()

      for (let i = lo + 4; i < hi - 4; i += 9) drawTie(i)

      // Live core
      const pulseBoost = 1 + wirePulse * 1.6
      const glowBlur = prefersReduced ? 0 : 10 + wirePulse * 18

      smoothPathFrom(runPoints(lo, hi))
      ctx.strokeStyle = `rgba(74, 159, 212, ${0.14 + wirePulse * 0.12})`
      ctx.lineWidth = CORE_WIDTH + 10 * pulseBoost
      ctx.shadowColor = BLUE.glow
      ctx.shadowBlur = glowBlur
      ctx.stroke()
      ctx.shadowBlur = 0

      smoothPathFrom(runPoints(lo, hi))
      const a = nodes[lo]
      const b = nodes[hi]
      const coreGrad = ctx.createLinearGradient(0, a.y, 0, b.y)
      const phase = prefersReduced ? 0 : (t * (85 + wirePulse * 40)) % 60
      const runLen = b.y - a.y || 1
      for (let s = -60; s < runLen + 60; s += 60) {
        const p0 = Math.max(0, Math.min(1, (s + phase) / runLen))
        const p1 = Math.max(0, Math.min(1, (s + phase + 34) / runLen))
        if (p1 > p0) {
          const alpha = 0.15 + wirePulse * 0.1
          coreGrad.addColorStop(p0, `rgba(120,190,255,${alpha})`)
          coreGrad.addColorStop((p0 + p1) / 2, BLUE.bright)
          coreGrad.addColorStop(p1, `rgba(120,190,255,${alpha})`)
        }
      }
      ctx.strokeStyle = coreGrad
      ctx.lineWidth = CORE_WIDTH
      ctx.stroke()
    }

    const simulate = () => {
      if (prefersReduced || nodes.length < 2) return

      const top = nodes[0]
      top.x += (top.baseX - top.x) * 0.18
      top.vx *= 0.5

      for (let i = 1; i < nodes.length; i++) {
        const n = nodes[i]
        let force = 0
        if (mouse.active) {
          const dx = n.x - mouse.x
          const dy = n.y - mouse.y
          const dist = Math.hypot(dx, dy)
          if (dist < MOUSE_RADIUS && dist > 0.001) {
            const strength = (1 - dist / MOUSE_RADIUS) ** 1.4
            force = (dx / dist) * strength * 34
          }
        }
        const target = n.baseX + force
        n.vx += (target - n.x) * 0.07
        n.vx *= 0.86
        n.x += n.vx
      }
      const bottom = nodes[nodes.length - 1]
      bottom.x += (bottom.baseX - bottom.x) * 0.18
    }

    const draw = () => {
      if (!visible) {
        raf = requestAnimationFrame(draw)
        return
      }
      if (nodes.length < 2) {
        raf = requestAnimationFrame(draw)
        return
      }

      updateWirePulse()
      simulate()

      // Only touch the slice of the (possibly very tall) canvas that's
      // actually near the viewport - this is what keeps a page-spanning
      // canvas cheap regardless of document length.
      const viewTop = Math.max(0, window.scrollY - RENDER_BUFFER)
      const viewBottom = Math.min(height, window.scrollY + window.innerHeight + RENDER_BUFFER)
      let lo = Math.max(0, Math.floor(viewTop / SPACING) - 2)
      let hi = Math.min(nodes.length - 1, Math.ceil(viewBottom / SPACING) + 2)

      ctx.clearRect(0, Math.max(0, nodes[lo].y - 40), width, nodes[hi].y - nodes[lo].y + 80)
      computeNormals(lo, hi)

      for (const [lo2, hi2] of runsInRange(lo, hi)) drawRun(lo2, hi2)
      for (const [bs, be] of breaks) {
        if (be >= lo && bs <= hi) drawSparkGap(bs, be)
      }

      if (lo === 0) drawEndCap(0, 1)
      if (hi === nodes.length - 1) drawEndCap(nodes.length - 1, -1)

      if (!prefersReduced) t += 1 / 60
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
    }

    measure()
    computeNormals(0, nodes.length - 1)
    draw()
    if (prefersReduced) cancelAnimationFrame(raf)

    let resizeTimer = 0
    const onResize = () => {
      window.clearTimeout(resizeTimer)
      resizeTimer = window.setTimeout(measure, 120)
    }
    window.addEventListener('resize', onResize)
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerleave', onLeave)
    window.addEventListener('scroll', updateWirePulse, { passive: true })

    const ro = new ResizeObserver(onResize)
    ro.observe(document.body)

    const io = new IntersectionObserver(
      ([entry]) => {
        visible = entry.isIntersecting
      },
      { rootMargin: '200px 0px' },
    )
    io.observe(wrap)

    const settleTimers = [200, 800, 1800].map((ms) => window.setTimeout(measure, ms))

    return () => {
      cancelAnimationFrame(raf)
      window.clearTimeout(resizeTimer)
      settleTimers.forEach(window.clearTimeout)
      window.removeEventListener('resize', onResize)
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerleave', onLeave)
      window.removeEventListener('scroll', updateWirePulse)
      ro.disconnect()
      io.disconnect()
    }
  }, [])

  return (
    <div ref={wrapRef} className="pointer-events-none absolute inset-x-0 top-0 -z-10">
      <div className="mx-auto h-full max-w-6xl px-5 sm:px-8">
        <canvas ref={canvasRef} className="h-full w-full opacity-[0.97]" aria-hidden="true" />
      </div>
    </div>
  )
}
