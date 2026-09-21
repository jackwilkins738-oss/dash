'use client'

import { useEffect, useRef } from 'react'

// One client component that owns every pointer-driven flourish on the site,
// wired through delegation on `document` rather than a listener per element.
// That is what lets the cards, buttons and headings it affects stay plain
// server-rendered markup: they opt in with a data attribute and nothing else.
//
//   [data-spotlight]  a glow and lit edge that follow the pointer
//   [data-magnetic]   leans toward the pointer while it is over the element
//   the crosshair     trails the native cursor and reads out coordinates
//   the top hairline  fills with scroll progress
//
// Nothing here replaces the native cursor or changes how anything is
// clicked. Fine pointers only for the cursor effects (a phone has no
// pointer to follow), and none of the motion runs under reduced-motion.

const INTERACTIVE = 'a[href], button, [role="tab"], [role="button"], summary, label[for]'
const TEXT_ENTRY = 'input, textarea, select, [contenteditable="true"]'

const pad = (n: number) => String(Math.max(0, Math.round(n))).padStart(4, '0')

export function InteractionLayer() {
  const cursorRef = useRef<HTMLDivElement>(null)
  const labelRef = useRef<HTMLSpanElement>(null)
  const progressRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches
    const cursor = cursorRef.current
    const label = labelRef.current
    const progress = progressRef.current

    // ---- scroll progress ----------------------------------------------
    let progressRaf = 0
    const updateProgress = () => {
      progressRaf = 0
      if (!progress) return
      const max = document.documentElement.scrollHeight - window.innerHeight
      const p = max > 0 ? Math.min(1, Math.max(0, window.scrollY / max)) : 0
      progress.style.setProperty('--p', p.toFixed(4))
    }
    const onScroll = () => {
      if (!progressRaf) progressRaf = requestAnimationFrame(updateProgress)
    }
    updateProgress()
    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('resize', onScroll, { passive: true })

    if (!finePointer) {
      return () => {
        cancelAnimationFrame(progressRaf)
        window.removeEventListener('scroll', onScroll)
        window.removeEventListener('resize', onScroll)
      }
    }

    // ---- spotlight + magnetic (delegated) -----------------------------
    let lit: HTMLElement | null = null
    let magnet: HTMLElement | null = null

    const releaseMagnet = () => {
      if (magnet) magnet.style.translate = ''
      magnet = null
    }

    // ---- crosshair ------------------------------------------------------
    const target = { x: -100, y: -100 }
    const pos = { x: -100, y: -100 }
    let cursorRaf = 0
    let shown = false
    let lastLabel = ''

    const tick = () => {
      cursorRaf = 0
      // Ease toward the pointer; stop the loop once it has caught up so an
      // idle pointer costs nothing.
      pos.x += (target.x - pos.x) * 0.22
      pos.y += (target.y - pos.y) * 0.22
      if (cursor) cursor.style.transform = `translate3d(${pos.x.toFixed(1)}px, ${pos.y.toFixed(1)}px, 0)`
      if (Math.abs(target.x - pos.x) > 0.15 || Math.abs(target.y - pos.y) > 0.15) {
        cursorRaf = requestAnimationFrame(tick)
      }
    }

    const setLabel = (text: string) => {
      if (label && text !== lastLabel) {
        label.textContent = text
        lastLabel = text
      }
    }

    const onMove = (e: PointerEvent) => {
      if (e.pointerType === 'touch') return
      const el = e.target instanceof Element ? e.target : null

      // Spotlight: light the nearest opted-in ancestor and track the pointer
      // inside it. Only that one element is measured, on hover.
      const card = el?.closest<HTMLElement>('[data-spotlight]') ?? null
      if (card !== lit) {
        lit?.removeAttribute('data-lit')
        lit = card
        lit?.setAttribute('data-lit', '')
      }
      if (card) {
        const r = card.getBoundingClientRect()
        card.style.setProperty('--mx', `${e.clientX - r.left}px`)
        card.style.setProperty('--my', `${e.clientY - r.top}px`)
      }

      // Magnetic: lean toward the pointer, capped, only while it is over the
      // element. Leaving snaps back through the CSS transition.
      if (!reduced) {
        const mag = el?.closest<HTMLElement>('[data-magnetic]') ?? null
        if (mag !== magnet) {
          releaseMagnet()
          magnet = mag
        }
        if (mag) {
          const r = mag.getBoundingClientRect()
          const dx = (e.clientX - (r.left + r.width / 2)) / (r.width / 2)
          const dy = (e.clientY - (r.top + r.height / 2)) / (r.height / 2)
          mag.style.translate = `${(dx * 7).toFixed(1)}px ${(dy * 5).toFixed(1)}px`
        }
      }

      // Crosshair.
      if (!reduced && cursor) {
        target.x = e.clientX
        target.y = e.clientY
        if (!shown) {
          shown = true
          pos.x = target.x
          pos.y = target.y
          cursor.setAttribute('data-on', '')
        }
        const interactive = el?.closest(INTERACTIVE)
        const typing = el?.closest(TEXT_ENTRY)
        cursor.toggleAttribute('data-link', !!interactive && !typing)
        // Over a text field the crosshair would sit on top of the caret.
        cursor.toggleAttribute('data-hidden', !!typing)
        setLabel(interactive && !typing ? 'SELECT' : `X ${pad(e.clientX)}  Y ${pad(e.clientY)}`)
        if (!cursorRaf) cursorRaf = requestAnimationFrame(tick)
      }
    }

    const onDown = () => cursor?.setAttribute('data-down', '')
    const onUp = () => cursor?.removeAttribute('data-down')

    const onLeave = (e: MouseEvent) => {
      // relatedTarget is null when the pointer leaves the window entirely.
      if (e.relatedTarget) return
      lit?.removeAttribute('data-lit')
      lit = null
      releaseMagnet()
      shown = false
      cursor?.removeAttribute('data-on')
    }

    document.addEventListener('pointermove', onMove, { passive: true })
    document.addEventListener('pointerdown', onDown, { passive: true })
    document.addEventListener('pointerup', onUp, { passive: true })
    document.addEventListener('mouseout', onLeave)

    return () => {
      cancelAnimationFrame(cursorRaf)
      cancelAnimationFrame(progressRaf)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('resize', onScroll)
      document.removeEventListener('pointermove', onMove)
      document.removeEventListener('pointerdown', onDown)
      document.removeEventListener('pointerup', onUp)
      document.removeEventListener('mouseout', onLeave)
      lit?.removeAttribute('data-lit')
      releaseMagnet()
    }
  }, [])

  return (
    <>
      <div ref={progressRef} className="bp-progress" aria-hidden="true" />
      <div ref={cursorRef} className="bp-cursor" aria-hidden="true">
        <svg className="bp-cursor-ring" width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor">
          <circle cx="20" cy="20" r="11" strokeWidth="1" opacity="0.85" />
          <path d="M20 3v9M20 28v9M3 20h9M28 20h9" strokeWidth="1" strokeLinecap="round" />
          <circle cx="20" cy="20" r="1.4" fill="currentColor" stroke="none" />
        </svg>
        <span ref={labelRef} className="bp-cursor-label" />
      </div>
    </>
  )
}
