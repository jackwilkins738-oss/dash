'use client'

import { useState } from 'react'
import { Phone, MessageCircle } from 'lucide-react'
import { SITE } from '@/lib/site'

// One tap instead of an email: tradespeople look at their preview - often
// several times - but rarely write back. Each button tells the owner at once
// (app/api/preview-choice -> Telegram) and records the answer in the
// dashboard, so the call list knows who wants a ring.
type Choice = 'call' | 'whatsapp' | 'not_now'

// us: a US preview - "call" not "ring", and no WhatsApp (the number is a UK one).
export function QuickReply({ slug, firmName, us = false }: { slug: string; firmName: string; us?: boolean }) {
  const [open, setOpen] = useState(false)
  const [phone, setPhone] = useState('')
  const [done, setDone] = useState<Choice | null>(null)
  const [busy, setBusy] = useState(false)

  const send = async (choice: Choice) => {
    setBusy(true)
    try {
      await fetch('/api/preview-choice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ slug, choice, phone: choice === 'call' ? phone : '' }),
        keepalive: true,
      })
    } catch {
      // Shown as sent either way: WhatsApp still opens, and a lost "maybe later" costs nothing.
    }
    setBusy(false)
    setDone(choice)
  }

  const whatsapp = `${SITE.whatsapp}?text=${encodeURIComponent(`Hi, it's ${firmName} - I've seen the website preview you made for us.`)}`

  if (done) {
    return (
      <div className="rounded-2xl border border-blueprint/40 bg-card p-6 text-center sm:p-8" role="status">
        <p className="font-display text-2xl font-bold tracking-tight">
          {done === 'call' ? (us ? "Thanks - I'll call you shortly." : "Thanks - I'll give you a ring shortly.") : done === 'whatsapp' ? 'Thanks - speak on WhatsApp.' : 'No problem at all.'}
        </p>
        <p className="mt-3 text-pretty text-muted-foreground">
          {done === 'call'
            ? 'If now turns out to be a bad time, just say and I will try later.'
            : done === 'whatsapp'
              ? "If WhatsApp didn't open, message me on it any time."
              : "I won't chase you. This preview stays here if you want another look."}
        </p>
      </div>
    )
  }

  return (
    <div className="rounded-2xl border border-blueprint/40 bg-card p-6 sm:p-8">
      <p className="font-display text-balance text-2xl font-bold tracking-tight sm:text-3xl">Like what you see? One tap is enough.</p>
      <p className="mt-3 text-pretty text-muted-foreground">No forms to fill in. Pick one and I&apos;ll take it from there.</p>
      <div className={`mt-6 grid gap-3 ${us ? '' : 'sm:grid-cols-2'}`}>
        <button
          type="button"
          onClick={() => setOpen(true)}
          disabled={busy}
          aria-expanded={open}
          className="inline-flex items-center justify-center gap-2 rounded-xl bg-blueprint px-5 py-4 text-base font-semibold text-white transition-colors hover:bg-brass disabled:opacity-60"
        >
          <Phone className="h-5 w-5" aria-hidden />
          {us ? 'Yes, call me' : 'Yes, give me a ring'}
        </button>
        {!us && (
        <a
          href={whatsapp}
          target="_blank"
          rel="noopener"
          onClick={() => void send('whatsapp')}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-border px-5 py-4 text-base font-semibold transition-colors hover:border-blueprint"
        >
          <MessageCircle className="h-5 w-5" aria-hidden />
          WhatsApp me
        </a>
        )}
      </div>
      {open && (
        <form
          className="mt-4 flex flex-col gap-3 sm:flex-row"
          onSubmit={(e) => {
            e.preventDefault()
            void send('call')
          }}
        >
          <label className="sr-only" htmlFor="quick-reply-phone">
            {us ? 'Best number to call (optional)' : 'Best number to ring (optional)'}
          </label>
          <input
            id="quick-reply-phone"
            type="tel"
            inputMode="tel"
            autoComplete="tel"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="Best number (optional - or I'll use the one on your website)"
            className="w-full rounded-xl border border-border bg-background px-4 py-3 text-base outline-none focus:border-blueprint"
            maxLength={20}
          />
          <button
            type="submit"
            disabled={busy}
            className="shrink-0 rounded-xl bg-blueprint px-6 py-3 font-semibold text-white transition-colors hover:bg-brass disabled:opacity-60"
          >
            {busy ? 'Sending...' : us ? 'Call me' : 'Ring me'}
          </button>
        </form>
      )}
      <button
        type="button"
        onClick={() => void send('not_now')}
        disabled={busy}
        className="mt-5 text-sm text-muted-foreground underline underline-offset-4 hover:text-foreground"
      >
        Maybe later - don&apos;t chase me
      </button>
    </div>
  )
}
