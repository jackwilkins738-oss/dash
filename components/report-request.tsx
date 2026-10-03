'use client'

import { useState, type FormEvent } from 'react'
import { ArrowRight, Loader2 } from 'lucide-react'

// Under the free speed test: "send me the full report" - the owner gets it on Telegram straight away
// (app/api/website-check) and builds their preview, so the reply has something real to show.
const TRADES = ['Roofing', 'Loft conversions', 'Driveways & patios', 'Landscaping', 'Building & extensions', 'Other trade']
const field =
  'w-full rounded-lg border border-border bg-background px-4 py-3 text-base outline-none placeholder:text-muted-foreground/70 focus:border-blueprint'

export function ReportRequest({ website, score }: { website: string; score: number }) {
  const [form, setForm] = useState({ name: '', business: '', email: '', phone: '', trade: '', town: '', company: '' })
  const [state, setState] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle')
  const [error, setError] = useState('')
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })

  async function submit(e: FormEvent) {
    e.preventDefault()
    setState('sending')
    setError('')
    try {
      const res = await fetch('/api/website-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, website, score }),
      })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error || 'Could not send right now.')
      setState('sent')
    } catch (err) {
      setState('error')
      setError(err instanceof Error ? err.message : 'Could not send right now.')
    }
  }

  if (state === 'sent') {
    return (
      <div className="mx-auto mt-8 max-w-lg rounded-2xl border border-blueprint/40 bg-card p-7 text-center" role="status">
        <p className="font-display text-xl font-bold tracking-tight">Got it - it&apos;s on its way.</p>
        <p className="mt-3 text-pretty text-muted-foreground">
          You&apos;ll get the full report, with a preview of your site rebuilt to load fast, by email - usually the same day.
          Nothing to pay and no obligation.
        </p>
      </div>
    )
  }

  return (
    <form onSubmit={submit} className="mx-auto mt-8 max-w-lg rounded-2xl border border-blueprint/40 bg-card p-7">
      <p className="font-display text-xl font-bold tracking-tight">Want the full report - and your site rebuilt, free to look at?</p>
      <p className="mt-2 text-pretty text-sm leading-relaxed text-muted-foreground">
        What&apos;s slowing your site down, in plain English, plus a preview of your own homepage rebuilt to load in under
        a second. Sent by email, usually the same day. No obligation - and we won&apos;t add you to any mailing list.
      </p>
      <div className="mt-5 grid gap-3 sm:grid-cols-2">
        <input className={field} placeholder="Your name" value={form.name} onChange={set('name')} autoComplete="name" required maxLength={80} aria-label="Your name" />
        <input className={field} placeholder="Business name" value={form.business} onChange={set('business')} autoComplete="organization" required maxLength={120} aria-label="Business name" />
        <input className={field} type="email" placeholder="Email" value={form.email} onChange={set('email')} autoComplete="email" required maxLength={254} aria-label="Email" />
        <input className={field} type="tel" placeholder="Phone (optional)" value={form.phone} onChange={set('phone')} autoComplete="tel" maxLength={30} aria-label="Phone (optional)" />
        <select className={field} value={form.trade} onChange={set('trade')} aria-label="Your trade">
          <option value="">Your trade</option>
          {TRADES.map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
        <input className={field} placeholder="Town you work in" value={form.town} onChange={set('town')} maxLength={60} aria-label="Town you work in" />
      </div>
      {/* Honeypot: hidden from people, filled in by bots */}
      <input type="text" name="company" value={form.company} onChange={set('company')} tabIndex={-1} autoComplete="off" className="hidden" aria-hidden />
      <button
        type="submit"
        disabled={state === 'sending'}
        className="btn-chamfer group mt-5 inline-flex w-full items-center justify-center gap-2 bg-blueprint px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background disabled:opacity-70"
      >
        {state === 'sending' ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
        Send me the report
        {state === 'sending' ? null : <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />}
      </button>
      {state === 'error' && <p className="mt-3 text-center text-sm text-brass">{error}</p>}
      <p className="mt-3 text-center text-xs text-muted-foreground">
        Used only to send your report and reply to you - see the <a href="/privacy" className="underline underline-offset-4">privacy notice</a>.
      </p>
    </form>
  )
}
