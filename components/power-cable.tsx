'use client'

import { useEffect, useRef } from 'react'

type Node = { baseX: number; x: number; y: number; vx: number; vy: number }
type Pt = { x: number; y: number }

const SPACING = 30
const CABLE_WIDTH = 25
const CORE_WIDTH = 5
const MOUSE_RADIUS = 150
const ROTATIONS = 2.4

// Site blueprint palette — oklch(0.62 0.135 244) family
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
    let raf = 0
    let t = 0
    let wirePulse = 0
    let visible = true
    const mouse = { x: -9999, y: -9999, active: false }

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
      const margin = 30
      const maxRadius = Math.max(0, Math.min(startX, width - endX, width * 0.34) - margin * 0.4)

      const count = Math.ceil(height / SPACING) + 1
      const prevNodes = nodes
      nodes = []
      for (let i = 0; i < count; i++) {
        const y = Math.min(i * SPACING, height)
        const p = height > 0 ? y / height : 0
        // Corkscrew that starts pinned at the logo, bulges outward through
        // the middle of the page, and unwinds back to zero radius exactly
        // at the bottom-right landing point - so both ends stay put while
        // the middle spirals.
        const centerX = startX + p * (endX - startX)
        const radius = maxRadius * Math.sin(Math.PI * p)
        const angle = p * ROTATIONS * Math.PI * 2
        const baseX = centerX + Math.cos(angle) * radius
        const prev = prevNodes[i]
        nodes.push({
          baseX,
          x: prev ? prev.x : baseX,
          y,
          vx: prev ? prev.vx : 0,
          vy: prev ? prev.vy : 0,
        })
      }
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

    // Per-node outward normal, averaged from the two adjacent segments so
    // it stays continuous through the spiral's curves instead of only
    // being correct on straight runs.
    const normals: Pt[] = []
    const computeNormals = () => {
      normals.length = 0
      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[Math.max(0, i - 1)]
        const b = nodes[Math.min(nodes.length - 1, i + 1)]
        const dx = b.x - a.x
        const dy = b.y - a.y
        const len = Math.hypot(dx, dy) || 1
        normals.push({ x: -dy / len, y: dx / len })
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

    const smoothPath = () => smoothPathFrom(nodes)

    const offsetPath = (amount: number | ((i: number) => number)) =>
      nodes.map((n, i) => {
        const a = typeof amount === 'function' ? amount(i) : amount
        const nrm = normals[i]
        return { x: n.x + nrm.x * a, y: n.y + nrm.y * a }
      })

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
      ctx.fillStyle = 'rgba(255,255,255,0.12)'
      ctx.fillRect(-CABLE_WIDTH * 0.74, -4, CABLE_WIDTH * 1.48, 1.2)
      ctx.fillStyle = '#0d0e11'
      ctx.beginPath()
      ctx.arc(-CABLE_WIDTH * 0.5, 0, 1.6, 0, Math.PI * 2)
      ctx.arc(CABLE_WIDTH * 0.5, 0, 1.6, 0, Math.PI * 2)
      ctx.fill()
      ctx.restore()
    }

    // Fine molded ribbing, perpendicular ticks that fade in and out to
    // suggest the jacket twisting as it follows the spiral.
    const drawJacketTexture = () => {
      for (let i = 0; i < nodes.length - 1; i += 2) {
        const n = nodes[i]
        const nrm = normals[i]
        const twist = Math.sin(i * 0.5 + t * 0.35) * 0.5 + 0.5
        const half = CABLE_WIDTH * 0.42 * (0.55 + twist * 0.45)
        ctx.strokeStyle = `rgba(0,0,0,${0.16 + twist * 0.12})`
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(n.x - nrm.x * half, n.y - nrm.y * half)
        ctx.lineTo(n.x + nrm.x * half, n.y + nrm.y * half)
        ctx.stroke()
      }
    }

    // A thin brass tracer stripe wound helically along the jacket - the
    // identification line real armoured/multicore cable carries.
    const drawTracerStripe = () => {
      const pts = nodes.map((n, i) => {
        const twist = Math.sin(i * 0.5 + t * 0.35)
        const off = twist * CABLE_WIDTH * 0.36
        const nrm = normals[i]
        return { x: n.x + nrm.x * off, y: n.y + nrm.y * off, front: twist > 0 }
      })
      ctx.save()
      ctx.lineWidth = 1.6
      ctx.strokeStyle = BRASS
      ctx.globalAlpha = 0.55
      let segStart = 0
      for (let i = 1; i <= pts.length; i++) {
        const brokeRun = i === pts.length || pts[i].front !== pts[segStart].front
        if (brokeRun) {
          if (pts[segStart].front) {
            ctx.beginPath()
            ctx.moveTo(pts[segStart].x, pts[segStart].y)
            for (let j = segStart + 1; j < i; j++) ctx.lineTo(pts[j].x, pts[j].y)
            ctx.stroke()
          }
          segStart = i
        }
      }
      ctx.restore()
    }

    const drawEndCap = (index: number, direction: 1 | -1) => {
      const n = nodes[index]
      const neighbour = nodes[index - direction] ?? n
      const angle = Math.atan2(n.x - neighbour.x, n.y - neighbour.y)
      ctx.save()
      ctx.translate(n.x, n.y)
      ctx.rotate(angle)

      // Rounded rubber boot capping the cut end
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

      // Chrome ferrule ring
      const ferrule = ctx.createLinearGradient(-CABLE_WIDTH / 2, 0, CABLE_WIDTH / 2, 0)
      ferrule.addColorStop(0, '#4c515a')
      ferrule.addColorStop(0.3, '#c7ccd3')
      ferrule.addColorStop(0.5, '#eef1f4')
      ferrule.addColorStop(0.7, '#9ba1aa')
      ferrule.addColorStop(1, '#33363c')
      ctx.fillStyle = ferrule
      ctx.fillRect(-CABLE_WIDTH * 0.52, -2, CABLE_WIDTH * 1.04, 5)

      // Live glow bleeding from the seam between ferrule and boot
      const glow = 6 + wirePulse * 14
      ctx.fillStyle = BLUE.spark
      ctx.shadowColor = BLUE.glow
      ctx.shadowBlur = glow
      ctx.beginPath()
      ctx.arc(0, bootLen * 0.5, 2.4, 0, Math.PI * 2)
      ctx.fill()
      ctx.shadowBlur = 0

      ctx.restore()
    }

    const simulate = () => {
      if (prefersReduced || nodes.length < 2) return

      const top = nodes[0]
      top.x += (top.baseX - top.x) * 0.18
      top.vx *= 0.5
      top.vy *= 0.5

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
            n.vy += (dy / dist) * strength * 5
          }
        }
        const target = n.baseX + force
        n.vx += (target - n.x) * 0.07
        n.vx *= 0.84
        n.vy *= 0.88
        n.x += n.vx
        n.y += n.vy
        n.vy += 0.01
      }

      for (let pass = 0; pass < 4; pass++) {
        for (let i = 0; i < nodes.length - 1; i++) {
          const a = nodes[i]
          const b = nodes[i + 1]
          const dx = b.x - a.x
          const dy = b.y - a.y
          const dist = Math.hypot(dx, dy) || 1
          const diff = (SPACING - dist) / dist
          const ox = dx * diff * 0.5
          const oy = dy * diff * 0.5
          if (i > 0) {
            a.x -= ox
            a.y -= oy
          }
          b.x += ox
          b.y += oy
        }
      }
      // Keep the landing point pinned to the spiral's bottom-right target
      const bottom = nodes[nodes.length - 1]
      bottom.x += (bottom.baseX - bottom.x) * 0.18
    }

    const draw = () => {
      if (!visible) {
        raf = requestAnimationFrame(draw)
        return
      }

      ctx.clearRect(0, 0, width, height)
      if (nodes.length < 2) {
        raf = requestAnimationFrame(draw)
        return
      }

      updateWirePulse()
      simulate()
      computeNormals()

      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'

      // Cast shadow - constant light direction regardless of the curve
      ctx.save()
      smoothPath()
      ctx.strokeStyle = 'rgba(0,0,0,0.001)'
      ctx.lineWidth = CABLE_WIDTH
      ctx.shadowColor = 'rgba(0,0,0,0.55)'
      ctx.shadowBlur = 12
      ctx.shadowOffsetX = 6
      ctx.shadowOffsetY = 8
      ctx.stroke()
      ctx.shadowColor = 'transparent'
      ctx.shadowBlur = 0
      ctx.shadowOffsetX = 0
      ctx.shadowOffsetY = 0
      ctx.restore()

      // Base rubber jacket - flat mid-tone, shading comes from the
      // curve-following highlight/shadow strokes drawn next
      smoothPath()
      ctx.strokeStyle = '#1b1d22'
      ctx.lineWidth = CABLE_WIDTH
      ctx.stroke()

      drawJacketTexture()
      drawTracerStripe()

      // Specular highlight - offset along the true per-node normal so it
      // reads correctly through every turn of the spiral, not just on
      // vertical runs
      smoothPathFrom(offsetPath(-CABLE_WIDTH * 0.2))
      ctx.strokeStyle = 'rgba(255,255,255,0.1)'
      ctx.lineWidth = 5
      ctx.stroke()
      smoothPathFrom(offsetPath(-CABLE_WIDTH * 0.24))
      ctx.strokeStyle = 'rgba(255,255,255,0.3)'
      ctx.lineWidth = 1.6
      ctx.stroke()

      // Core shadow on the far side, same treatment
      smoothPathFrom(offsetPath(CABLE_WIDTH * 0.3))
      ctx.strokeStyle = 'rgba(0,0,0,0.34)'
      ctx.lineWidth = 4
      ctx.stroke()

      // Outer jacket edge darkening
      smoothPathFrom(offsetPath(CABLE_WIDTH * 0.49))
      ctx.strokeStyle = 'rgba(0,0,0,0.5)'
      ctx.lineWidth = 2
      ctx.stroke()
      smoothPathFrom(offsetPath(-CABLE_WIDTH * 0.49))
      ctx.strokeStyle = 'rgba(0,0,0,0.5)'
      ctx.lineWidth = 2
      ctx.stroke()

      for (let i = 8; i < nodes.length - 10; i += 9) drawTie(i)

      // Live core glow - intensifies near the "cut the wire" section
      const pulseBoost = 1 + wirePulse * 1.6
      const glowBlur = prefersReduced ? 0 : 14 + wirePulse * 22

      smoothPath()
      ctx.strokeStyle = `rgba(74, 159, 212, ${0.14 + wirePulse * 0.12})`
      ctx.lineWidth = CORE_WIDTH + 12 * pulseBoost
      ctx.shadowColor = BLUE.glow
      ctx.shadowBlur = glowBlur
      ctx.stroke()
      ctx.shadowBlur = 0

      smoothPath()
      const coreGrad = ctx.createLinearGradient(0, 0, 0, height)
      const phase = prefersReduced ? 0 : (t * (85 + wirePulse * 40)) % 60
      for (let s = -60; s < height + 60; s += 60) {
        const p0 = Math.max(0, Math.min(1, (s + phase) / height))
        const p1 = Math.max(0, Math.min(1, (s + phase + 34) / height))
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

      drawEndCap(0, 1)
      drawEndCap(nodes.length - 1, -1)

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
      { rootMargin: '120px 0px' },
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
