'use client'

import { useEffect, useRef, useState, type CSSProperties, type KeyboardEvent } from 'react'
import {
  ALL_SCENES,
  SHOWCASE_CYCLE_MS,
  SHOWCASE_TRADES,
  nextShowcaseIndex,
  showcaseIndexForTrade,
  type ShowcaseArt,
  type ShowcaseTrade,
} from '@/lib/showcase'

// The hero's centrepiece: a small, honest illustration of what the product
// is. A real-looking website for a trade, set in a 3D scene that turns to
// follow the cursor, annotated like a technical drawing - and switchable
// between trades, re-theming itself as it goes.
//
// It is deliberately a *picture of a site*, not a screenshot of a client:
// "YOUR FIRM" is a placeholder and nothing in it claims a result (see
// lib/showcase.ts). The whole preview is decorative, so it is hidden from
// assistive tech, with the switcher and one live sentence carrying the same
// information in a form a screen reader can use.
//
// Everything scales through container-query units (cqw) so the same markup
// holds up from a phone to a wide desktop without a JS resize observer.

type Vars = CSSProperties & Record<`--${string}`, string | number>

const HEX = /^#[0-9a-f]{6}$/i

/**
 * Their trade's scene with their own service names on the tiles (topped up
 * from the scene's own to make three) and their colour. The colour arrives
 * already darkened to take white text; the lighter version for this page's
 * dark background is mixed from it, the same way the scenes' own pairs are.
 */
function personalise(scene: ShowcaseTrade, firm?: { services?: string[]; accent?: string | null }): ShowcaseTrade {
  const own = (firm?.services ?? []).slice(0, 3)
  const seen = new Set(own.map((s) => s.toLowerCase()))
  const tiles = [...own, ...scene.tiles.filter((t) => !seen.has(t.toLowerCase()))].slice(0, 3) as ShowcaseTrade['tiles']
  const accent = firm?.accent && HEX.test(firm.accent) ? firm.accent : null
  return {
    ...scene,
    tiles: own.length >= 2 ? tiles : scene.tiles,
    ...(accent ? { accent, accentUi: `color-mix(in oklch, ${accent} 55%, white)` } : {}),
  }
}

