'use client'

import { useEffect, useRef } from 'react'

type Node = { baseX: number; x: number; y: number; vx: number; vy: number }

const SPACING = 34
const CABLE_WIDTH = 26
const CORE_WIDTH = 5
const MOUSE_RADIUS = 160

// Site blueprint palette — oklch(0.62 0.135 244) family
const BLUE = { core: '#4a9fd4', glow: '#3d8fd4', bright: '#c8e8ff', spark: '#7fc4ff' }

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
    let anchorX = 0
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

      anchorX = 20
      const count = Math.ceil(height / SPACING) + 1
      const prevNodes = nodes
      nodes = []
      for (let i = 0; i < count; i++) {
        const y = i * SPACING
        const wave = Math.sin(y * 0.003) * 11 + Math.sin(y * 0.0095 + 1.4) * 5
        const baseX = anchorX + wave
        const prev = prevNodes[i]
        nodes.push({
          baseX,
          x: prev ? prev.x : baseX,
          y: Math.min(y, height),
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

    const smoothPath = () => {
      ctx.beginPath()
      ctx.moveTo(nodes[0].x, nodes[0].y)
      for (let i = 1; i < nodes.length - 1; i++) {
        const mx = (nodes[i].x + nodes[i + 1].x) / 2
        const my = (nodes[i].y + nodes[i + 1].y) / 2
        ctx.quadraticCurveTo(nodes[i].x, nodes[i].y, mx, my)
      }
      const last = nodes[nodes.length - 1]
      ctx.lineTo(last.x, last.y)
    }

    const drawTie = (n: Node, i: number) => {
      ctx.save()
      ctx.translate(n.x, n.y)
      const angle = i > 0 && i < nodes.length - 1
        ? Math.atan2(nodes[i + 1].x - nodes[i - 1].x, nodes[i + 1].y - nodes[i - 1].y)
        : 0
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

    const drawHelicalRibs = () => {
      ctx.save()
      for (let i = 0; i < nodes.length - 1; i++) {
        const a = nodes[i]
        const b = nodes[i + 1]
        const dx = b.x - a.x
        const dy = b.y - a.y
        const len = Math.hypot(dx, dy) || 1
        const twist = Math.sin(i * 0.55 + t * 0.4) * 0.35 + 0.65
        const nx = (-dy / len) * (CABLE_WIDTH * 0.44 * twist)
        const ny = (dx / len) * (CABLE_WIDTH * 0.44 * twist)
        ctx.strokeStyle = i % 2 === 0 ? 'rgba(0,0,0,0.28)' : 'rgba(255,255,255,0.04)'
        ctx.lineWidth = i % 2 === 0 ? 1.1 : 0.7
        ctx.beginPath()
        ctx.moveTo(a.x - nx, a.y - ny)
        ctx.lineTo(a.x + nx, a.y + ny)
        ctx.stroke()
      }
      ctx.restore()
    }

    const drawUKPlug = (n: Node) => {
      ctx.save()
      ctx.translate(n.x, n.y)

      // Pins protruding upward into off-screen socket
      const pinGrad = ctx.createLinearGradient(-8, -28, 8, -28)
      pinGrad.addColorStop(0, '#8a7a50')
      pinGrad.addColorStop(0.5, '#d4c48a')
      pinGrad.addColorStop(1, '#6a5a38')
      ctx.fillStyle = pinGrad
      for (const [px, ph] of [[-9, 22], [9, 22], [0, 28]] as const) {
        ctx.beginPath()
        ctx.roundRect(px - 2.2, -ph - 4, 4.4, ph, 1.2)
        ctx.fill()
      }

      // Plug body — BS 1363 proportions
      const bw = 38
      const bh = 50
      ctx.shadowColor = 'rgba(0,0,0,0.55)'
      ctx.shadowBlur = 12
      ctx.shadowOffsetY = 5
      const body = ctx.createLinearGradient(-bw / 2, 0, bw / 2, 0)
      body.addColorStop(0, '#c8ccd2')
      body.addColorStop(0.35, '#eef0f3')
      body.addColorStop(0.55, '#f5f6f8')
      body.addColorStop(1, '#b8bcc4')
      ctx.fillStyle = body
      ctx.beginPath()
      ctx.roundRect(-bw / 2, -2, bw, bh, 6)
      ctx.fill()
      ctx.shadowBlur = 0
      ctx.shadowOffsetY = 0

      // Fuse window emboss
      ctx.fillStyle = 'rgba(0,0,0,0.08)'
      ctx.beginPath()
      ctx.roundRect(-10, 14, 20, 14, 2)
      ctx.fill()
      ctx.strokeStyle = 'rgba(0,0,0,0.15)'
      ctx.lineWidth = 0.8
      ctx.stroke()
      ctx.fillStyle = '#c0392b'
      ctx.beginPath()
      ctx.roundRect(-6, 18, 12, 6, 1)
      ctx.fill()

      // Cable strain relief boot
      const boot = ctx.createLinearGradient(0, bh - 2, 0, bh + 14)
      boot.addColorStop(0, '#1a1c20')
      boot.addColorStop(1, '#0a0b0d')
      ctx.fillStyle = boot
      ctx.beginPath()
      ctx.roundRect(-CABLE_WIDTH * 0.55, bh - 2, CABLE_WIDTH * 1.1, 16, 3)
      ctx.fill()

      // Live indicator on plug face
      const ledGlow = 10 + wirePulse * 14
      ctx.fillStyle = BLUE.spark
      ctx.shadowColor = BLUE.glow
      ctx.shadowBlur = ledGlow
      ctx.beginPath()
      ctx.arc(0, 8, 2.8, 0, Math.PI * 2)
      ctx.fill()
      ctx.shadowBlur = 0

      // Occasional micro-spark at pin base
      if (!prefersReduced && Math.sin(t * 4.2) > 0.92) {
        ctx.strokeStyle = `rgba(200,232,255,${0.35 + wirePulse * 0.4})`
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(-9, -4)
        ctx.lineTo(-9 + Math.sin(t * 12) * 3, -8)
        ctx.stroke()
      }

      ctx.restore()
    }

    const drawUKSocket = (n: Node) => {
      ctx.save()
      ctx.translate(n.x, n.y)

      const pw = 52
      const ph = 58

      ctx.shadowColor = 'rgba(0,0,0,0.5)'
      ctx.shadowBlur = 10
      ctx.shadowOffsetY = 3
      const plate = ctx.createLinearGradient(-pw / 2, 0, pw / 2, 0)
      plate.addColorStop(0, '#181a1e')
      plate.addColorStop(0.5, '#2a2e34')
      plate.addColorStop(1, '#181a1e')
      ctx.fillStyle = plate
      ctx.beginPath()
      ctx.roundRect(-pw / 2, -ph, pw, ph, 4)
      ctx.fill()
      ctx.shadowBlur = 0

      // Twin socket apertures
      for (const sy of [-ph + 14, -ph + 36]) {
        ctx.fillStyle = '#08090b'
        ctx.beginPath()
        ctx.roundRect(-14, sy - 7, 28, 14, 2)
        ctx.fill()
        ctx.strokeStyle = 'rgba(255,255,255,0.08)'
        ctx.lineWidth = 0.8
        ctx.stroke()
        // L/N/E pin holes
        ctx.fillStyle = '#030304'
        for (const hx of [-6, 6]) ctx.fillRect(hx - 1.5, sy - 4, 3, 8)
        ctx.fillRect(-1.5, sy - 6, 3, 5)
      }

      // Faceplate screws
      for (const sy of [-ph + 6, -6]) {
        const sg = ctx.createRadialGradient(0, sy - 0.5, 0.2, 0, sy, 2.5)
        sg.addColorStop(0, '#cfd4da')
        sg.addColorStop(1, '#565c65')
        ctx.fillStyle = sg
        ctx.beginPath()
        ctx.arc(0, sy, 2.3, 0, Math.PI * 2)
        ctx.fill()
      }

      // Live LED between sockets
      const intensity = 0.55 + wirePulse * 0.45
      ctx.fillStyle = BLUE.spark
      ctx.shadowColor = BLUE.glow
      ctx.shadowBlur = 8 + wirePulse * 16
      ctx.globalAlpha = intensity
      ctx.beginPath()
      ctx.arc(0, -ph / 2, 2.5, 0, Math.PI * 2)
      ctx.fill()
      ctx.globalAlpha = 1
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
            force = (dx / dist) * strength * 38
            n.vy += (dy / dist) * strength * 6
          }
        }
        const target = n.baseX + force
        n.vx += (target - n.x) * 0.07
        n.vx *= 0.84
        n.vy *= 0.88
        n.x += n.vx
        n.y += n.vy
        n.vy += 0.015
      }

      // Rope constraints — keeps the cable taut and draped realistically
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

      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'

      // Cast shadow
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

      // Rubber jacket
      smoothPath()
      const grad = ctx.createLinearGradient(anchorX - CABLE_WIDTH * 0.75, 0, anchorX + CABLE_WIDTH * 0.75, 0)
      grad.addColorStop(0, '#030304')
      grad.addColorStop(0.22, '#181a1f')
      grad.addColorStop(0.4, '#2e3139')
      grad.addColorStop(0.5, '#383c45')
      grad.addColorStop(0.62, '#22252b')
      grad.addColorStop(1, '#020203')
      ctx.strokeStyle = grad
      ctx.lineWidth = CABLE_WIDTH
      ctx.stroke()

      drawHelicalRibs()

      // Specular highlight — off-centre for cylindrical read
      ctx.save()
      ctx.translate(-CABLE_WIDTH * 0.18, 0)
      smoothPath()
      ctx.strokeStyle = 'rgba(255,255,255,0.14)'
      ctx.lineWidth = 4.5
      ctx.stroke()
      ctx.strokeStyle = 'rgba(255,255,255,0.32)'
      ctx.lineWidth = 1.2
      ctx.stroke()
      ctx.restore()

      ctx.save()
      ctx.translate(CABLE_WIDTH * 0.36, 0)
      smoothPath()
      ctx.strokeStyle = 'rgba(0,0,0,0.32)'
      ctx.lineWidth = 3.5
      ctx.stroke()
      ctx.restore()

      for (let i = 6; i < nodes.length - 8; i += 7) drawTie(nodes[i], i)

      // Live core glow — intensifies near the "Cut the wire" section
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

      drawUKPlug(nodes[0])
      drawUKSocket(nodes[nodes.length - 1])

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
