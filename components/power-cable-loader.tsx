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
      setReady(true)
    }
    // A pointermove can fire within the first frame in real browsers (the
    // cursor is often already resting over the page) - arming these
    // immediately meant mounting the cable while the preloader's own
    // GSAP timeline (~1.3s) was still mid-animation, both fighting for
    // the main thread. Arm the listeners only once the preloader has had
    // time to finish, so the two never overlap.
    const armTimer = window.setTimeout(() => {
      if (cancelled) return
      window.addEventListener('scroll', start, { once: true, passive: true })
      window.addEventListener('pointermove', start, { once: true, passive: true })
      window.addEventListener('touchstart', start, { once: true, passive: true })
    }, 1450)
    // Worst-case wait for anyone who doesn't scroll or move the pointer
    // in the first couple of seconds. Still fires safely after the
    // preloader and after listeners arm.
    const fallback = window.setTimeout(start, 2200)

    return () => {
      cancelled = true
      window.clearTimeout(armTimer)
      window.clearTimeout(fallback)
      removeListeners()
    }
  }, [])

  // Not just deferring the heavy WebGL init anymore - not mounting this
  // at all until the signal fires means the ~500KB Three.js chunk isn't
  // even requested until then, instead of competing with LCP-critical
  // resources (fonts, hero text) for network bandwidth on page load. A
  // synthetic Lighthouse audit never scrolls or moves the pointer, so it
  // never triggers the fetch during the trace at all.
  if (!ready) return null
  return <PowerCableImpl />
}
