'use client'

import { useEffect, useRef } from 'react'

type Node = {
  ox: number
  oy: number
  x: number
  y: number
  vx: number
  vy: number
}

export function BlueprintCanvas() {
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
    let nodes: Node[] = []
    const spacing = 46
    const mouse = { x: -9999, y: -9999 }
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

      nodes = []
      const cols = Math.ceil(width / spacing) + 1
      const rows = Math.ceil(height / spacing) + 1
      for (let i = 0; i < cols; i++) {
        for (let j = 0; j < rows; j++) {
          const ox = i * spacing
          const oy = j * spacing
          nodes.push({ ox, oy, x: ox, y: oy, vx: 0, vy: 0 })
        }
      }
    }

    const draw = () => {
      ctx.clearRect(0, 0, width, height)
      const radius = 150

      for (const n of nodes) {
        const dx = n.x - mouse.x
        const dy = n.y - mouse.y
        const dist = Math.hypot(dx, dy)

        if (dist < radius && dist > 0) {
          const force = (1 - dist / radius) * 14
          n.vx += (dx / dist) * force
          n.vy += (dy / dist) * force
        }

        // spring back to origin
        n.vx += (n.ox - n.x) * 0.06
        n.vy += (n.oy - n.y) * 0.06
        n.vx *= 0.86
        n.vy *= 0.86
        n.x += n.vx
        n.y += n.vy
      }

      // grid lines
      const cols = Math.ceil(width / spacing) + 1
      const rows = Math.ceil(height / spacing) + 1
      ctx.lineWidth = 1
      ctx.strokeStyle = 'rgba(120, 200, 220, 0.10)'
      ctx.beginPath()
      for (let i = 0; i < cols; i++) {
        for (let j = 0; j < rows; j++) {
          const idx = i * rows + j
          const n = nodes[idx]
          if (!n) continue
          const right = nodes[(i + 1) * rows + j]
          const down = nodes[i * rows + (j + 1)]
          if (right && i < cols - 1) {
            ctx.moveTo(n.x, n.y)
            ctx.lineTo(right.x, right.y)
          }
          if (down && j < rows - 1) {
            ctx.moveTo(n.x, n.y)
            ctx.lineTo(down.x, down.y)
          }
        }
      }
      ctx.stroke()

      // nodes glow near cursor
      for (const n of nodes) {
        const dist = Math.hypot(n.x - mouse.x, n.y - mouse.y)
        const t = Math.max(0, 1 - dist / radius)
        const size = 0.8 + t * 2.2
        ctx.beginPath()
        ctx.fillStyle = `rgba(150, 220, 235, ${0.15 + t * 0.6})`
        ctx.arc(n.x, n.y, size, 0, Math.PI * 2)
        ctx.fill()
      }

      raf = requestAnimationFrame(draw)
    }

    const onMove = (e: PointerEvent) => {
      const rect = canvas.getBoundingClientRect()
      mouse.x = e.clientX - rect.left
      mouse.y = e.clientY - rect.top
    }
    const onLeave = () => {
      mouse.x = -9999
      mouse.y = -9999
    }

    build()
    if (prefersReduced) {
      // static single-frame render
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
