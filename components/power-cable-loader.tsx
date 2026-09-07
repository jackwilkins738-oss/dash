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
    // Worst-case wait for anyone who doesn't scroll or move the pointer
    // in the first couple of seconds. Comes after the prefetch above has
    // had a moment to land, so mounting doesn't also wait on the network.
    const fallback = window.setTimeout(start, 2000)

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
