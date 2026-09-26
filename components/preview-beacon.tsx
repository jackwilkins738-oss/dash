'use client'

import { useEffect } from 'react'

// Tells the owner a prospect has opened their preview page (see
// app/api/preview-view/route.ts). Once per browser session, so a reload or
// a second tab doesn't ping the phone twice. It runs in the browser after
// the page has loaded, which also means link scanners that fetch the page
// without running it (most email security scanners) don't trigger it.
export function PreviewBeacon({ slug }: { slug: string }) {
  useEffect(() => {
    const key = `scalar-pv-${slug}`
    try {
      if (sessionStorage.getItem(key)) return
      sessionStorage.setItem(key, '1')
    } catch {
      // Storage blocked (private mode): still send - an occasional
      // duplicate alert beats a missed one.
    }
    const src = new URLSearchParams(window.location.search).get('src') ?? ''
    fetch('/api/preview-view', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slug, src }),
      keepalive: true,
    }).catch(() => {})
  }, [slug])

  return null
}
