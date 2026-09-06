'use client'

import { useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Edges, Float } from '@react-three/drei'
import * as THREE from 'three'

const EDGE = '#7fd9e8'
const FILL = '#0f2a31'

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

function WireMesh({
  args,
  color = FILL,
  opacity = 0.35,
}: {
  args: [number, number, number]
  color?: string
  opacity?: number
}) {
  return (
    <mesh>
      <boxGeometry args={args} />
      <meshBasicMaterial color={color} transparent opacity={opacity} />
      <Edges color={EDGE} threshold={12} />
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
    const px = state.pointer.x
    const py = state.pointer.y
    group.current.rotation.y += 0.0035
    group.current.rotation.y += (px * 0.5 - (group.current.rotation.y % (Math.PI * 2)) * 0) * 0
    // subtle pointer tilt layered on top of continuous spin
    group.current.rotation.x = THREE.MathUtils.lerp(group.current.rotation.x, -py * 0.25 + 0.05, 0.05)
    group.current.position.y = Math.sin(state.clock.elapsedTime * 0.6) * 0.05
  })

  return (
    <group ref={group} scale={1.05}>
      {/* Foundation slab */}
      <Piece target={[0, -0.02, 0]} from={[0, -2.4, 0]} delay={0} reduced={reduced}>
        <WireMesh args={[3.4, 0.16, 3.4]} opacity={0.5} />
      </Piece>

      {/* Main walls */}
      <Piece target={[0, 0.95, 0]} from={[0, 4, 0]} delay={0.35} reduced={reduced}>
        <WireMesh args={[2.6, 1.8, 2.6]} />
      </Piece>

      {/* Left extension block */}
      <Piece target={[-1.9, 0.6, 0.4]} from={[-5, 0.6, 0.4]} delay={0.7} reduced={reduced}>
        <WireMesh args={[1.3, 1.1, 1.8]} opacity={0.3} />
      </Piece>

      {/* Roof — 4-sided pyramid */}
      <Piece target={[0, 2.35, 0]} from={[0, 6, 0]} delay={1.05} reduced={reduced}>
        <mesh rotation={[0, Math.PI / 4, 0]}>
          <coneGeometry args={[2.1, 1.2, 4]} />
          <meshBasicMaterial color={FILL} transparent opacity={0.4} />
          <Edges color={EDGE} threshold={12} />
        </mesh>
      </Piece>

      {/* Chimney */}
      <Piece target={[0.7, 2.7, 0.2]} from={[0.7, 6.5, 0.2]} delay={1.35} reduced={reduced}>
        <WireMesh args={[0.28, 0.7, 0.28]} opacity={0.55} />
      </Piece>

      {/* Door */}
      <Piece target={[0, 0.5, 1.31]} from={[0, -3, 1.31]} delay={1.5} reduced={reduced}>
        <WireMesh args={[0.5, 0.9, 0.06]} opacity={0.6} />
      </Piece>

      {/* Windows */}
      <Piece target={[-0.75, 1.0, 1.31]} from={[-4, 1.0, 1.31]} delay={1.65} reduced={reduced}>
        <WireMesh args={[0.5, 0.5, 0.06]} opacity={0.6} />
      </Piece>
      <Piece target={[0.75, 1.0, 1.31]} from={[4, 1.0, 1.31]} delay={1.75} reduced={reduced}>
        <WireMesh args={[0.5, 0.5, 0.06]} opacity={0.6} />
      </Piece>
    </group>
  )
}

function GroundGrid() {
  return (
    <gridHelper
      args={[16, 32, EDGE, EDGE]}
      position={[0, -0.12, 0]}
      // @ts-expect-error material opacity is valid on the helper's LineBasicMaterial
      material-transparent
      material-opacity={0.12}
    />
  )
}

export default function BuildScene() {
  const reduced =
    typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches

  return (
    <Canvas
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true }}
      camera={{ position: [5.5, 3.6, 6.5], fov: 42 }}
    >
      <ambientLight intensity={0.6} />
      <GroundGrid />
      {reduced ? (
        <House reduced />
      ) : (
        <Float speed={1.2} rotationIntensity={0.15} floatIntensity={0.25}>
          <House reduced={false} />
        </Float>
      )}
    </Canvas>
  )
}
