'use client'

import { useState, type ReactNode } from 'react'

// A package card on a prospect's preview: their quote opens straight away (app/api/preview-start),
// to accept, sign and pay the deposit. If it can't - prices not published yet, dashboard down - it
// goes to the contact form exactly as before, so nobody keen is ever left stuck.
export function StartQuote({
  slug,
  pkg,
  businessName,
  className,
  children,
}: {
  slug: string
  pkg: 'build' | 'landing'
  businessName: string
  className: string
  children: ReactNode
}) {
  const [busy, setBusy] = useState(false)
  const fallback = `/contact?firm=${encodeURIComponent(businessName)}&package=${pkg}`

  async function open() {
    if (busy) return
    setBusy(true)
    let url: string | null = null
    try {
      const res = await fetch('/api/preview-start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug, package: pkg }),
      })
      url = ((await res.json()) as { url?: string | null }).url ?? null
    } catch {
      url = null
    }
    window.location.href = url && /^https:\/\//.test(url) ? url : fallback
  }

  return (
    <a
      href={fallback}
      onClick={(e) => {
        e.preventDefault()
        void open()
      }}
      aria-busy={busy}
      className={className}
    >
      {children}
      {busy && <span className="mt-2 block text-sm text-muted-foreground">Opening your quote...</span>}
    </a>
  )
}
