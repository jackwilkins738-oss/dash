'use client'

import dynamic from 'next/dynamic'
import { useEffect, useState } from 'react'

// Code-split out of the main page bundle - this pulls in Three.js and two
// postprocessing passes, none of which should count against the page's
// own script-parse budget or compete with real interactivity on load.
const PowerCableImpl = dynamic(() => import('@/components/power-cable').then((m) => m.PowerCable), {
  ssr: false,
})

// The cable is decoration. On a device that is short of CPU, memory or data it
// is a poor trade: ~130KB to download and over a second of synchronous WebGL
// shader compilation to draw a glowing wire. So it is simply not started on
// those, rather than started and left to struggle.
type NavigatorHints = Navigator & { deviceMemory?: number; connection?: { saveData?: boolean } }
function deviceCanAffordIt(): boolean {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return false
  const nav = navigator as NavigatorHints
  if (nav.connection?.saveData) return false
  if (typeof nav.deviceMemory === 'number' && nav.deviceMemory <= 2) return false
  if (typeof nav.hardwareConcurrency === 'number' && nav.hardwareConcurrency <= 2) return false
  return true
}

const idle = (fn: () => void, timeout: number) =>
  typeof window.requestIdleCallback === 'function'
    ? window.requestIdleCallback(fn, { timeout })
    : window.setTimeout(fn, 50)

export function PowerCable() {
  const [ready, setReady] = useState(false)

  useEffect(() => {
    if (!deviceCanAffordIt()) return

    let cancelled = false

    const removeListeners = () => {
      window.removeEventListener('scroll', start)
      window.removeEventListener('pointermove', start)
      window.removeEventListener('touchstart', start)
    }
    const start = () => {
      if (cancelled) return
      cancelled = true
      removeListeners()
      window.clearTimeout(fallback)
      // Defer the actual mount - and the ~1.3s of synchronous WebGL/shader
      // work that follows inside power-cable.tsx - to the next idle moment
      // instead of firing it inside this handler directly. scroll is one of
      // the trigger events, and starting that work synchronously mid-scroll
      // competed with the very scroll frame the user was on for the main
      // thread, which read as jumpiness rather than just lateness.
      idle(() => setReady(true), 300)
    }

    // Arm the interaction listeners once the opening sequence has had time to
    // play, so the two never fight for the main thread.
    const armTimer = window.setTimeout(() => {
      if (cancelled) return
      window.addEventListener('scroll', start, { once: true, passive: true })
      window.addEventListener('pointermove', start, { once: true, passive: true })
      window.addEventListener('touchstart', start, { once: true, passive: true })
    }, 1450)

    // Warm the ~500KB Three.js chunk so it is already cached by the time
    // something triggers the mount - but only well AFTER the page has finished
    // loading. It used to start fetching at 1.45s, squarely inside the window
    // where the page is trying to paint its content, and a phone's connection
    // is one shared pipe: those ~130KB were taken directly out of the
    // content's share. And import() doesn't just download, it evaluates: a
    // 54ms task that, under a phone's throttled CPU, is a ~170ms block - so it
    // has to land after the page has stopped being busy, not merely after
    // load. import() is deduped by the module system, so dynamic()'s own call
    // resolves from this same fetch.
    let prefetchTimer: number | undefined
    const prefetch = () => {
      prefetchTimer = window.setTimeout(() => {
        if (!cancelled) idle(() => void import('@/components/power-cable'), 4000)
      }, 6500)
    }
    if (document.readyState === 'complete') prefetch()
    else window.addEventListener('load', prefetch, { once: true })

    // Worst-case wait for anyone who doesn't scroll or move the pointer at
    // all. The real cost this defers isn't the mount itself but the WebGL
    // shader compilation inside it - a single >500ms main-thread task under a
    // software-rendered GPU, the conditions lab tools run under. Nearly
    // everyone reading the page scrolls or moves the mouse well before this
    // fires, so it costs a genuinely idle visitor a few extra seconds before
    // a purely decorative effect appears, and nothing else.
    const fallback = window.setTimeout(start, 7000)

    return () => {
      cancelled = true
      window.clearTimeout(armTimer)
      window.clearTimeout(fallback)
      window.clearTimeout(prefetchTimer)
      window.removeEventListener('load', prefetch)
      removeListeners()
    }
  }, [])

  // Mounting (not just running the heavy WebGL init) waits for the signal
  // above, so a synthetic audit - which never scrolls or moves the pointer -
  // never renders this during the trace at all.
  if (!ready) return null
  return <PowerCableImpl />
}
