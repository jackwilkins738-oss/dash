'use client'

import { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Edges, Environment, ContactShadows, Float, MeshTransmissionMaterial } from '@react-three/drei'
import { EffectComposer, Bloom, Vignette } from '@react-three/postprocessing'
import * as THREE from 'three'

const EDGE = '#4d84c4'
const WALL = '#e8e4dc'
const ROOF = '#1c2226'
const CONCRETE = '#6b7075'
const CHIMNEY = '#4a4f54'
const GLASS = '#dff4f7'

const easeOutCubic = (t: number) => 1 - Math.pow(1 - t, 3)

type PieceProps = {
  target: [number, number, number]
  from: [number, number, number]
  delay: number
  reduced: boolean
  children: React.ReactNode
}

function Piece({ target, from, delay, reduced, children }: PieceProps) {
  const ref = useRef<THREE.Group>(null)
  const fromV = useMemo(() => new THREE.Vector3(...from), [from])
  const toV = useMemo(() => new THREE.Vector3(...target), [target])

  useFrame((state) => {
    if (!ref.current) return
    if (reduced) {
      ref.current.position.copy(toV)
      return
    }
    const raw = (state.clock.elapsedTime - delay) / 1.3
    const t = Math.min(1, Math.max(0, raw))
    ref.current.position.lerpVectors(fromV, toV, easeOutCubic(t))
  })

  return <group ref={ref}>{children}</group>
}

// A solid, properly-shaded volume - real roughness/clearcoat instead of a
// flat transparent fill, with the blueprint accent kept as a thin, low-
// opacity edge line rather than the whole story.
function SolidMesh({
  args,
  color,
  roughness = 0.6,
  metalness = 0,
  clearcoat = 0,
}: {
  args: [number, number, number]
  color: string
  roughness?: number
  metalness?: number
  clearcoat?: number
}) {
  return (
    <mesh castShadow receiveShadow>
      <boxGeometry args={args} />
      <meshPhysicalMaterial color={color} roughness={roughness} metalness={metalness} clearcoat={clearcoat} clearcoatRoughness={0.4} />
      <Edges color={EDGE} threshold={12} transparent opacity={0.35} />
    </mesh>
  )
}

// Real glass - transmission/refraction via drei's MeshTransmissionMaterial,
// instead of a flat cyan-tinted box standing in for a window.
function GlassMesh({ args }: { args: [number, number, number] }) {
  return (
    <mesh castShadow>
      <boxGeometry args={args} />
      <MeshTransmissionMaterial
        color={GLASS}
        transmission={1}
        thickness={0.15}
        roughness={0.04}
        ior={1.5}
        chromaticAberration={0.02}
        backside
      />
      <Edges color={EDGE} threshold={12} transparent opacity={0.4} />
    </mesh>
  )
}

function House({ reduced }: { reduced: boolean }) {
  const group = useRef<THREE.Group>(null)

  useFrame((state) => {
    if (!group.current) return
    if (reduced) {
      group.current.rotation.y = -0.5
      return
    }
    const py = state.pointer.y
    group.current.rotation.y += 0.0035
    group.current.rotation.x = THREE.MathUtils.lerp(group.current.rotation.x, -py * 0.25 + 0.05, 0.05)
    group.current.position.y = Math.sin(state.clock.elapsedTime * 0.6) * 0.05
  })

  return (
    <group ref={group} scale={1.05}>
      {/* Foundation slab */}
      <Piece target={[0, -0.02, 0]} from={[0, -2.4, 0]} delay={0} reduced={reduced}>
        <SolidMesh args={[3.4, 0.16, 3.4]} color={CONCRETE} roughness={0.85} />
      </Piece>

      {/* Main walls */}
      <Piece target={[0, 0.95, 0]} from={[0, 4, 0]} delay={0.35} reduced={reduced}>
        <SolidMesh args={[2.6, 1.8, 2.6]} color={WALL} roughness={0.6} clearcoat={0.15} />
      </Piece>

      {/* Left extension block */}
      <Piece target={[-1.9, 0.6, 0.4]} from={[-5, 0.6, 0.4]} delay={0.7} reduced={reduced}>
        <SolidMesh args={[1.3, 1.1, 1.8]} color={WALL} roughness={0.6} clearcoat={0.15} />
      </Piece>

      {/* Roof — 4-sided pyramid, brushed-metal tone, with a real eave
          overhang past the wall line rather than sitting flush */}
      <Piece target={[0, 2.3, 0]} from={[0, 6, 0]} delay={1.05} reduced={reduced}>
        <mesh rotation={[0, Math.PI / 4, 0]} castShadow receiveShadow>
          <coneGeometry args={[2.35, 1.2, 4]} />
          <meshPhysicalMaterial color={ROOF} roughness={0.32} metalness={0.65} />
          <Edges color={EDGE} threshold={12} transparent opacity={0.35} />
        </mesh>
      </Piece>

      {/* Chimney */}
      <Piece target={[0.7, 2.7, 0.2]} from={[0.7, 6.5, 0.2]} delay={1.35} reduced={reduced}>
        <SolidMesh args={[0.28, 0.7, 0.28]} color={CHIMNEY} roughness={0.7} />
      </Piece>

      {/* Door */}
      <Piece target={[0, 0.5, 1.31]} from={[0, -3, 1.31]} delay={1.5} reduced={reduced}>
        <GlassMesh args={[0.5, 0.9, 0.06]} />
      </Piece>

      {/* Windows */}
      <Piece target={[-0.75, 1.0, 1.31]} from={[-4, 1.0, 1.31]} delay={1.65} reduced={reduced}>
        <GlassMesh args={[0.5, 0.5, 0.06]} />
      </Piece>
      <Piece target={[0.75, 1.0, 1.31]} from={[4, 1.0, 1.31]} delay={1.75} reduced={reduced}>
        <GlassMesh args={[0.5, 0.5, 0.06]} />
      </Piece>
    </group>
  )
}

