'use client'

import dynamic from 'next/dynamic'
import { useEffect, useState } from 'react'

// Code-split out of the main page bundle - this pulls in Three.js and two
// postprocessing passes, none of which should count against the page's
// own script-parse budget or compete with real interactivity on load.
const PowerCableImpl = dynamic(() => import('@/components/power-cable').then((m) => m.PowerCable), {
  ssr: false,
})

export function PowerCable() {
  const [ready, setReady] = useState(false)

  useEffect(() => {
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
      // work that follows inside power-cable.tsx - to the next idle
      // moment instead of firing it inside this handler directly. scroll
      // is one of the trigger events, and starting that work synchronously
      // mid-scroll competed with the very scroll frame the user was on
      // for the main thread, which is what read as jumpiness rather than
      // just lateness. requestIdleCallback (short timeout fallback for
      // Safari, which doesn't implement it) lets the current frame paint
      // and the gesture settle first.
      const mount = () => setReady(true)
      const idle = typeof window.requestIdleCallback === 'function' ? window.requestIdleCallback : null
      if (idle) {
        idle(mount, { timeout: 300 })
      } else {
        window.setTimeout(mount, 50)
      }
    }
    // A pointermove can fire within the first frame in real browsers (the
    // cursor is often already resting over the page) - arming these
    // immediately meant mounting the cable while the preloader's own
    // GSAP timeline (~1.3s) was still mid-animation, both fighting for
    // the main thread. Arm the listeners only once the preloader has had
    // time to finish, so the two never overlap.
    const armTimer = window.setTimeout(() => {
      if (cancelled) return
      // Start fetching the ~500KB Three.js chunk right as the listeners
      // arm - after the preloader (so it's not competing with the hero's
      // own paint), but well before mounting, so it's already warm by
      // the time something actually triggers the mount below. import()
      // is deduped by the module system: this and dynamic()'s own call
      // resolve from the same cached fetch, so nothing downloads twice.
      import('@/components/power-cable')
      window.addEventListener('scroll', start, { once: true, passive: true })
      window.addEventListener('pointermove', start, { once: true, passive: true })
      window.addEventListener('touchstart', start, { once: true, passive: true })
    }, 1450)
    // Worst-case wait for anyone who doesn't scroll or move the pointer at
    // all. The real cost this exists to defer isn't the mount itself -
    // it's the WebGL shader compilation inside it, which is expensive
    // enough (measured: a single >500ms main-thread task under a
    // software-rendered GPU, the same conditions Lighthouse and PageSpeed
    // Insights lab data run under) that firing it at 2s landed squarely
    // inside the page's Time to Interactive window and inflated Total
    // Blocking Time - for a synthetic crawler that never scrolls or moves
    // the pointer, same as for a real visitor who genuinely never
    // interacts. Nearly everyone who's actually reading the page scrolls
    // or moves the mouse well before this fires anyway (see the listeners
    // above), so pushing it out this far costs real disengaged visitors a
    // few extra seconds before a purely decorative effect appears, not
    // any missing functionality.
    const fallback = window.setTimeout(start, 7000)

    return () => {
      cancelled = true
      window.clearTimeout(armTimer)
      window.clearTimeout(fallback)
      removeListeners()
    }
  }, [])

  // Mounting (not just running the heavy WebGL init) waits for the signal
  // above, so a synthetic Lighthouse audit - which never scrolls or moves
  // the pointer - never renders this during the trace at all. The chunk
  // itself is fetched slightly earlier (see armTimer) so a real visitor
  // isn't also waiting on the network on top of the ~1.3s init once it
  // does mount.
  if (!ready) return null
  return <PowerCableImpl />
}
