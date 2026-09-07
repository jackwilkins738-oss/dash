'use client'

import { useEffect, useRef } from 'react'

type Node = { baseX: number; x: number; y: number; vx: number }

const SPACING = 36
const CABLE_WIDTH = 24
const CORE_WIDTH = 6
const MOUSE_RADIUS = 140

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
    const mouse = { x: -9999, y: -9999, active: false }

    const measure = () => {
      const footer = document.querySelector('footer')
      const rect = wrap.getBoundingClientRect()
      width = rect.width
      const footerY = footer
        ? footer.getBoundingClientRect().top + window.scrollY
        : document.documentElement.scrollHeight
      height = Math.max(0, footerY - (rect.top + window.scrollY))
      dpr = 1

      canvas.width = width * dpr
      canvas.height = height * dpr
      canvas.style.width = `${width}px`
      canvas.style.height = `${height}px`
      wrap.style.height = `${height}px`
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

      anchorX = 18
      const count = Math.ceil(height / SPACING) + 1
      const prevNodes = nodes
      nodes = []
      for (let i = 0; i < count; i++) {
        const y = i * SPACING
        const wave = Math.sin(y * 0.0032) * 10 + Math.sin(y * 0.011 + 1.7) * 4
        const baseX = anchorX + wave
        const prev = prevNodes[i]
        nodes.push({ baseX, x: prev ? prev.x : baseX, y: Math.min(y, height), vx: prev ? prev.vx : 0 })
      }
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

    const drawTie = (n: Node) => {
      ctx.save()
      ctx.translate(n.x, n.y)
      ctx.fillStyle = 'rgba(0,0,0,0.35)'
      ctx.fillRect(-CABLE_WIDTH * 0.72 + 1.5, -2.5, CABLE_WIDTH * 1.44, 6)
      const g = ctx.createLinearGradient(0, -4, 0, 4)
      g.addColorStop(0, '#4a5058')
      g.addColorStop(0.5, '#2a2e34')
      g.addColorStop(1, '#14161a')
      ctx.fillStyle = g
      ctx.fillRect(-CABLE_WIDTH * 0.74, -4, CABLE_WIDTH * 1.48, 8)
      ctx.fillStyle = 'rgba(255,255,255,0.14)'
      ctx.fillRect(-CABLE_WIDTH * 0.74, -4, CABLE_WIDTH * 1.48, 1.2)
      // two rivets
      ctx.fillStyle = '#0d0e11'
      ctx.beginPath()
      ctx.arc(-CABLE_WIDTH * 0.5, 0, 1.6, 0, Math.PI * 2)
      ctx.arc(CABLE_WIDTH * 0.5, 0, 1.6, 0, Math.PI * 2)
      ctx.fill()
      ctx.restore()
    }

    // Faint perpendicular ribbing, the molded texture on a real cable jacket
    const drawRibs = () => {
      ctx.save()
      ctx.strokeStyle = 'rgba(0,0,0,0.22)'
      ctx.lineWidth = 1
      for (let i = 0; i < nodes.length - 1; i++) {
        if (i % 2 !== 0) continue
        const a = nodes[i]
        const b = nodes[i + 1]
        const dx = b.x - a.x
        const dy = b.y - a.y
        const len = Math.hypot(dx, dy) || 1
        const nx = (-dy / len) * (CABLE_WIDTH * 0.42)
        const ny = (dx / len) * (CABLE_WIDTH * 0.42)
        ctx.beginPath()
        ctx.moveTo(a.x - nx, a.y - ny)
        ctx.lineTo(a.x + nx, a.y + ny)
        ctx.stroke()
      }
      ctx.restore()
    }

    const drawEndpoint = (n: Node, kind: 'plug' | 'socket') => {
      ctx.save()
      ctx.translate(n.x, n.y)
      const w = CABLE_WIDTH * 1.7
      const h = 22
      const yOff = kind === 'plug' ? 0 : -h

      ctx.shadowColor = 'rgba(0,0,0,0.6)'
      ctx.shadowBlur = 10
      ctx.shadowOffsetY = 4
      const body = ctx.createLinearGradient(-w / 2, 0, w / 2, 0)
      body.addColorStop(0, '#15171b')
      body.addColorStop(0.45, '#2e323a')
      body.addColorStop(0.55, '#363b44')
      body.addColorStop(1, '#15171b')
      ctx.fillStyle = body
      ctx.beginPath()
      ctx.roundRect(-w / 2, yOff, w, h, 5)
      ctx.fill()
      ctx.shadowBlur = 0
      ctx.shadowOffsetY = 0

      ctx.strokeStyle = 'rgba(255,255,255,0.18)'
      ctx.lineWidth = 1
      ctx.beginPath()
      ctx.roundRect(-w / 2 + 1, yOff + 1, w - 2, h - 2, 4)
      ctx.stroke()

      // screws top-left / top-right of the housing
      const screwY = kind === 'plug' ? h - 5 : -5
      for (const sx of [-w / 2 + 6, w / 2 - 6]) {
        const sg = ctx.createRadialGradient(sx - 0.6, screwY - 0.6, 0.2, sx, screwY, 2.4)
        sg.addColorStop(0, '#cfd4da')
        sg.addColorStop(1, '#565c65')
        ctx.fillStyle = sg
        ctx.beginPath()
        ctx.arc(sx, screwY, 2.2, 0, Math.PI * 2)
        ctx.fill()
        ctx.strokeStyle = '#1a1c20'
        ctx.lineWidth = 0.8
        ctx.beginPath()
        ctx.moveTo(sx - 1.5, screwY)
        ctx.lineTo(sx + 1.5, screwY)
        ctx.stroke()
      }

      // indicator LED
      const ledY = kind === 'plug' ? h / 2 : -h / 2
      ctx.fillStyle = '#7fc4ff'
      ctx.shadowColor = '#7fc4ff'
      ctx.shadowBlur = 12
      ctx.beginPath()
      ctx.arc(0, ledY, 3, 0, Math.PI * 2)
      ctx.fill()
      ctx.fillStyle = 'rgba(255,255,255,0.85)'
      ctx.shadowBlur = 0
      ctx.beginPath()
      ctx.arc(-0.8, ledY - 0.8, 1, 0, Math.PI * 2)
      ctx.fill()
      ctx.restore()
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height)
      if (nodes.length < 2) {
        raf = requestAnimationFrame(draw)
        return
      }

      if (!prefersReduced) {
        for (const n of nodes) {
          let force = 0
          if (mouse.active) {
            const dx = n.x - mouse.x
            const dy = n.y - mouse.y
            const dist = Math.hypot(dx, dy)
            if (dist < MOUSE_RADIUS && dist > 0.001) {
              force = (dx / dist) * (1 - dist / MOUSE_RADIUS) * 30
            }
          }
          const target = n.baseX + force
          n.vx += (target - n.x) * 0.08
          n.vx *= 0.82
          n.x += n.vx
        }
      }

      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'

      // Cast shadow onto the page - lit from the upper left, so the shadow
      // falls lower-right, exactly as a real cable resting against a wall would.
      ctx.save()
      smoothPath()
      ctx.strokeStyle = 'rgba(0,0,0,0.001)'
      ctx.lineWidth = CABLE_WIDTH
      ctx.shadowColor = 'rgba(0,0,0,0.55)'
      ctx.shadowBlur = 10
      ctx.shadowOffsetX = 5
      ctx.shadowOffsetY = 7
      ctx.stroke()
      ctx.shadowColor = 'transparent'
      ctx.shadowBlur = 0
      ctx.shadowOffsetX = 0
      ctx.shadowOffsetY = 0
      ctx.restore()

      // Rubber insulation body
      smoothPath()
      const grad = ctx.createLinearGradient(anchorX - CABLE_WIDTH * 0.7, 0, anchorX + CABLE_WIDTH * 0.7, 0)
      grad.addColorStop(0, '#050506')
      grad.addColorStop(0.28, '#1c1e23')
      grad.addColorStop(0.42, '#2b2e35')
      grad.addColorStop(0.5, '#34373f')
      grad.addColorStop(0.64, '#1f2127')
      grad.addColorStop(1, '#020203')
      ctx.strokeStyle = grad
      ctx.lineWidth = CABLE_WIDTH
      ctx.stroke()

      drawRibs()

      // Off-centre specular highlight - a true cylinder's brightest edge sits
      // toward the light source, not dead-centre, which is what sells the 3D
      // roundness rather than a flat painted stripe.
      ctx.save()
      ctx.translate(-CABLE_WIDTH * 0.16, 0)
      smoothPath()
      ctx.strokeStyle = 'rgba(255,255,255,0.16)'
      ctx.lineWidth = 4
      ctx.stroke()
      ctx.restore()
      ctx.save()
      ctx.translate(-CABLE_WIDTH * 0.16, 0)
      smoothPath()
      ctx.strokeStyle = 'rgba(255,255,255,0.34)'
      ctx.lineWidth = 1.4
      ctx.stroke()
      ctx.restore()

      // A darker contact-shadow edge on the far side balances the highlight
      ctx.save()
      ctx.translate(CABLE_WIDTH * 0.34, 0)
      smoothPath()
      ctx.strokeStyle = 'rgba(0,0,0,0.3)'
      ctx.lineWidth = 3
      ctx.stroke()
      ctx.restore()

      // Ties every ~7 nodes
      for (let i = 6; i < nodes.length - 6; i += 7) drawTie(nodes[i])

      // Glowing core - the live current, pulsing downward
      smoothPath()
      ctx.strokeStyle = 'rgba(74, 150, 224, 0.18)'
      ctx.lineWidth = CORE_WIDTH + 10
      ctx.shadowColor = '#4d96e0'
      ctx.shadowBlur = prefersReduced ? 0 : 18
      ctx.stroke()
      ctx.shadowBlur = 0

      smoothPath()
      const coreGrad = ctx.createLinearGradient(0, 0, 0, height)
      const phase = prefersReduced ? 0 : (t * 70) % 60
      for (let s = -60; s < height + 60; s += 60) {
        const p0 = Math.max(0, Math.min(1, (s + phase) / height))
        const p1 = Math.max(0, Math.min(1, (s + phase + 34) / height))
        if (p1 > p0) {
          coreGrad.addColorStop(p0, 'rgba(120,190,255,0.15)')
          coreGrad.addColorStop((p0 + p1) / 2, 'rgba(220,240,255,0.95)')
          coreGrad.addColorStop(p1, 'rgba(120,190,255,0.15)')
        }
      }
      ctx.strokeStyle = coreGrad
      ctx.lineWidth = CORE_WIDTH
      ctx.stroke()

      drawEndpoint(nodes[0], 'plug')
      drawEndpoint(nodes[nodes.length - 1], 'socket')

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

    const ro = new ResizeObserver(onResize)
    ro.observe(document.body)

    const settleTimers = [200, 800, 1800].map((ms) => window.setTimeout(measure, ms))

    return () => {
      cancelAnimationFrame(raf)
      window.clearTimeout(resizeTimer)
      settleTimers.forEach(window.clearTimeout)
      window.removeEventListener('resize', onResize)
      window.removeEventListener('pointermove', onMove)
      window.removeEventListener('pointerleave', onLeave)
      ro.disconnect()
    }
  }, [])

  return (
    <div ref={wrapRef} className="pointer-events-none absolute inset-x-0 top-0 -z-10">
      <div className="mx-auto h-full max-w-6xl px-5 sm:px-8">
        <canvas ref={canvasRef} className="h-full w-full opacity-95" aria-hidden="true" />
      </div>
    </div>
  )
}
