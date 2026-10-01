'use client'

import { useState } from 'react'

// "Not for us" on a preview page: one tap, no form. The dashboard marks them
// lost and the owner's panel stops every email and call to them
// (app/api/preview-optout). Kinder than ignoring three more emails, and it
// keeps the sending domains clean.
export function PreviewOptOut({ slug, firmName }: { slug: string; firmName: string }) {
  const [state, setState] = useState<'idle' | 'sending' | 'done'>('idle')

  async function optOut() {
    if (!window.confirm(`No more emails or calls to ${firmName} about this?`)) return
    setState('sending')
    try {
      await fetch('/api/preview-optout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug }),
      })
    } catch {
      // Shown as done either way: they've asked, and the owner reads replies too.
    }
    setState('done')
  }

  if (state === 'done') {
    return <p className="text-sm text-muted-foreground">Understood - you won&apos;t hear from me again about this. Thanks for looking.</p>
  }
  return (
    <button
      type="button"
      data-print="hide"
      onClick={optOut}
      disabled={state === 'sending'}
      className="text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground disabled:opacity-60"
    >
      Not for us - please don&apos;t contact {firmName} again
    </button>
  )
}
