'use client'

import { useEffect, useRef } from 'react'
import {
  ACESFilmicToneMapping,
  AdditiveBlending,
  BackSide,
  BoxGeometry,
  CanvasTexture,
  CatmullRomCurve3,
  CylinderGeometry,
  DirectionalLight,
  Group,
  HemisphereLight,
  Mesh,
  MeshBasicMaterial,
  MeshPhysicalMaterial,
  MeshStandardMaterial,
  OrthographicCamera,
  PMREMGenerator,
  PointLight,
  Quaternion,
  RepeatWrapping,
  Scene,
  SphereGeometry,
  TorusGeometry,
  TubeGeometry,
  Vector2,
  Vector3,
  WebGLRenderer,
} from 'three'
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js'
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js'
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js'

type Node = { baseX: number; x: number; y: number; vx: number }
type Anchor = { x: number; y: number }

const SPACING = 30
const RADIUS = 12
const LEG_HEIGHT = 640
const RENDER_BUFFER = 340
const GAP = 5

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
    let cancelled = false
    let cleanup: (() => void) | undefined

    // This setup is genuinely ~1.3s of synchronous work (largely WebGL
    // shader compilation + the PMREM environment bake), phase-split
    // across frames so it yields instead of blocking one long task (see
    // the repeated `await nextFrame()` calls below). The interaction
    // gating that used to live here - waiting for scroll/pointer/touch,
    // or a timed fallback - has moved up to power-cable-loader.tsx,
    // which now delays *mounting this component at all* until that
    // signal fires. That means the ~500KB Three.js chunk itself isn't
    // even fetched until then either, instead of downloading immediately
    // on page load while sitting unused for a couple of seconds.
    const nextFrame = () => new Promise<void>((resolve) => requestAnimationFrame(() => resolve()))

    void runInit()

    async function runInit() {
    const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    // Phones are pushing the same bloom-postprocessed WebGL scene, rebuilt
    // 30x/sec, on GPUs a fraction as capable as a desktop's - that's the
    // sitewide "lag," not just the resize glitch. Coarse pointer is a more
    // reliable signal than viewport width (a resized desktop window is
    // still a desktop GPU), so drop resolution/geometry detail and rebuild
    // less often there instead of paying full desktop quality everywhere.
    const isMobile = window.matchMedia('(pointer: coarse)').matches
    // Geometry only rebuilds (and the visible node range recomputes) at
    // FRAME_INTERVAL below - 20fps on mobile vs 30fps on desktop, so
    // there's ~1.5x longer between rebuilds for a fast touch-flick to
    // outrun the buffered range before it catches up again. Wider buffer
    // on mobile keeps segments from visibly popping in/out at the edges
    // during a fast scroll, which read as part of the same "shakiness."
    const renderBuffer = isMobile ? RENDER_BUFFER * 2 : RENDER_BUFFER
    // Fresh layout every visit - fixed seeds get memorised and stop reading
    // as "electric," they start reading as "the same decoration."
    const sessionSeed = (Date.now() ^ Math.floor(Math.random() * 2147483647)) >>> 0

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

    // ---- renderer / scene ---------------------------------------------
    const renderer = new WebGLRenderer({ antialias: !isMobile, alpha: true, powerPreference: 'low-power' })
    renderer.setClearColor(0x000000, 0)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, isMobile ? 1.5 : 2))
    renderer.toneMapping = ACESFilmicToneMapping
    renderer.toneMappingExposure = 1.2
    mount!.appendChild(renderer.domElement)

    // If unmounted mid-init (fast route change right after landing), at
    // minimum tear down the WebGL context and its canvas - that's the
    // scarce resource (browsers cap concurrent contexts); a few textures
    // or materials never wired up are comparatively harmless.
    const bailIfCancelled = () => {
      if (!cancelled) return false
      renderer.dispose()
      if (renderer.domElement.parentElement === mount) mount!.removeChild(renderer.domElement)
      return true
    }

    const scene = new Scene()
    const camera = new OrthographicCamera(-vw / 2, vw / 2, vh / 2, -vh / 2, -1000, 1000)
    camera.position.z = 500

    // Real bloom, not a color trick - this is what makes a spark or a
    // moving highlight actually look like it's emitting light.
    const composer = new EffectComposer(renderer)
    composer.addPass(new RenderPass(scene, camera))
    // UnrealBloomPass sizes its internal mip chain off this resolution -
    // halving it on mobile is the single biggest lever on its GPU cost,
    // and the blur already hides the drop in sharpness.
    const bloomRes = isMobile ? new Vector2(vw / 2, vh / 2) : new Vector2(vw, vh)
    const bloomPass = new UnrealBloomPass(bloomRes, 0.95, 0.55, 0.68)
    composer.addPass(bloomPass)

    const toScene = (px: number, pyViewport: number, z = 0) =>
      new Vector3(px - vw / 2, -(pyViewport - vh / 2), z)

    const key = new DirectionalLight(0xe4edff, 4.2)
    key.position.set(-120, 170, 260)
    scene.add(key)
    const fill = new HemisphereLight(0x6c86a8, 0x030405, 0.55)
    scene.add(fill)
    const rim = new DirectionalLight(0x5fa8e8, 1.4)
    rim.position.set(160, -100, 140)
    scene.add(rim)

    const travelLight = new PointLight(0x7fc4ff, 0, 260, 2)
    scene.add(travelLight)
    const travelLight2 = new PointLight(0x7fc4ff, 0, 200, 2)
    scene.add(travelLight2)

    if (bailIfCancelled()) return
    await nextFrame()
    if (bailIfCancelled()) return

    // Procedural fine-grain bump texture for the jacket surface - soft
    // blurred blobs rather than raw per-pixel noise, which reads as TV
    // static once magnified rather than a rubber weave.
    const noiseCanvas = document.createElement('canvas')
    noiseCanvas.width = 128
    noiseCanvas.height = 128
    const nctx = noiseCanvas.getContext('2d')!
    nctx.fillStyle = '#808080'
    nctx.fillRect(0, 0, 128, 128)
    nctx.filter = 'blur(1px)'
    for (let i = 0; i < 900; i++) {
      const v = 128 + (Math.random() - 0.5) * 100
      nctx.fillStyle = `rgb(${v},${v},${v})`
      nctx.beginPath()
      nctx.arc(Math.random() * 128, Math.random() * 128, 0.6 + Math.random() * 1.8, 0, Math.PI * 2)
      nctx.fill()
    }
    const grainTex = new CanvasTexture(noiseCanvas)
    grainTex.wrapS = RepeatWrapping
    grainTex.wrapT = RepeatWrapping
    // A TubeGeometry's V coordinate always spans 0-1 along its own length
    // regardless of how many world-units long that particular run is - the
    // texture needs an explicit repeat or it stretches into invisibility.
    grainTex.repeat.set(3, 22)

    await nextFrame()
    if (bailIfCancelled()) return

    // A simple procedural "room" the clearcoat can actually reflect -
    // without this, glossy/clearcoat properties have nothing to show and
    // the jacket reads flat no matter how it's lit directly.
    const pmrem = new PMREMGenerator(renderer)
    const envScene = new Scene()
    const envGeo = new SphereGeometry(50, 16, 16)
    const envMatTop = new MeshBasicMaterial({ color: 0x3a4a63, side: BackSide })
    const envSphere = new Mesh(envGeo, envMatTop)
    envScene.add(envSphere)
    const envLight1 = new PointLight(0xbcd6ff, 6, 90)
    envLight1.position.set(-20, 25, 10)
    envScene.add(envLight1)
    const envLight2 = new PointLight(0x2a3550, 4, 90)
    envLight2.position.set(15, -20, -10)
    envScene.add(envLight2)
    const envTarget = pmrem.fromScene(envScene, 0.06)
    scene.environment = envTarget.texture
    pmrem.dispose()
    envGeo.dispose()
    envMatTop.dispose()

    await nextFrame()
    if (bailIfCancelled()) return

    const jacketMat = new MeshPhysicalMaterial({
      color: 0x1a1c22,
      roughness: 0.38,
      metalness: 0.02,
      clearcoat: 0.7,
      clearcoatRoughness: 0.14,
      envMapIntensity: 0.9,
      bumpMap: grainTex,
      bumpScale: 0.5,
    })
    const shadowMat = new MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.4, depthWrite: false })
    const tracerMat = new MeshStandardMaterial({ color: 0xc9a15a, roughness: 0.4, metalness: 0.3 })
    const tieMat = new MeshStandardMaterial({ color: 0x2c3038, roughness: 0.45, metalness: 0.5 })
    const copperMat = new MeshStandardMaterial({
      color: 0xd98a3d,
      roughness: 0.35,
      metalness: 0.6,
      emissive: 0x3a1f0a,
      emissiveIntensity: 0.4,
    })
    const coreGlowMat = new MeshBasicMaterial({ color: 0x7fc4ff, transparent: true, opacity: 0.22 })
    const copperGlowMat = new MeshStandardMaterial({
      color: 0xd98a3d,
      roughness: 0.3,
      metalness: 0.65,
      emissive: 0xff8a2a,
      emissiveIntensity: 0.5,
    })

    const runGroup = new Group()
    scene.add(runGroup)
    const clearRunGroup = () => {
      for (const child of runGroup.children.slice()) {
        runGroup.remove(child)
        const mesh = child as Mesh
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

      // Full page height, not just down to the footer's top edge - the
      // wire should run the entire length of the site.
      docHeight = Math.max(document.documentElement.scrollHeight, document.body.scrollHeight)

      // Randomised zig-zag, reshuffled fresh each page load - variable leg
      // length, heavy edge jitter, and the occasional repeated-side leg so
      // the placement of every bend genuinely differs, not just its size.
      const rand = mulberry32(sessionSeed)
      anchors = [{ x: startX, y: 0 }]
      let side: 1 | -1 = 1
      let y = 0
      const span = endX - startX
      while (y < docHeight - LEG_HEIGHT * 0.35) {
        y += LEG_HEIGHT * (0.4 + rand() * 1.7)
        const repeatSide = rand() < 0.16
        const edge = (repeatSide ? side : side === 1 ? -1 : 1) === 1 ? endX : startX
        const jitter = (rand() - 0.5) * span * 0.55
        const x = Math.max(startX, Math.min(endX, edge + jitter))
        anchors.push({ x, y: Math.min(y, docHeight) })
        side = repeatSide ? side : side === 1 ? -1 : 1
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
      composer.setSize(vw, vh)
      bloomPass.resolution.set(isMobile ? vw / 2 : vw, isMobile ? vh / 2 : vh)
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
      const lo = Math.max(0, Math.floor((scrollY - renderBuffer) / SPACING) - 2)
      const hi = Math.min(nodes.length - 1, Math.ceil((scrollY + vh + renderBuffer) / SPACING) + 2)

      nodes[0].x += (nodes[0].baseX - nodes[0].x) * 0.18
      for (let i = Math.max(1, lo); i <= hi; i++) {
        const n = nodes[i]
        n.vx += (n.baseX - n.x) * 0.08
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

    const buildTubeForRun = (lo: number, hi: number) => {
      const pts: Vector3[] = []
      for (let i = lo; i <= hi; i++) {
        const n = nodes[i]
        const z = Math.sin(i * 0.22) * 5
        // Document-space Y, no scroll subtracted - scroll position is
        // applied once as a cheap group transform every real frame
        // instead of being baked into every rebuilt vertex (see draw()).
        pts.push(toScene(n.x, n.y, z))
      }
      const curve = new CatmullRomCurve3(pts, false, 'catmullrom', 0.15)
      // Rebuilt from scratch ~30x/sec (see draw()) - on mobile that's real
      // vertex-generation and GC cost per rebuild, so both the longitudinal
      // segment count and every tube's radial segment count get thinner.
      const segments = Math.max(4, (hi - lo) * (isMobile ? 1 : 2))
      const radial = (n: number) => (isMobile ? Math.max(5, Math.round(n * 0.6)) : n)

      // Contact shadow - darkens the page behind/below the cable so it
      // reads as sitting in front of something instead of floating on
      // nothing. Offset opposite the key light, drawn further from camera.
      const shadowPts = pts.map((p) => p.clone().add(new Vector3(6, -8, -18)))
      const shadowCurve = new CatmullRomCurve3(shadowPts, false, 'catmullrom', 0.15)
      const shadowGeo = new TubeGeometry(shadowCurve, segments, RADIUS * 1.1, radial(8), false)
      runGroup.add(new Mesh(shadowGeo, shadowMat))

      const geo = new TubeGeometry(curve, segments, RADIUS, radial(10), false)
      const mesh = new Mesh(geo, jacketMat)
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
        return p.clone().add(new Vector3(Math.cos(nrmAngle) * off, Math.sin(nrmAngle) * off, RADIUS * 0.6))
      })
      const tracerCurve = new CatmullRomCurve3(tracerPts, false, 'catmullrom', 0.15)
      const tracerGeo = new TubeGeometry(tracerCurve, segments, 1.5, radial(6), false)
      runGroup.add(new Mesh(tracerGeo, tracerMat))

      // Cable ties - small rings around the tube. Purely decorative detail
      // that's easy to lose on a small screen, so skip building them on
      // mobile entirely rather than just thinning them out.
      if (!isMobile) {
        for (let i = lo + 4; i < hi - 4; i += 9) {
          const idx = i - lo
          if (idx < 0 || idx >= pts.length) continue
          const p = pts[idx]
          const tangent = curve.getTangentAt(Math.min(0.999, Math.max(0.001, idx / (pts.length - 1))))
          const ring = new Mesh(new TorusGeometry(RADIUS * 1.15, 1.6, 8, 20), tieMat)
          ring.position.copy(p)
          const quat = new Quaternion().setFromUnitVectors(new Vector3(0, 0, 1), tangent)
          ring.setRotationFromQuaternion(quat)
          runGroup.add(ring)
        }
      }

      // Emissive core glow inside the jacket (shared material, mutated
      // once per frame in draw() - never allocate a material per call)
      const glowGeo = new TubeGeometry(curve, segments, RADIUS * 0.45, radial(8), false)
      runGroup.add(new Mesh(glowGeo, coreGlowMat))
    }

    // A proper lightning bolt: fractal midpoint displacement for a jagged
    // path, then built as real glowing geometry (a bright core tube inside
    // a soft additive halo tube) so bloom picks it up - a THREE.Line is
    // a 1px hairline on almost every GPU and will never read as a shock.
    const boltCore = new MeshBasicMaterial({
      color: 0xf3fbff,
      transparent: true,
      blending: AdditiveBlending,
      depthWrite: false,
    })
    const boltHalo = new MeshBasicMaterial({
      color: 0x6fc2ff,
      transparent: true,
      blending: AdditiveBlending,
      depthWrite: false,
    })
    const buildBolt = (origin: Vector3, target: Vector3, strength: number) => {
      let pts = [origin.clone(), target.clone()]
      for (let iter = 0; iter < 4; iter++) {
        const scale = (target.distanceTo(origin) || 20) * 0.22 * Math.pow(0.52, iter)
        const next: Vector3[] = [pts[0]]
        for (let i = 0; i < pts.length - 1; i++) {
          const p0 = pts[i]
          const p1 = pts[i + 1]
          const dir = p1.clone().sub(p0)
          const len = dir.length() || 1
          const perp = new Vector3(-dir.y, dir.x, 0).normalize()
          const mid = p0
            .clone()
            .lerp(p1, 0.5)
            .add(perp.multiplyScalar((Math.random() - 0.5) * 2 * scale))
            .add(new Vector3(0, 0, (Math.random() - 0.5) * scale * 0.7))
          next.push(mid, p1)
        }
        pts = next
      }
      if (pts.length < 2) return
      const curve = new CatmullRomCurve3(pts, false, 'catmullrom', 0.05)
      const segs = Math.max(8, pts.length * 2)
      boltCore.opacity = 0.75 + strength * 0.25
      boltHalo.opacity = 0.3 + strength * 0.45
      runGroup.add(new Mesh(new TubeGeometry(curve, segs, 0.9 + strength * 0.5, 5, false), boltCore))
      runGroup.add(new Mesh(new TubeGeometry(curve, segs, 3.2 + strength * 2.2, 6, false), boltHalo))
    }

    const buildFrayed = (i: number, forward: 1 | -1) => {
      const n = nodes[i]
      if (!n) return
      const base = toScene(n.x, n.y, 0)
      for (let s = 0; s < 5; s++) {
        const spread = (s / 4 - 0.5) * 1.4
        const len = 14 + Math.sin(t * 3 + s) * 4
        const dir = new Vector3(Math.sin(spread), -forward * Math.cos(spread) * 0.4, Math.cos(spread) * 0.6)
          .normalize()
          .multiplyScalar(len)
        const cyl = new Mesh(new CylinderGeometry(0.6, 0.15, len, 5), copperMat)
        cyl.position.copy(base).add(dir.clone().multiplyScalar(0.5))
        cyl.quaternion.setFromUnitVectors(new Vector3(0, 1, 0), dir.clone().normalize())
        runGroup.add(cyl)
      }
    }

    // A knife-slash gouge in the jacket - doesn't sever the run, just
    // exposes the conductor and arcs on its own irregular cycle.
    const buildSlash = (i: number) => {
      const n = nodes[i]
      const a = nodes[Math.max(0, i - 2)]
      const b = nodes[Math.min(nodes.length - 1, i + 2)]
      if (!n || !a || !b) return
      const pa = toScene(a.x, a.y, 0)
      const pb = toScene(b.x, b.y, 0)
      const base = toScene(n.x, n.y, 0)
      const tangent = pb.clone().sub(pa).normalize()
      const front = base.clone().add(new Vector3(0, 0, RADIUS * 0.92))

      // Diagonal cut across the jacket surface - bigger, unmissable
      const gash = new Mesh(new BoxGeometry(RADIUS * 2.4, 5, 2.4), tieMat)
      gash.position.copy(front)
      const gashQuat = new Quaternion().setFromUnitVectors(new Vector3(1, 0, 0), tangent)
      gash.quaternion.copy(gashQuat)
      gash.rotateZ(Math.PI / 2.6)
      runGroup.add(gash)

      // Exposed copper conductor in the wound - glows faintly even between
      // discharges, so the damage still reads when it isn't actively arcing
      copperGlowMat.emissiveIntensity = 0.5 + Math.max(0, Math.sin(t * 5 + i)) * 0.6
      const copper = new Mesh(new CylinderGeometry(2, 2, RADIUS * 1.6, 10), copperGlowMat)
      copper.position.copy(front).add(new Vector3(0, 0, 0.8))
      copper.quaternion.copy(gashQuat)
      copper.rotateZ(Math.PI / 2.6)
      runGroup.add(copper)

      // Irregular arcing - phase seeded per slash so they never fire in
      // sync, but frequent enough that scrolling past one, you'll see it.
      const phase = (t * (1.1 + (i % 5) * 0.22) + i * 3.1) % 4
      if (phase > 2.55) {
        const burst = Math.min(1, (phase - 2.55) / 0.25)
        const strength = burst < 1 ? burst : Math.max(0, 1 - (phase - 2.8) / 1.2)
        const boltCount = 2 + (i % 3)
        for (let s = 0; s < boltCount; s++) {
          const ang = (i * 1.7 + s * 2.4) % (Math.PI * 2)
          const tilt = Math.sin(i + s) * 0.6
          const len = 20 + strength * 22
          const dir = new Vector3(Math.cos(ang), Math.sin(ang) * 0.5 + tilt, 0.5 + Math.sin(ang * 2) * 0.5)
            .normalize()
            .multiplyScalar(len)
          buildBolt(front, front.clone().add(dir), strength)
        }
        const flash = new PointLight(0x8fd0ff, strength * 5.5, 220, 2)
        flash.position.copy(front)
        runGroup.add(flash)
      }
    }

    const buildSparkGap = (bs: number, be: number) => {
      const a = nodes[bs - 1]
      const b = nodes[be + 1]
      if (!a || !b) return
      buildFrayed(bs - 1, 1)
      buildFrayed(be + 1, -1)

      const cycle = (t * 1.1 + bs) % 3
      if (cycle > 1.7) {
        const strength = Math.min(1, (cycle - 1.7) / 0.5)
        const p0 = toScene(a.x, a.y, 4)
        const p1 = toScene(b.x, b.y, 4)
        buildBolt(p0, p1, strength)
        const flashLight = new PointLight(0x9fd6ff, strength * 4.5, 200, 2)
        flashLight.position.copy(p0.clone().lerp(p1, 0.5))
        runGroup.add(flashLight)
      }
    }

    // Rebuilding real TubeGeometry objects (jacket, glow, shadow, tracer,
    // ties) for the whole visible range is genuinely heavy CPU/GPU work,
    // so that part is throttled to ~30fps. But baking the scroll offset
    // directly into those rebuilt vertices meant the cable's on-screen
    // position only updated 30 times a second too - visible as a shake/
    // judder while scrolling, since scroll position itself changes every
    // real frame. Fixed by separating the two: geometry is now built in
    // document space (no scroll baked in) and repositioned every real
    // frame via a single cheap group transform, so scroll-tracking stays
    // smooth at 60fps regardless of how often the geometry itself rebuilds.
    let lastFrameTime = 0
    const FRAME_INTERVAL = 1000 / (isMobile ? 20 : 30)

    const draw = () => {
      raf = requestAnimationFrame(draw)
      if (!visible) return

      // Mobile browsers rubber-band/overscroll at the top and bottom of
      // the page - window.scrollY genuinely goes negative or past the max
      // scrollable distance for the duration of that bounce. Applying that
      // raw value directly to the whole group's position every frame made
      // the entire wire visibly judder in sync with the bounce - that's
      // the mobile-specific "shakiness", not a rendering-rate issue.
      // Desktop wheel/trackpad scrolling doesn't overshoot this way, so
      // clamping is a no-op there.
      const maxScroll = Math.max(0, docHeight - vh)
      const scrollY = Math.max(0, Math.min(window.scrollY, maxScroll))
      runGroup.position.y = scrollY

      const now = performance.now()
      if (now - lastFrameTime >= FRAME_INTERVAL) {
        lastFrameTime = now
        updateWirePulse()
        simulate()
        clearRunGroup()
        coreGlowMat.opacity = 0.22 + wirePulse * 0.16

        const lo = Math.max(0, Math.floor((scrollY - renderBuffer) / SPACING) - 2)
        const hi = Math.min(nodes.length - 1, Math.ceil((scrollY + vh + renderBuffer) / SPACING) + 2)

        for (const [lo2, hi2] of runsInRange(lo, hi)) buildTubeForRun(lo2, hi2)
        for (const [bs, be] of breaks) {
          if (be >= lo && bs <= hi) buildSparkGap(bs, be)
        }
        for (const si of slashes) {
          if (si >= lo && si <= hi) buildSlash(si)
        }
      }

      // Travelling current - every real frame (cheap, no geometry rebuild)
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
      const lightAt = (docY: number, light: PointLight) => {
        light.position.copy(toScene(xAtY(docY), docY - scrollY, RADIUS + 4))
        light.intensity = prefersReduced ? 1 : 3.4 + wirePulse * 4.5
      }
      lightAt(phase1, travelLight)
      lightAt(phase2, travelLight2)

      composer.render()
      if (!prefersReduced) t += 1 / 60
    }

    await nextFrame()
    if (bailIfCancelled()) return

    measure()
    draw()

    // Mobile browsers fire `resize` on their own scroll-driven address-bar
    // show/hide - purely a viewport *height* change, dozens of times over
    // the course of a scroll. Rerunning measure() on every one of those
    // rebuilds the whole node/anchor array and touches the bloom pass's
    // render targets, which is exactly the kind of work that shows up as
    // visible stutter/glitching on a phone. Only a genuine width change
    // (rotate, actual resize) warrants that; height-only churn is ignored.
    let resizeTimer = 0
    let lastWidth = window.innerWidth
    const onResize = () => {
      if (window.innerWidth === lastWidth) return
      lastWidth = window.innerWidth
      window.clearTimeout(resizeTimer)
      resizeTimer = window.setTimeout(measure, 120)
    }
    window.addEventListener('resize', onResize)
    // Not also calling updateWirePulse from a scroll listener on purpose -
    // it already runs every throttled draw() cycle below. Scroll events
    // fire far more often than that during touch/momentum scrolling, and
    // since the smoothing step (wirePulse += (proximity - wirePulse) *
    // 0.06) compounds per call rather than per unit time, calling it from
    // both meant the glow's convergence rate became scroll-frequency-
    // dependent - fast on a mobile flick, slower on a mouse wheel tick.
    // That rate inconsistency was part of what read as "shaky."

    const ro = new ResizeObserver(onResize)
    ro.observe(document.body)

    const io = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting
    })
    io.observe(mount!)

    const settleTimers = [200, 800, 1800].map((ms) => window.setTimeout(measure, ms))

    cleanup = () => {
      cancelAnimationFrame(raf)
      window.clearTimeout(resizeTimer)
      settleTimers.forEach(window.clearTimeout)
      window.removeEventListener('resize', onResize)
      ro.disconnect()
      io.disconnect()
      clearRunGroup()
      jacketMat.dispose()
      tracerMat.dispose()
      tieMat.dispose()
      copperMat.dispose()
      coreGlowMat.dispose()
      shadowMat.dispose()
      envTarget.dispose()
      copperGlowMat.dispose()
      boltCore.dispose()
      boltHalo.dispose()
      grainTex.dispose()
      composer.dispose()
      renderer.dispose()
      if (renderer.domElement.parentElement === mount) mount!.removeChild(renderer.domElement)
    }
    }

    return () => {
      cancelled = true
      cleanup?.()
    }
  }, [])

  return <div ref={mountRef} className="pointer-events-none fixed inset-0 -z-10" aria-hidden="true" />
}
