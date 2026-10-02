'use client'

import { useEffect } from 'react'

// What a prospect did on their preview page, for the owner's call list.
//
// The VIEW (app/api/preview-view: count + Telegram "they're looking") is only
// sent once someone is really there: the page has been on screen for 4
// seconds, or they've scrolled or touched it. Email security scanners that
// open links in a real browser to check them - several times, within a
// minute of the email arriving - do neither, so they stop showing up as
// "viewed". Automated browsers (navigator.webdriver) are skipped outright.
// Once per browser session, so a reload or second tab doesn't ping twice.
//
// The ENGAGEMENT (app/api/preview-engagement) goes when the page is put away:
// seconds actually on screen, how far down they scrolled, and which sections
// they reached - so "3 visits, 2m40s, got to the price" can be told apart
// from a two-second glance.
const SECTIONS = ['loading', 'rebuilt', 'race', 'findings', 'pricing', 'reply']
const ENGAGED_AFTER_MS = 4000

export function PreviewBeacon({ slug }: { slug: string }) {
  useEffect(() => {
    if (navigator.webdriver) return
    const src = new URLSearchParams(window.location.search).get('src') ?? ''
    if (src === 'dashboard') return // the owner checking it isn't the prospect looking

    const viewKey = `scalar-pv-${slug}`
    let viewSent = false
    try {
      viewSent = !!sessionStorage.getItem(viewKey)
    } catch {
      // Storage blocked (private mode): send anyway - an occasional duplicate beats a miss.
    }
    const sendView = () => {
      if (viewSent) return
      viewSent = true
      try {
        sessionStorage.setItem(viewKey, '1')
      } catch {}
      fetch('/api/preview-view', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug, src }),
        keepalive: true,
      }).catch(() => {})
    }

    let visibleMs = 0
    let since = document.visibilityState === 'visible' ? performance.now() : 0
    let maxScroll = 0
    const reached = new Set<string>()
    const tick = () => {
      if (since) {
        const now = performance.now()
        visibleMs += now - since
        since = now
      }
    }
    const engagedTimer = window.setTimeout(sendView, ENGAGED_AFTER_MS)
    const onScroll = () => {
      const doc = document.documentElement
      const pct = Math.round(((window.scrollY + window.innerHeight) / Math.max(doc.scrollHeight, 1)) * 100)
      maxScroll = Math.max(maxScroll, Math.min(100, pct))
      if (window.scrollY > 40) sendView()
    }
    const onTouch = () => sendView()

    const observer = new IntersectionObserver(
      (entries) => entries.forEach((e) => e.isIntersecting && reached.add(e.target.id)),
      { threshold: 0.35 },
    )
    SECTIONS.forEach((id) => {
      const el = document.getElementById(id)
      if (el) observer.observe(el)
    })

    let flushed = 0
    const flush = () => {
      tick()
      const seconds = Math.round(visibleMs / 1000) - flushed
      if (!viewSent || (seconds <= 0 && reached.size === 0)) return
      flushed += Math.max(0, seconds)
      const body = JSON.stringify({ slug, src, seconds: Math.max(0, seconds), scroll: maxScroll, reached: [...reached] })
      if (!navigator.sendBeacon?.('/api/preview-engagement', body)) {
        fetch('/api/preview-engagement', { method: 'POST', body, keepalive: true }).catch(() => {})
      }
    }
    const onVisibility = () => {
      if (document.visibilityState === 'hidden') {
        flush()
        since = 0
      } else {
        since = performance.now()
      }
    }

    window.addEventListener('scroll', onScroll, { passive: true })
    window.addEventListener('pointerdown', onTouch, { passive: true })
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('pagehide', flush)
    return () => {
      window.clearTimeout(engagedTimer)
      window.removeEventListener('scroll', onScroll)
      window.removeEventListener('pointerdown', onTouch)
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('pagehide', flush)
      observer.disconnect()
    }
  }, [slug])

  return null
}