export function SiteShowcase({
  initialTrade,
  firm,
  us = false,
}: {
  initialTrade?: string
  /** A US prospect's preview (lib/market.ts): "New lead" rather than "New enquiry". */
  us?: boolean
  /**
   * A real prospect's name and domain, on their private preview page (app/for/[slug]) -
   * and, when their homepage made them clear, their own service names and brand colour,
   * shown on their own trade's scene only.
   */
  firm?: { name: string; domain?: string | null; services?: string[]; accent?: string | null }
} = {}) {
  const firmName = firm?.name.toUpperCase() ?? 'YOUR FIRM'
  const firmDomain = firm?.domain || 'yourfirm.co.uk'
  const [active, setActive] = useState(() => showcaseIndexForTrade(initialTrade) ?? 0)
  const rootRef = useRef<HTMLDivElement>(null)
  const stageRef = useRef<HTMLDivElement>(null)
  const tiltRef = useRef<HTMLDivElement>(null)
  const tabRefs = useRef<(HTMLButtonElement | null)[]>([])
  const ownIndex = firm && initialTrade ? showcaseIndexForTrade(initialTrade) : null
  const trade = active === ownIndex ? personalise(ALL_SCENES[active], firm) : ALL_SCENES[active]
  // The homepage's trades, plus a preview-only scene (HVAC, plumbing, electrical) as an extra tab
  // when that's the one being shown - their own trade on a prospect's page, or a ?trade= link.
  const [extra, setExtra] = useState(() => {
    const i = showcaseIndexForTrade(initialTrade)
    return i !== null && i >= SHOWCASE_TRADES.length ? i : null
  })
  // Their own trade comes first: it's the one the page is about.
  const tabs = extra !== null ? [extra, ...SHOWCASE_TRADES.keys()] : [...SHOWCASE_TRADES.keys()]

  // Auto-rotation is driven by the switcher's own CSS progress bar: when its
  // animation ends, move on. That keeps the visible bar and the actual
  // timing in step for free, and pausing the animation (hover, focus,
  // offscreen) pauses the rotation with it. Choosing a tab yourself stops it.
  // On a prospect's own preview page, stay on their trade - rotating away
  // to someone else's would undo the point of the page.
  const [auto, setAuto] = useState(!(firm && initialTrade))

  // A visitor arriving from a trade-specific link (an outreach batch, a
  // trade page's own preview link) should land on the matching tab instead
  // of whatever the rotation happens to default to. This reads the URL
  // itself, after mount, rather than the page passing it down via Next's
  // `searchParams` - that would opt the whole (otherwise fully static)
  // homepage into per-request dynamic rendering just for this. The cost is
  // one extra render right after hydration for the handful of visitors who
  // arrive with a `?trade=` link; every other visitor pays nothing.
  useEffect(() => {
    if (initialTrade) return
    const idx = showcaseIndexForTrade(new URLSearchParams(window.location.search).get('trade'))
    // Syncing from an external system (the URL the page loaded with) into
    // React state once on mount - not reacting to props/state changing, so
    // the "don't setState synchronously in an effect" warning doesn't apply.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (idx !== null) setActive(idx)
    if (idx !== null && idx >= SHOWCASE_TRADES.length) setExtra(idx)
    // Mount-only: this is meant to read the URL the page was loaded with,
    // not to react to later client-side navigation within the SPA.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const root = rootRef.current
    const stage = stageRef.current
    const tilt = tiltRef.current
    if (!root || !stage || !tilt) return

    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const fine = window.matchMedia('(hover: hover) and (pointer: fine)').matches

    // Pause the auto-rotation while it can't be seen or is being looked at.
    let hovering = false
    let offscreen = false
    const syncPause = () => root.toggleAttribute('data-paused', hovering || offscreen)
    const onEnter = () => {
      hovering = true
      syncPause()
    }
    const onLeave = () => {
      hovering = false
      syncPause()
    }
    root.addEventListener('pointerenter', onEnter)
    root.addEventListener('pointerleave', onLeave)
    root.addEventListener('focusin', onEnter)
    root.addEventListener('focusout', onLeave)

    let visible = false
    const io = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting
      offscreen = !entry.isIntersecting
      syncPause()
      if (visible && !raf && tiltActive) raf = requestAnimationFrame(loop)
    })
    io.observe(root)

    // The 3D scene turns to face the cursor. Fine pointers only: a phone has
    // no pointer to follow, and reduced-motion asks for none of it.
    let tiltActive = false
    let raf = 0
    const cur = { rx: 0, ry: 0, gx: 30, gy: 20 }
    const tgt = { rx: 0, ry: 0, gx: 30, gy: 20 }

    const loop = () => {
      raf = 0
      if (!visible) return
      cur.rx += (tgt.rx - cur.rx) * 0.085
      cur.ry += (tgt.ry - cur.ry) * 0.085
      cur.gx += (tgt.gx - cur.gx) * 0.12
      cur.gy += (tgt.gy - cur.gy) * 0.12
      tilt.style.setProperty('--rx', `${cur.rx.toFixed(2)}deg`)
      tilt.style.setProperty('--ry', `${cur.ry.toFixed(2)}deg`)
      tilt.style.setProperty('--gx', `${cur.gx.toFixed(1)}%`)
      tilt.style.setProperty('--gy', `${cur.gy.toFixed(1)}%`)
      const settled =
        Math.abs(tgt.rx - cur.rx) < 0.01 &&
        Math.abs(tgt.ry - cur.ry) < 0.01 &&
        Math.abs(tgt.gx - cur.gx) < 0.05 &&
        Math.abs(tgt.gy - cur.gy) < 0.05
      if (!settled) raf = requestAnimationFrame(loop)
    }

    const clamp = (n: number) => Math.max(-1, Math.min(1, n))
    const onMove = (e: PointerEvent) => {
      if (e.pointerType === 'touch') return
      const r = stage.getBoundingClientRect()
      // Aim relative to the viewport, not just the element, so the scene
      // keeps looking toward the cursor from anywhere on screen.
      const nx = clamp((e.clientX - (r.left + r.width / 2)) / (window.innerWidth / 2))
      const ny = clamp((e.clientY - (r.top + r.height / 2)) / (window.innerHeight / 2))
      tgt.ry = nx * 11
      tgt.rx = -ny * 8
      tgt.gx = Math.max(0, Math.min(100, ((e.clientX - r.left) / r.width) * 100))
      tgt.gy = Math.max(0, Math.min(100, ((e.clientY - r.top) / r.height) * 100))
      if (visible && !raf) raf = requestAnimationFrame(loop)
    }

    if (!reduced && fine) {
      tiltActive = true
      window.addEventListener('pointermove', onMove, { passive: true })
    }

    return () => {
      cancelAnimationFrame(raf)
      io.disconnect()
      window.removeEventListener('pointermove', onMove)
      root.removeEventListener('pointerenter', onEnter)
      root.removeEventListener('pointerleave', onLeave)
      root.removeEventListener('focusin', onEnter)
      root.removeEventListener('focusout', onLeave)
    }
  }, [])

  const choose = (i: number) => {
    setActive(i)
    setAuto(false)
  }

  // Arrow-key navigation across the tabs, per the WAI-ARIA tabs pattern.
  // `pos` is the tab's place in the row; `tabs` maps it to its scene.
  const onTabKey = (e: KeyboardEvent<HTMLButtonElement>, pos: number) => {
    const n = tabs.length
    let to = -1
    if (e.key === 'ArrowRight') to = (pos + 1) % n
    else if (e.key === 'ArrowLeft') to = (pos - 1 + n) % n
    else if (e.key === 'Home') to = 0
    else if (e.key === 'End') to = n - 1
    if (to < 0) return
    e.preventDefault()
    choose(tabs[to])
    tabRefs.current[to]?.focus()
  }

  const rootVars: Vars = { '--accent': trade.accent, '--accent-ui': trade.accentUi }

  return (
    <div
      ref={rootRef}
      className="sc-root"
      style={rootVars}
      role="group"
      aria-label="Interactive preview: a website built for each trade"
    >
      <div ref={stageRef} className="sc-stage">
        <div ref={tiltRef} className="sc-tilt">
          {/* Drafting dimension line along the top edge */}
          <div className="sc-layer sc-dim" style={{ '--z': '30px' } as Vars} aria-hidden="true">
            <span className="sc-dim-tick" />
            <span className="sc-dim-line" />
            <span className="sc-dim-label">Fits every screen</span>
            <span className="sc-dim-line" />
            <span className="sc-dim-tick" />
          </div>

          <div className="sc-layer sc-shadow" style={{ '--z': '-70px' } as Vars} aria-hidden="true" />

          {/* ---- the website ---- */}
          <div className="sc-layer sc-window" style={{ '--z': '0px' } as Vars} aria-hidden="true">
            {/* The blueprint the site is built from on first load (app/intro.css). */}
            <span className="sc-blueprint" />
            <div className="sc-chrome">
              <span className="sc-dot" />
              <span className="sc-dot" />
              <span className="sc-dot" />
              <span className="sc-url">{firmDomain}</span>
            </div>

            <div key={trade.id} className="sc-site sc-swap">
              <div className="sc-nav">
                <div className="sc-brand">
                  <span className="sc-brand-mark" />
                  <span>
                    <span className="sc-brand-name">{firmName}</span>
                    <span className="sc-brand-sub">{trade.descriptor}</span>
                  </span>
                </div>
                <div className="sc-nav-links">
                  <span>Services</span>
                  <span>Our work</span>
                  <span>Contact</span>
                  <span className="sc-nav-cta">Quote</span>
                </div>
              </div>

              <div className="sc-hero">
                <div className="sc-copy">
                  <span className="sc-eyebrow">{trade.eyebrow}</span>
                  <h3 className="sc-headline">{trade.headline}</h3>
                  <p className="sc-sub">{trade.sub}</p>
                  <div className="sc-actions">
                    <span className="sc-btn sc-btn-primary">{trade.cta}</span>
                    <span className="sc-btn sc-btn-ghost">Our work</span>
                  </div>
                </div>
                <div className="sc-art">
                  <TradeArt kind={trade.art} />
                </div>
              </div>

              <div className="sc-tiles">
                {trade.tiles.map((label, i) => (
                  <div key={label} className="sc-tile">
                    <span className="sc-tile-swatch" style={{ '--i': i } as Vars} />
                    <span className="sc-tile-label">{label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* A light source that follows the cursor: the far edges darken. */}
            <div className="sc-shade" />
          </div>

          {/* ---- floating layers, each at its own depth ---- */}
          {/* Anchored to the phone, which never moves. A note pointing at a
              button inside the window would drift off it whenever the
              headline wraps differently from one trade to the next. */}
          <div className="sc-layer sc-callout" style={{ '--z': '96px' } as Vars} aria-hidden="true">
            <span className="sc-callout-dot" />
            <span className="sc-callout-line" />
            <span className="sc-callout-label">Tap to call · thumb reach</span>
          </div>

          <div className="sc-layer sc-chip sc-chip-speed" style={{ '--z': '78px' } as Vars} aria-hidden="true">
            <span className="sc-chip-dot" />
            {'<1s load'}
          </div>

          <div key={`t-${trade.id}`} className="sc-layer sc-toast sc-pop" style={{ '--z': '62px' } as Vars} aria-hidden="true">
            <span className="sc-toast-head">
              <span className="sc-chip-dot" />
              {us ? 'New lead' : 'New enquiry'}
            </span>
            <span className="sc-toast-title">{trade.enquiry}</span>
            <span className="sc-toast-meta">Just now · in your dashboard</span>
          </div>

          <div className="sc-layer sc-phone" style={{ '--z': '96px' } as Vars} aria-hidden="true">
            <div className="sc-phone-body">
              <span className="sc-phone-notch" />
              <div key={trade.id} className="sc-swap">
                <div className="sc-phone-brand">
                  <span className="sc-brand-mark" />
                  <span className="sc-phone-name">{firmName}</span>
                </div>
                <div className="sc-phone-headline">{trade.eyebrow}</div>
                <div className="sc-phone-call">
                  Tap to call
                  <span className="sc-phone-ring" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div role="tablist" aria-label="Choose a trade to preview" className="sc-tabs" data-count={tabs.length}>
        {tabs.map((i, pos) => {
          const t = ALL_SCENES[i]
          const on = i === active
          return (
            <button
              key={t.id}
              ref={(el) => {
                tabRefs.current[pos] = el
              }}
              type="button"
              role="tab"
              aria-selected={on}
              tabIndex={on ? 0 : -1}
              onClick={() => choose(i)}
              onKeyDown={(e) => onTabKey(e, pos)}
              className="sc-tab"
              data-magnetic
            >
              {t.tab}
              {on && auto && (
                <span
                  key={`p-${t.id}`}
                  className="sc-tab-progress"
                  style={{ animationDuration: `${SHOWCASE_CYCLE_MS}ms` }}
                  onAnimationEnd={() => setActive((a) => nextShowcaseIndex(a))}
                />
              )}
            </button>
          )
        })}
      </div>

      <p className="sr-only" aria-live="polite">
        Previewing a website for {trade.tab.toLowerCase()} firms: {trade.headline}
      </p>
    </div>
  )
}

// One small vector scene per trade, tinted by the previewed site's own brand
// colour. Vector rather than photography on purpose: nothing to download,
// nothing implying real work that isn't the visitor's, and it recolours for
// free when the accent changes.
function TradeArt({ kind }: { kind: ShowcaseArt }) {
  const id = `sc-${kind}`
  return (
    <svg viewBox="0 0 200 215" preserveAspectRatio="xMidYMid slice" className="sc-art-svg" aria-hidden="true">
      <defs>
        <linearGradient id={`${id}-sky`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--accent)" stopOpacity="0.16" />
          <stop offset="1" stopColor="var(--accent)" stopOpacity="0.05" />
        </linearGradient>
        <pattern
          id={`${id}-blocks`}
          width="28"
          height="14"
          patternUnits="userSpaceOnUse"
          patternTransform="rotate(-38)"
        >
          <rect x="1" y="1" width="12" height="5.2" rx="1" fill="var(--accent)" opacity="0.62" />
          <rect x="15" y="1" width="12" height="5.2" rx="1" fill="var(--accent)" opacity="0.4" />
          <rect x="8" y="8" width="12" height="5.2" rx="1" fill="var(--accent)" opacity="0.5" />
          <rect x="22" y="8" width="12" height="5.2" rx="1" fill="var(--accent)" opacity="0.68" />
          <rect x="-6" y="8" width="12" height="5.2" rx="1" fill="var(--accent)" opacity="0.68" />
        </pattern>
        <pattern id={`${id}-slate`} width="22" height="16" patternUnits="userSpaceOnUse">
          <path d="M0 0h22v9c-5.5 0-5.5 5-11 5S5.5 9 0 9z" fill="var(--accent)" opacity="0.5" />
          <path d="M-11 8h22v9c-5.5 0-5.5 5-11 5s-5.5-5-11-5z" fill="var(--accent)" opacity="0.34" />
          <path d="M11 8h22v9c-5.5 0-5.5 5-11 5s-5.5-5-11-5z" fill="var(--accent)" opacity="0.34" />
        </pattern>
      </defs>
      <rect width="200" height="215" fill={`url(#${id}-sky)`} />

      {kind === 'blocks' && (
        <>
          <circle cx="158" cy="42" r="14" fill="var(--accent)" opacity="0.14" />
          {/* house */}
          <path d="M44 92 100 44l56 48v30H44z" fill="#fff" opacity="0.92" />
          <path d="M44 92 100 44l56 48" fill="none" stroke="var(--accent)" strokeWidth="3" strokeLinejoin="round" />
          <rect x="86" y="96" width="28" height="26" fill="var(--accent)" opacity="0.85" />
          <rect x="54" y="98" width="20" height="16" fill="var(--accent)" opacity="0.28" />
          <rect x="126" y="98" width="20" height="16" fill="var(--accent)" opacity="0.28" />
          {/* lawn either side, block-paved drive sweeping to the door */}
          <path d="M0 122h200v93H0z" fill="var(--accent)" opacity="0.1" />
          <path d="M86 122h28l62 93H24z" fill={`url(#${id}-blocks)`} />
          <path d="M86 122h28l62 93H24z" fill="none" stroke="var(--accent)" strokeWidth="1.5" opacity="0.5" />
        </>
      )}

      {kind === 'roofline' && (
        <>
          <g fill="none" stroke="var(--accent)" strokeLinejoin="round" strokeLinecap="round">
            <path d="M22 132 100 42l78 90" strokeWidth="3.4" />
            <path d="M22 132h156" strokeWidth="3.4" />
            {/* rafters and purlins: the structure, drawn like a section */}
            <path d="M100 42v90M60 88v44M140 88v44M40 110l60-68 60 68" strokeWidth="1.4" opacity="0.55" />
            <path d="M52 100h96M40 116h120" strokeWidth="1.4" opacity="0.4" strokeDasharray="4 4" />
          </g>
          {/* dormer */}
          <path d="M120 96 148 96 148 132 120 132z" fill="#fff" opacity="0.94" />
          <path d="M116 98 134 82 152 98" fill="var(--accent)" opacity="0.85" />
          <rect x="126" y="106" width="16" height="16" fill="var(--accent)" opacity="0.3" />
          <path d="M126 114h16M134 106v16" stroke="var(--accent)" strokeWidth="1" opacity="0.7" />
          <path d="M0 150h200v65H0z" fill="var(--accent)" opacity="0.09" />
        </>
      )}

      {kind === 'slate' && (
        <>
          <circle cx="40" cy="44" r="13" fill="var(--accent)" opacity="0.14" />
          <path d="M30 74 170 58v112L30 186z" fill={`url(#${id}-slate)`} />
          <path d="M30 74 170 58v112L30 186z" fill="none" stroke="var(--accent)" strokeWidth="2.4" strokeLinejoin="round" />
          <path d="M30 74 170 58" stroke="var(--accent)" strokeWidth="6" strokeLinecap="round" opacity="0.7" />
          {/* chimney */}
          <path d="M132 62V34h22v26z" fill="var(--accent)" opacity="0.78" />
          <path d="M128 34h30" stroke="var(--accent)" strokeWidth="4" strokeLinecap="round" />
          <path d="M0 196h200v19H0z" fill="var(--accent)" opacity="0.1" />
        </>
      )}

      {kind === 'unit' && (
        <>
          <circle cx="160" cy="40" r="15" fill="var(--accent)" opacity="0.14" />
          {/* house wall with a window, the outdoor unit on its pad, air moving */}
          <path d="M0 40h92v135H0z" fill="#fff" opacity="0.9" />
          <rect x="22" y="62" width="44" height="34" fill="var(--accent)" opacity="0.22" />
          <path d="M44 62v34M22 79h44" stroke="var(--accent)" strokeWidth="1.4" opacity="0.6" />
          <rect x="104" y="112" width="78" height="62" rx="5" fill="#fff" opacity="0.95" />
          <rect x="104" y="112" width="78" height="62" rx="5" fill="none" stroke="var(--accent)" strokeWidth="2.6" />
          <circle cx="143" cy="143" r="22" fill="none" stroke="var(--accent)" strokeWidth="2" opacity="0.8" />
          <g stroke="var(--accent)" strokeWidth="1.4" opacity="0.55">
            <path d="M121 143h44M143 121v44M127.4 127.4l31.2 31.2M158.6 127.4l-31.2 31.2" />
          </g>
          <circle cx="143" cy="143" r="5" fill="var(--accent)" opacity="0.85" />
          <path d="M98 174h92v8H98z" fill="var(--accent)" opacity="0.45" />
          <g fill="none" stroke="var(--accent)" strokeWidth="2" strokeLinecap="round" opacity="0.5">
            <path d="M116 100c8-6 14 6 22 0s14 6 22 0" />
            <path d="M124 88c8-6 14 6 22 0s14 6 22 0" />
          </g>
          {/* thermostat on the wall */}
          <circle cx="44" cy="128" r="12" fill="var(--accent)" opacity="0.85" />
          <circle cx="44" cy="128" r="6" fill="#fff" opacity="0.9" />
          <path d="M0 182h200v33H0z" fill="var(--accent)" opacity="0.1" />
        </>
      )}

      {kind === 'pipes' && (
        <>
          <circle cx="40" cy="40" r="13" fill="var(--accent)" opacity="0.14" />
          {/* a pipe run with elbows and joints, ending at a tap with a drop */}
          <g fill="none" stroke="var(--accent)" strokeLinecap="round" strokeLinejoin="round">
            <path d="M0 160h70v-70h70v40" strokeWidth="12" opacity="0.32" />
            <path d="M0 160h70v-70h70v40" strokeWidth="4" opacity="0.85" />
          </g>
          <g fill="var(--accent)">
            <rect x="60" y="150" width="20" height="20" rx="3" opacity="0.8" />
            <rect x="60" y="80" width="20" height="20" rx="3" opacity="0.8" />
            <rect x="130" y="80" width="20" height="20" rx="3" opacity="0.8" />
            <rect x="34" y="153" width="8" height="14" rx="2" opacity="0.6" />
            <rect x="100" y="83" width="8" height="14" rx="2" opacity="0.6" />
          </g>
          <path d="M126 128h28v10h-28z" fill="var(--accent)" opacity="0.9" />
          <path d="M136 122h8v8h-8z" fill="var(--accent)" opacity="0.7" />
          <path d="M140 146c-5 8-8 12-8 16a8 8 0 0 0 16 0c0-4-3-8-8-16z" fill="var(--accent)" opacity="0.55" />
          <path d="M0 192h200v23H0z" fill="var(--accent)" opacity="0.1" />
        </>
      )}

      {kind === 'circuit' && (
        <>
          {/* a breaker panel beside a lit bulb */}
          <rect x="22" y="58" width="74" height="110" rx="5" fill="#fff" opacity="0.94" />
          <rect x="22" y="58" width="74" height="110" rx="5" fill="none" stroke="var(--accent)" strokeWidth="2.6" />
          <g fill="var(--accent)">
            {[0, 1, 2, 3, 4].map((row) => (
              <g key={row}>
                <rect x="34" y={72 + row * 18} width="20" height="10" rx="2" opacity={row % 2 ? 0.45 : 0.8} />
                <rect x="64" y={72 + row * 18} width="20" height="10" rx="2" opacity={row % 2 ? 0.8 : 0.45} />
              </g>
            ))}
          </g>
          <path d="M96 100h20c10 0 10-30 26-30" fill="none" stroke="var(--accent)" strokeWidth="2.4" opacity="0.6" />
          <circle cx="150" cy="70" r="20" fill="var(--accent)" opacity="0.85" />
          <circle cx="150" cy="70" r="30" fill="var(--accent)" opacity="0.14" />
          <rect x="143" y="90" width="14" height="12" rx="2" fill="var(--accent)" opacity="0.6" />
          <g stroke="var(--accent)" strokeWidth="2.4" strokeLinecap="round" opacity="0.55">
            <path d="M150 28v-10M184 70h10M176 44l7-7M124 44l-7-7M176 96l7 7" />
          </g>
          <path d="M0 186h200v29H0z" fill="var(--accent)" opacity="0.1" />
        </>
      )}

      {kind === 'hills' && (
        <>
          <circle cx="150" cy="50" r="17" fill="var(--accent)" opacity="0.16" />
          <path d="M0 118c30-30 62-30 94-6s62 22 106-12v115H0z" fill="var(--accent)" opacity="0.22" />
          <path d="M0 148c38-26 70-22 104 0s60 14 96-8v75H0z" fill="var(--accent)" opacity="0.38" />
          <path d="M0 178c44-18 84-12 118 6s58 6 82-6v37H0z" fill="var(--accent)" opacity="0.62" />
          {/* planting */}
          <g fill="var(--accent)">
            <circle cx="52" cy="112" r="11" opacity="0.7" />
            <rect x="50.5" y="118" width="3" height="14" opacity="0.7" />
            <circle cx="86" cy="122" r="8" opacity="0.55" />
            <rect x="85" y="126" width="2.4" height="10" opacity="0.55" />
            <circle cx="150" cy="128" r="12" opacity="0.6" />
            <rect x="148.6" y="135" width="3" height="14" opacity="0.6" />
          </g>
        </>
      )}
    </svg>
  )
}
