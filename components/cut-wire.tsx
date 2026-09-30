// "Cut the wire and it's dead in seconds" - shown, not just said. A live cable
// runs across the top of the section with power pulsing along it; as the
// reader scrolls into the argument it snaps, sparks, and the far half goes
// dark while the near half keeps pushing current into nothing.
//
// A server component with no JavaScript: the snap is a CSS scroll-driven
// animation (app/globals.css, .cw-*), so it moves exactly at the reader's pace
// on the compositor. Where scroll timelines aren't supported, and under
// reduced motion, it simply shows the cut wire.
export function CutWire() {
  // Both halves are the same gentle S-curve, mirrored about the centre.
  const left = 'M0 44 C 140 44, 200 18, 300 30 S 430 58, 488 44'
  const right = 'M512 44 C 570 30, 700 16, 800 34 S 900 44, 1000 44'
  return (
    <div className="cw-root relative mx-auto mb-14 h-24 w-full max-w-5xl" aria-hidden="true">
      <svg viewBox="0 0 1000 88" preserveAspectRatio="none" className="absolute inset-0 h-full w-full overflow-visible">
        <defs>
          <filter id="cw-glow" x="-10%" y="-200%" width="120%" height="500%">
            <feGaussianBlur stdDeviation="4" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* The join: the piece of cable that is there until it isn't */}
        <path className="cw-join" d="M484 44 L516 44" stroke="oklch(0.42 0.06 244)" strokeWidth="7" strokeLinecap="round" vectorEffect="non-scaling-stroke" />

        <g className="cw-left">
          <path d={left} stroke="oklch(0.42 0.06 244)" strokeWidth="7" fill="none" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
          <path className="cw-current" d={left} pathLength={1000} stroke="oklch(0.78 0.14 236)" strokeWidth="4.5" fill="none" strokeLinecap="round" vectorEffect="non-scaling-stroke" filter="url(#cw-glow)" />
          {/* Bare copper at the cut end */}
          <path className="cw-copper" d="M488 44 l12 -5 M488 44 l14 1 M488 44 l11 6" stroke="var(--brass)" strokeWidth="2.5" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
        </g>

        <g className="cw-right">
          <path className="cw-right-cable" d={right} stroke="oklch(0.42 0.06 244)" strokeWidth="7" fill="none" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
          <path className="cw-current cw-current-right" d={right} pathLength={1000} stroke="oklch(0.78 0.14 236)" strokeWidth="4.5" fill="none" strokeLinecap="round" vectorEffect="non-scaling-stroke" filter="url(#cw-glow)" />
          <path className="cw-copper" d="M512 44 l-12 -5 M512 44 l-14 1 M512 44 l-11 6" stroke="var(--brass)" strokeWidth="2.5" strokeLinecap="round" vectorEffect="non-scaling-stroke" />
        </g>
      </svg>

      {/* The spark, in HTML so it stays round whatever the section's width */}
      <span className="cw-spark" />
    </div>
  )
}