// A real ground surface, not just a shadow floating over nothing - this is
// most of what turns "object rendered on a page" into "product sitting on
// a studio floor." Cheap enough to keep on mobile too; only its shadow-
// receiving is gated behind heavyEffects.
function Floor({ receiveShadows }: { receiveShadows: boolean }) {
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.16, 0]} receiveShadow={receiveShadows}>
      {/* Was radius 9 - roughly 3x the house's own scale and nearly as far
          out as the camera itself, which very likely filled the entire
          frustum edge-to-edge and read as a solid black frame rather than
          a grounded studio floor. 4 keeps it a floor, not a wall. */}
      <circleGeometry args={[4, 48]} />
      <meshPhysicalMaterial color="#1a212c" roughness={0.75} metalness={0.05} />
    </mesh>
  )
}

// Faint grid kept above the floor - a nod to the blueprint concept without
// it being the ground's whole visual job any more.
function FaintGrid() {
  return (
    <gridHelper
      args={[16, 32, EDGE, EDGE]}
      position={[0, -0.15, 0]}
      // @ts-expect-error material opacity is valid on the helper's LineBasicMaterial
      material-transparent
      material-opacity={0.06}
    />
  )
}

export default function BuildScene() {
  const reduced =
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
  // Environment reflections + bloom are the expensive part of this scene -
  // skip them on small screens so mobile stays light, same reasoning as
  // the 2D fallback used for the hero's BlueprintCanvas.
  const isDesktop = typeof window !== 'undefined' && window.innerWidth >= 768
  const heavyEffects = isDesktop && !reduced

  return (
    <Canvas
      shadows={heavyEffects}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true }}
      onCreated={({ gl }) => {
        // Renderer properties like tone mapping aren't WebGLRenderer
        // constructor params, so they need to be set here rather than in
        // the gl prop object above - the previous approach silently
        // produced a fully black canvas instead of erroring.
        gl.toneMapping = THREE.ACESFilmicToneMapping
        gl.toneMappingExposure = 1.15
      }}
      camera={{ position: [5.5, 3.6, 6.5], fov: 42 }}
    >
      {/* Key light */}
      <directionalLight
        position={[4, 6, 3]}
        intensity={1.4}
        castShadow={heavyEffects}
        shadow-mapSize={[1024, 1024]}
      />
      {/* Soft cool fill from the opposite side, so the shadowed face of the
          house reads as lit-but-cooler rather than going flat black */}
      <directionalLight position={[-4, 3, -3]} intensity={0.35} color="#9db8d8" />
      {/* A touch of blueprint-blue rim light from behind, for edge
          separation against the dark background */}
      <pointLight position={[-3, 4, 4]} intensity={0.3} color="#4d84c4" />
      <ambientLight intensity={0.3} />
      <FaintGrid />
      <Floor receiveShadows={heavyEffects} />
      {heavyEffects && (
        <>
          <Environment preset="studio" />
          <ContactShadows position={[0, -0.13, 0]} opacity={0.55} scale={10} blur={2.4} far={4} resolution={512} />
        </>
      )}
      {reduced ? (
        <House reduced />
      ) : (
        <Float speed={1.2} rotationIntensity={0.15} floatIntensity={0.25}>
          <House reduced={false} />
        </Float>
      )}
      {heavyEffects && (
        <EffectComposer>
          <Bloom intensity={0.4} luminanceThreshold={0.65} luminanceSmoothing={0.9} mipmapBlur />
          <Vignette eskil={false} offset={0.15} darkness={0.6} />
        </EffectComposer>
      )}
    </Canvas>
  )
}
