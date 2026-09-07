'use client'

import { useEffect, useRef } from 'react'
import * as THREE from 'three'

type Node = { baseX: number; x: number; y: number; vx: number }
type Anchor = { x: number; y: number }

const SPACING = 30
const RADIUS = 12
const LEG_HEIGHT = 640
const RENDER_BUFFER = 340
const GAP = 5
const MOUSE_RADIUS = 150

// Deterministic PRNG so the randomised path is stable across re-measures
// instead of reshuffling every resize.
function mulberry32(seed: number) {
  let a = seed
  return () => {
    a |= 0
    a = (a + 0x6d2b79f5) | 0
    let x = Math.imul(a ^ (a >>> 15), 1 | a)
    x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296
  }
}

export function PowerCable() {
  const mountRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return

    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    let vw = window.innerWidth
    let vh = window.innerHeight
    let docHeight = 0
    let startX = 20
    let endX = vw - 34
    let anchors: Anchor[] = []
    let legCount = 2
    let nodes: Node[] = []
    let breaks: [number, number][] = []
    let slashes: number[] = []
    let t = 0
    let wirePulse = 0
    let raf = 0
    let visible = true
    const mouse = { x: -9999, y: -9999, active: false }

    // ---- renderer / scene ---------------------------------------------
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'low-power' })
    renderer.setClearColor(0x000000, 0)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2))
    renderer.toneMapping = THREE.ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.2
    mount.appendChild(renderer.domElement)

    const scene = new THREE.Scene()
    const camera = new THREE.OrthographicCamera(-vw / 2, vw / 2, vh / 2, -vh / 2, -1000, 1000)
    camera.position.z = 500

    const toScene = (px: number, pyViewport: number, z = 0) =>
      new THREE.Vector3(px - vw / 2, -(pyViewport - vh / 2), z)

    const key = new THREE.DirectionalLight(0xe4edff, 4.2)
    key.position.set(-120, 170, 260)
    scene.add(key)
    const fill = new THREE.HemisphereLight(0x6c86a8, 0x030405, 0.55)
    scene.add(fill)
    const rim = new THREE.DirectionalLight(0x5fa8e8, 1.4)
    rim.position.set(160, -100, 140)
    scene.add(rim)

    const travelLight = new THREE.PointLight(0x7fc4ff, 0, 260, 2)
    scene.add(travelLight)
    const travelLight2 = new THREE.PointLight(0x7fc4ff, 0, 200, 2)
    scene.add(travelLight2)

    // Procedural fine-grain bump texture for the jacket surface
    const noiseCanvas = document.createElement('canvas')
    noiseCanvas.width = 96
    noiseCanvas.height = 96
    const nctx = noiseCanvas.getContext('2d')!
    const img = nctx.createImageData(96, 96)
    for (let i = 0; i < img.data.length; i += 4) {
      const v = 128 + (Math.random() - 0.5) * 60
      img.data[i] = v
      img.data[i + 1] = v
      img.data[i + 2] = v
      img.data[i + 3] = 255
    }
    nctx.putImageData(img, 0, 0)
    const grainTex = new THREE.CanvasTexture(noiseCanvas)
    grainTex.wrapS = THREE.RepeatWrapping
    grainTex.wrapT = THREE.RepeatWrapping

    const jacketMat = new THREE.MeshPhysicalMaterial({
      color: 0x1a1c22,
      roughness: 0.4,
      metalness: 0.02,
      clearcoat: 0.65,
      clearcoatRoughness: 0.15,
      bumpMap: grainTex,
      bumpScale: 0.5,
    })
    const tracerMat = new THREE.MeshStandardMaterial({ color: 0xc9a15a, roughness: 0.4, metalness: 0.3 })
    const tieMat = new THREE.MeshStandardMaterial({ color: 0x2c3038, roughness: 0.45, metalness: 0.5 })
    const copperMat = new THREE.MeshStandardMaterial({
      color: 0xd98a3d,
      roughness: 0.35,
      metalness: 0.6,
      emissive: 0x3a1f0a,
      emissiveIntensity: 0.4,
    })

    const runGroup = new THREE.Group()
    scene.add(runGroup)
    const clearRunGroup = () => {
      for (const child of runGroup.children.slice()) {
        runGroup.remove(child)
        const mesh = child as THREE.Mesh
        mesh.geometry?.dispose()
      }
    }

    // ---- path -----------------------------------------------------------
    const measure = () => {
      vw = window.innerWidth
      vh = window.innerHeight
      const navEl = document.querySelector('header nav') as HTMLElement | null
      const navRect = navEl ? navEl.getBoundingClientRect() : { left: 20, right: vw - 20 }
      startX = navRect.left + 20
      endX = Math.max(startX + 200, navRect.right - 34)

      const footer = document.querySelector('footer')
      docHeight = footer
        ? footer.getBoundingClientRect().top + window.scrollY
        : document.documentElement.scrollHeight

      // Randomised zig-zag - variable leg length and edge jitter so no two
      // bends read as the same shape, instead of a metronomic left-right.
      const rand = mulberry32(0xc0ffee)
      anchors = [{ x: startX, y: 0 }]
      let side: 1 | -1 = 1
      let y = 0
      const span = endX - startX
      while (y < docHeight - LEG_HEIGHT * 0.4) {
        y += LEG_HEIGHT * (0.62 + rand() * 0.85)
        const edge = side === 1 ? endX : startX
        const jitter = (rand() - 0.5) * span * 0.3
        anchors.push({ x: Math.max(startX, Math.min(endX, edge - side * Math.abs(jitter))), y: Math.min(y, docHeight) })
        side = side === 1 ? -1 : 1
      }
      anchors.push({ x: endX, y: docHeight })
      legCount = anchors.length - 1

      let legPtr = 0
      const count = Math.ceil(docHeight / SPACING) + 1
      const prevNodes = nodes
      nodes = []
      for (let i = 0; i < count; i++) {
        const ny = Math.min(i * SPACING, docHeight)
        while (legPtr < legCount - 1 && ny > anchors[legPtr + 1].y) legPtr++
        const a = anchors[legPtr]
        const b = anchors[legPtr + 1]
        const legSpan = b.y - a.y || 1
        const u = Math.max(0, Math.min(1, (ny - a.y) / legSpan))
        // ease-in-out with a touch of overshoot variance per leg, via its
        // own seeded wobble, so turns don't all carve the identical curve
        const overshoot = Math.sin(legPtr * 12.9 + 3.7) * 0.12
        const eased = u * u * (3 - 2 * u) + Math.sin(u * Math.PI) * overshoot
        const wiggle = Math.sin(i * 0.7) * 4.5 + Math.cos(i * 0.33) * 2.2
        const baseX = a.x + (b.x - a.x) * eased + wiggle
        const prev = prevNodes[i]
        nodes.push({ baseX, x: prev ? prev.x : baseX, y: ny, vx: prev ? prev.vx : 0 })
      }

      breaks = [
        [Math.floor(count * 0.34), Math.floor(count * 0.34) + GAP],
        [Math.floor(count * 0.71), Math.floor(count * 0.71) + GAP],
      ]
      const slashFracs = [0.12, 0.24, 0.45, 0.58, 0.79, 0.9]
      slashes = slashFracs
        .map((f) => Math.floor(count * f))
        .filter((idx) => breaks.every(([bs, be]) => idx < bs - 8 || idx > be + 8))

      camera.left = -vw / 2
      camera.right = vw / 2
      camera.top = vh / 2
      camera.bottom = -vh / 2
      camera.updateProjectionMatrix()
      renderer.setSize(vw, vh)
    }

    const updateWirePulse = () => {
      const wireSection = document.querySelector('[data-wire-section]')
      if (!wireSection) {
        wirePulse *= 0.92
        return
      }
      const rect = wireSection.getBoundingClientRect()
      const center = rect.top + rect.height / 2
      const dist = Math.abs(center - vh / 2)
      const proximity = Math.max(0, 1 - dist / (vh * 0.65))
      wirePulse += (proximity - wirePulse) * 0.06
    }

    const simulate = () => {
      if (prefersReduced || nodes.length < 2) return
      const scrollY = window.scrollY
      const lo = Math.max(0, Math.floor((scrollY - RENDER_BUFFER) / SPACING) - 2)
      const hi = Math.min(nodes.length - 1, Math.ceil((scrollY + vh + RENDER_BUFFER) / SPACING) + 2)

      nodes[0].x += (nodes[0].baseX - nodes[0].x) * 0.18
      for (let i = Math.max(1, lo); i <= hi; i++) {
        const n = nodes[i]
        let force = 0
        if (mouse.active) {
          const dx = n.x - mouse.x
          const dy = n.y - window.scrollY - mouse.y
          const dist = Math.hypot(dx, dy)
          if (dist < MOUSE_RADIUS && dist > 0.001) {
            const strength = (1 - dist / MOUSE_RADIUS) ** 1.4
            force = (dx / dist) * strength * 30
          }
        }
        const target = n.baseX + force
        n.vx += (target - n.x) * 0.08
        n.vx *= 0.85
        n.x += n.vx
      }
      const last = nodes[nodes.length - 1]
      last.x += (last.baseX - last.x) * 0.18
    }

    const runsInRange = (lo: number, hi: number): [number, number][] => {
      const out: [number, number][] = []
      let cursor = lo
      for (const [bs, be] of breaks) {
        if (be < lo || bs > hi) continue
        if (bs > cursor) out.push([cursor, Math.min(bs - 1, hi)])
        cursor = Math.max(cursor, be + 1)
      }
      if (cursor <= hi) out.push([cursor, hi])
      return out.filter(([a, b]) => b - a >= 3)
    }

    const buildTubeForRun = (lo: number, hi: number, scrollY: number) => {
      const pts: THREE.Vector3[] = []
      for (let i = lo; i <= hi; i++) {
        const n = nodes[i]
        const z = Math.sin(i * 0.22) * 5
        pts.push(toScene(n.x, n.y - scrollY, z))
      }
      const curve = new THREE.CatmullRomCurve3(pts, false, 'catmullrom', 0.15)
      const segments = Math.max(4, (hi - lo) * 2)
      const geo = new THREE.TubeGeometry(curve, segments, RADIUS, 10, false)
      const mesh = new THREE.Mesh(geo, jacketMat)
      runGroup.add(mesh)

      // Helical brass tracer as a thin secondary tube offset from centre
      const tracerPts = pts.map((p, idx) => {
        const i = lo + idx
        const twist = Math.sin(i * 0.5 + t * 0.35)
        const off = twist * RADIUS * 0.7
        // offset roughly perpendicular in screen-space (x/y plane)
        const nrmAngle = Math.atan2(
          (nodes[Math.min(nodes.length - 1, i + 1)].x - nodes[Math.max(0, i - 1)].x),
          SPACING * 2,
        )
        return p.clone().add(new THREE.Vector3(Math.cos(nrmAngle) * off, Math.sin(nrmAngle) * off, RADIUS * 0.6))
      })
      const tracerCurve = new THREE.CatmullRomCurve3(tracerPts, false, 'catmullrom', 0.15)
      const tracerGeo = new THREE.TubeGeometry(tracerCurve, segments, 1.5, 6, false)
      runGroup.add(new THREE.Mesh(tracerGeo, tracerMat))

      // Cable ties - small rings around the tube
      for (let i = lo + 4; i < hi - 4; i += 9) {
        const idx = i - lo
        if (idx < 0 || idx >= pts.length) continue
        const p = pts[idx]
        const tangent = curve.getTangentAt(Math.min(0.999, Math.max(0.001, idx / (pts.length - 1))))
        const ring = new THREE.Mesh(new THREE.TorusGeometry(RADIUS * 1.15, 1.6, 8, 20), tieMat)
        ring.position.copy(p)
        const quat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 0, 1), tangent)
        ring.setRotationFromQuaternion(quat)
        runGroup.add(ring)
      }

      // Emissive core glow inside the jacket
      const glowMat = new THREE.MeshBasicMaterial({
        color: 0x7fc4ff,
        transparent: true,
        opacity: 0.22 + wirePulse * 0.16,
      })
      const glowGeo = new THREE.TubeGeometry(curve, segments, RADIUS * 0.45, 8, false)
      runGroup.add(new THREE.Mesh(glowGeo, glowMat))
    }

    const buildFrayed = (i: number, forward: 1 | -1, scrollY: number) => {
      const n = nodes[i]
      if (!n) return
      const base = toScene(n.x, n.y - scrollY, 0)
      for (let s = 0; s < 5; s++) {
        const spread = (s / 4 - 0.5) * 1.4
        const len = 14 + Math.sin(t * 3 + s) * 4
        const dir = new THREE.Vector3(Math.sin(spread), -forward * Math.cos(spread) * 0.4, Math.cos(spread) * 0.6)
          .normalize()
          .multiplyScalar(len)
        const cyl = new THREE.Mesh(new THREE.CylinderGeometry(0.6, 0.15, len, 5), copperMat)
        cyl.position.copy(base).add(dir.clone().multiplyScalar(0.5))
        cyl.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize())
        runGroup.add(cyl)
      }
    }

    // A knife-slash gouge in the jacket - doesn't sever the run, just
    // exposes the conductor and arcs on its own irregular cycle.
    const buildSlash = (i: number, scrollY: number) => {
      const n = nodes[i]
      const a = nodes[Math.max(0, i - 2)]
      const b = nodes[Math.min(nodes.length - 1, i + 2)]
      if (!n || !a || !b) return
      const pa = toScene(a.x, a.y - scrollY, 0)
      const pb = toScene(b.x, b.y - scrollY, 0)
      const base = toScene(n.x, n.y - scrollY, 0)
      const tangent = pb.clone().sub(pa).normalize()
      const front = base.clone().add(new THREE.Vector3(0, 0, RADIUS * 0.92))

      // Diagonal cut across the jacket surface
      const gash = new THREE.Mesh(new THREE.BoxGeometry(RADIUS * 1.5, 3.5, 2), tieMat)
      gash.position.copy(front)
      const gashQuat = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(1, 0, 0), tangent)
      gash.quaternion.copy(gashQuat)
      gash.rotateZ(Math.PI / 2.6)
      runGroup.add(gash)

      // A sliver of exposed copper conductor in the wound
      const copper = new THREE.Mesh(new THREE.CylinderGeometry(1.4, 1.4, RADIUS * 1.1, 8), copperMat)
      copper.position.copy(front).add(new THREE.Vector3(0, 0, 0.6))
      copper.quaternion.copy(gashQuat)
      copper.rotateZ(Math.PI / 2.6)
      runGroup.add(copper)

      // Irregular arcing - phase seeded per slash so they never fire in sync
      const phase = (t * (1.4 + (i % 5) * 0.23) + i * 3.1) % 4
      if (phase > 3.35) {
        const flicker = (phase - 3.35) / 0.65
        for (let s = 0; s < 3; s++) {
          const ang = (i * 1.7 + s * 2.4 + t * 6) % (Math.PI * 2)
          const tilt = Math.sin(i + s) * 0.6
          const len = 16 + flicker * 14
          const dir = new THREE.Vector3(Math.cos(ang), Math.sin(ang) * 0.5 + tilt, 0.6 + Math.sin(ang * 2))
            .normalize()
            .multiplyScalar(len)
          const bolt = front.clone().add(dir)
          const kink = new THREE.Vector3(Math.sin(t * 40 + s), Math.cos(t * 33 + s), 0)
          const boltGeo = new THREE.BufferGeometry().setFromPoints([
            front,
            front.clone().lerp(bolt, 0.5).add(kink),
            bolt,
          ])
          const boltMat = new THREE.LineBasicMaterial({
            color: 0xcfe9ff,
            transparent: true,
            opacity: 0.35 + flicker * 0.65,
          })
          runGroup.add(new THREE.Line(boltGeo, boltMat))
        }
        const flash = new THREE.PointLight(0x8fd0ff, flicker * 3.2, 160, 2)
        flash.position.copy(front)
        runGroup.add(flash)
      }
    }

    const buildSparkGap = (bs: number, be: number, scrollY: number) => {
      const a = nodes[bs - 1]
      const b = nodes[be + 1]
      if (!a || !b) return
      buildFrayed(bs - 1, 1, scrollY)
      buildFrayed(be + 1, -1, scrollY)

      const cycle = (t * 1.1 + bs) % 3
      if (cycle > 2.5) {
        const flicker = (cycle - 2.5) / 0.5
        const p0 = toScene(a.x, a.y - scrollY, 4)
        const mid = toScene(
          (a.x + b.x) / 2 + Math.sin(t * 30) * 10,
          (a.y + b.y) / 2 - scrollY + Math.cos(t * 26) * 4,
          10,
        )
        const p1 = toScene(b.x, b.y - scrollY, 4)
        const sparkGeo = new THREE.BufferGeometry().setFromPoints([p0, mid, p1])
        const sparkMat = new THREE.LineBasicMaterial({
          color: 0xeaf4ff,
          transparent: true,
          opacity: 0.5 + flicker * 0.5,
        })
        runGroup.add(new THREE.Line(sparkGeo, sparkMat))

        const flashLight = new THREE.PointLight(0x9fd6ff, flicker * 2.2, 140, 2)
        flashLight.position.copy(mid)
        runGroup.add(flashLight)
      }
    }

    const draw = () => {
      if (!visible) {
        raf = requestAnimationFrame(draw)
        return
      }
      updateWirePulse()
      simulate()
      clearRunGroup()

      const scrollY = window.scrollY
      const lo = Math.max(0, Math.floor((scrollY - RENDER_BUFFER) / SPACING) - 2)
      const hi = Math.min(nodes.length - 1, Math.ceil((scrollY + vh + RENDER_BUFFER) / SPACING) + 2)

      for (const [lo2, hi2] of runsInRange(lo, hi)) buildTubeForRun(lo2, hi2, scrollY)
      for (const [bs, be] of breaks) {
        if (be >= lo && bs <= hi) buildSparkGap(bs, be, scrollY)
      }
      for (const si of slashes) {
        if (si >= lo && si <= hi) buildSlash(si, scrollY)
      }

      // Travelling current - a real moving light, not a painted gradient
      const speed = 1 + wirePulse * 1.2
      const totalLen = Math.max(1, docHeight)
      const phase1 = (t * 620 * speed) % totalLen
      const phase2 = (phase1 + totalLen * 0.5) % totalLen
      const xAtY = (docY: number) => {
        let leg = 0
        while (leg < legCount - 1 && docY > anchors[leg + 1].y) leg++
        const a = anchors[leg]
        const b = anchors[leg + 1]
        const span = b.y - a.y || 1
        const u = Math.max(0, Math.min(1, (docY - a.y) / span))
        const eased = u * u * (3 - 2 * u)
        return a.x + (b.x - a.x) * eased
      }
      const lightAt = (docY: number, light: THREE.PointLight) => {
        light.position.copy(toScene(xAtY(docY), docY - scrollY, RADIUS + 4))
        light.intensity = prefersReduced ? 1 : 3.4 + wirePulse * 4.5
      }
      lightAt(phase1, travelLight)
      lightAt(phase2, travelLight2)

      renderer.render(scene, camera)
      if (!prefersReduced) t += 1 / 60
      raf = requestAnimationFrame(draw)
    }

    const onMove = (e: PointerEvent) => {
      mouse.x = e.clientX
      mouse.y = e.clientY
      mouse.active = true
    }
    const onLeave = () => {
      mouse.active = false
    }

    measure()
    draw()

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

    const io = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting
    })
    io.observe(mount)

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
      clearRunGroup()
      jacketMat.dispose()
      tracerMat.dispose()
      tieMat.dispose()
      copperMat.dispose()
      grainTex.dispose()
      renderer.dispose()
      if (renderer.domElement.parentElement === mount) mount.removeChild(renderer.domElement)
    }
  }, [])

  return <div ref={mountRef} className="pointer-events-none fixed inset-0 -z-10" aria-hidden="true" />
}
