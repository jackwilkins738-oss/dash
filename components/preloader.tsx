import type { CSSProperties } from 'react'

// The build-a-house curtain that opens the site on a first visit.
//
// A server component with no JavaScript at all. The whole sequence - the
// drawing, the counter, the curtain lifting - is CSS in app/intro.css and
// starts on the first paint. It used to be a client component driven by a GSAP
// timeline that could only start once the JS had been downloaded and the page
// hydrated, which on a phone meant the visitor stared at a static overlay for
// seconds before the animation even began.
//
// Returning visitors never see it: a script in <head> (lib/intro.ts) marks
// the document before first paint and the CSS hides this whole block.

// Sets --i, the element's position within its staggered group.
const at = (i: number): CSSProperties => ({ ['--i' as string]: i })

const NODES: [number, number][] = [
  [150, 178],
  [237, 128],
  [77, 136],
  [150, 102],
  [157, 10],
]

export function Preloader() {
  return (
    <div className="pl-root" aria-hidden="true">
      {/* Split-panel curtain */}
      <div className="pl-panel absolute inset-0 blueprint-grid bg-background" style={at(0)} />
      <div className="pl-panel absolute inset-0 bg-background/60" style={at(1)} />

      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <svg
          viewBox="0 0 300 230"
          className="w-[280px] max-w-[76vw] sm:w-[360px]"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <defs>
            {/* Real cross-hatch fill for the wall faces, the way a section
                drawing actually renders a solid material - not a flat tint. */}
            <pattern id="pl-hatch" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="5" stroke="var(--blueprint)" strokeWidth="1" />
            </pattern>
          </defs>

          {/* Materialized fills (revealed at the end) - two hatched wall
              faces, two flat-tinted roof slopes, isometric */}
          <g className="bp-fill" style={at(0)} fill="url(#pl-hatch)" opacity="0.6" stroke="none">
            <path d="M150 178 L237 128 L237 52 L150 102 Z" />
          </g>
          <g className="bp-fill" style={at(1)} fill="url(#pl-hatch)" opacity="0.6" stroke="none">
            <path d="M150 178 L77 136 L77 60 L150 102 Z" />
          </g>
          <g className="bp-fill" style={at(2)} fill="var(--blueprint)" opacity="0.16" stroke="none">
            <path d="M150 102 L237 52 L157 10 Z" />
          </g>
          <g className="bp-fill" style={at(3)} fill="var(--blueprint)" opacity="0.24" stroke="none">
            <path d="M150 102 L77 60 L157 10 Z" />
          </g>

          {/* Ground line, isometric */}
          <path className="bp-draw bp-ground" pathLength={1} d="M53 137 L261 126" stroke="var(--blueprint)" strokeWidth="1.5" />

          {/* Walls: shared front edge, then each face's perimeter */}
          <path className="bp-draw bp-wall" style={at(0)} pathLength={1} d="M150 178 L150 102" stroke="var(--blueprint)" strokeWidth="1.5" />
          <path className="bp-draw bp-wall" style={at(1)} pathLength={1} d="M150 178 L237 128 L237 52 L150 102" stroke="var(--blueprint)" strokeWidth="1.5" />
          <path className="bp-draw bp-wall" style={at(2)} pathLength={1} d="M150 178 L77 136 L77 60 L150 102" stroke="var(--blueprint)" strokeWidth="1.5" />

          {/* Hip roof, isometric - two visible slopes to a single ridge apex */}
          <path className="bp-draw bp-roof" pathLength={1} d="M150 102 L157 10 L237 52 M157 10 L77 60" stroke="var(--blueprint)" strokeWidth="1.5" />

          {/* Details: door + two windows, each a proper isometric parallelogram */}
          <path className="bp-draw bp-detail" style={at(0)} pathLength={1} d="M155 175 L168 168 L168 132 L155 139 Z" stroke="var(--blueprint)" strokeWidth="1" />
          <path className="bp-draw bp-detail" style={at(1)} pathLength={1} d="M183 142 L201 132 L201 109 L183 119 Z" stroke="var(--blueprint)" strokeWidth="1" />
          <path className="bp-draw bp-detail" style={at(2)} pathLength={1} d="M117 142 L99 132 L99 109 L117 119 Z" stroke="var(--blueprint)" strokeWidth="1" />

          {/* Structural corner nodes */}
          {NODES.map(([cx, cy], i) => (
            <circle key={`${cx}-${cy}`} className="bp-node" style={at(i)} cx={cx} cy={cy} r="2.75" fill="var(--blueprint)" />
          ))}

          {/* Dimension lines with real callouts - width along the ground
              edge, height along the front corner, drafting-style extension
              ticks off each measured edge */}
          <g className="bp-dim" style={at(0)} stroke="var(--muted-foreground)" strokeWidth="0.6">
            <path d="M150 178 L157 190" />
            <path d="M237 128 L244 140" />
            <path d="M157 190 L244 140" />
          </g>
          <text className="bp-dim" style={at(1)} x="188" y="172" textAnchor="middle" fill="var(--muted-foreground)" fontSize="7" fontFamily="var(--font-mono)">
            3600
          </text>
          <g className="bp-dim" style={at(2)} stroke="var(--muted-foreground)" strokeWidth="0.6">
            <path d="M150 178 L136 178" />
            <path d="M150 102 L136 102" />
            <path d="M136 178 L136 102" />
          </g>
          <text className="bp-dim" style={at(3)} x="112" y="143" textAnchor="middle" fill="var(--muted-foreground)" fontSize="7" fontFamily="var(--font-mono)">
            3200
          </text>
          <text className="bp-dim" style={at(4)} x="150" y="214" textAnchor="middle" fill="var(--muted-foreground)" fontSize="9" fontFamily="var(--font-mono)">
            A-101
          </text>

          {/* Materialize flash */}
          <rect className="bp-flash" x="0" y="0" width="300" height="230" fill="var(--blueprint)" opacity="0" />
        </svg>

        <div className="pl-word mt-6 flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/mark.png" alt="" width={195} height={191} className="h-9 w-auto" />
          <span className="h-4 w-px bg-line" />
          <span className="font-mono text-[11px] uppercase tracking-[0.3em] text-muted-foreground">
            Scalar Digital
          </span>
        </div>

        <div className="mt-6 flex w-60 max-w-[76vw] items-center justify-between font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground">
          <span>Constructing</span>
          <span className="text-blueprint">
            <span className="pl-pad">0</span>
            <span className="pl-count" />
          </span>
        </div>
        <div className="mt-3 h-px w-60 max-w-[76vw] overflow-hidden bg-line">
          <div className="pl-bar h-full w-full bg-blueprint" />
        </div>
      </div>
    </div>
  )
}
