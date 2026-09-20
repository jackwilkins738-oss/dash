'use client'

import { useState } from 'react'
import { Check, Copy } from 'lucide-react'

const BASE = 'https://www.scalardigital.co.uk/contact'

// Keep the name readable in the link but safe to read back: letters, numbers,
// spaces and a few name punctuation marks, capped in length.
function clean(value: string) {
  return value.replace(/[^\p{L}\p{N} .'&-]/gu, '').replace(/\s+/g, ' ').trim().slice(0, 60)
}

async function copyText(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // Older browsers / blocked clipboard: fall back to a hidden textarea
    try {
      const el = document.createElement('textarea')
      el.value = text
      el.setAttribute('readonly', '')
      el.style.position = 'fixed'
      el.style.opacity = '0'
      document.body.appendChild(el)
      el.select()
      const ok = document.execCommand('copy')
      document.body.removeChild(el)
      return ok
    } catch {
      return false
    }
  }
}

export function ReferralLink() {
  const [name, setName] = useState('')
  const [copied, setCopied] = useState<'link' | 'message' | null>(null)
  const [failed, setFailed] = useState(false)

  const who = clean(name)
  const link = who ? `${BASE}?ref=${encodeURIComponent(who)}` : ''
  const message = who
    ? `Scalar Digital builds fast, hand-coded websites for trades. Use my link and you'll get 15% off your build: ${link}`
    : ''

  async function copy(kind: 'link' | 'message') {
    const ok = await copyText(kind === 'link' ? link : message)
    setFailed(!ok)
    setCopied(ok ? kind : null)
    if (ok) setTimeout(() => setCopied((c) => (c === kind ? null : c)), 2200)
  }

  return (
    <div className="rounded-2xl border border-blueprint/40 bg-card p-6 sm:p-8">
      <label htmlFor="referrer" className="mb-2 block font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
        Your name or business name
      </label>
      <input
        id="referrer"
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
        placeholder="e.g. Dave Thompson, or Thompson Roofing"
        maxLength={60}
        autoComplete="off"
        className="w-full rounded-lg border border-input bg-background px-4 py-3 text-sm text-foreground outline-none transition-colors placeholder:text-muted-foreground/70 focus:border-blueprint focus:ring-1 focus:ring-blueprint"
      />

      <div className="mt-6" aria-live="polite">
        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Your referral link</div>
        <div
          className={`mt-2 break-all rounded-lg border px-4 py-3 font-mono text-xs leading-relaxed ${
            link ? 'border-border bg-background text-foreground' : 'border-dashed border-border text-muted-foreground/60'
          }`}
        >
          {link || 'Type your name above and your link appears here.'}
        </div>
      </div>

      <div className="mt-5 flex flex-col gap-3 sm:flex-row">
        <button
          type="button"
          onClick={() => copy('link')}
          disabled={!link}
          className="btn-chamfer inline-flex items-center justify-center gap-2 bg-blueprint px-6 py-3 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background disabled:cursor-not-allowed disabled:opacity-40"
        >
          {copied === 'link' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          {copied === 'link' ? 'Copied' : 'Copy link'}
        </button>
        <button
          type="button"
          onClick={() => copy('message')}
          disabled={!link}
          className="btn-chamfer inline-flex items-center justify-center gap-2 border border-border px-6 py-3 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-foreground transition-colors hover:border-blueprint hover:text-blueprint disabled:cursor-not-allowed disabled:opacity-40"
        >
          {copied === 'message' ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          {copied === 'message' ? 'Copied' : 'Copy a ready-made message'}
        </button>
      </div>
      {failed && (
        <p className="mt-3 text-xs text-muted-foreground">
          Your browser blocked copying. Select the link above and copy it by hand.
        </p>
      )}
    </div>
  )
}
