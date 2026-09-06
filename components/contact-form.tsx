'use client'

import { useState, type FormEvent } from 'react'
import { Check, Loader2 } from 'lucide-react'

const TRADES = [
  'Resin Driveways',
  'Landscaping',
  'Loft Conversion',
  'House Extension',
  'Roofing',
  'Renovation',
  'Other',
]

const BUDGETS = ['£2,500 – £4,000', '£4,000 – £6,000', '£6,000 – £8,000', 'Not sure yet']

const fieldClass =
  'w-full rounded-lg border border-input bg-background px-4 py-3 text-sm text-foreground placeholder:text-muted-foreground/70 outline-none transition-colors focus:border-blueprint focus:ring-1 focus:ring-blueprint'

const labelClass = 'mb-2 block font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground'

export function ContactForm() {
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle')
  const [error, setError] = useState('')

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setStatus('loading')
    setError('')

    const form = e.currentTarget
    const data = Object.fromEntries(new FormData(form).entries())

    try {
      const res = await fetch('/api/contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      })
      const json = await res.json().catch(() => ({}))
      if (!res.ok) {
        setError(json.error || 'Something went wrong. Please try again.')
        setStatus('error')
        return
      }
      setStatus('success')
      form.reset()
    } catch {
      setError('Network error. Please try again or message on WhatsApp.')
      setStatus('error')
    }
  }

  if (status === 'success') {
    return (
      <div className="flex flex-col items-start rounded-2xl border border-blueprint/40 bg-card p-8 sm:p-10">
        <div className="flex h-12 w-12 items-center justify-center rounded-full border border-blueprint/50 text-blueprint">
          <Check className="h-6 w-6" strokeWidth={2} />
        </div>
        <h3 className="mt-6 font-display text-2xl font-bold">Got it — message sent.</h3>
        <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
          Thanks for reaching out. I read every enquiry myself and I&apos;ll come back to you within 2 hours during
          working hours with a plan and a fixed price. If it&apos;s urgent, drop me a WhatsApp.
        </p>
        <button
          type="button"
          onClick={() => setStatus('idle')}
          className="mt-6 font-mono text-xs uppercase tracking-[0.15em] text-blueprint hover:underline"
        >
          Send another
        </button>
      </div>
    )
  }

  return (
    <form
      onSubmit={onSubmit}
      className="rounded-2xl border border-border bg-card/40 p-6 sm:p-8"
      noValidate
    >
      {/* Honeypot */}
      <input
        type="text"
        name="company"
        tabIndex={-1}
        autoComplete="off"
        className="sr-only"
        aria-hidden="true"
      />

      <div className="grid gap-5 sm:grid-cols-2">
        <div>
          <label htmlFor="name" className={labelClass}>
            Your name
          </label>
          <input id="name" name="name" required placeholder="Dave Thompson" className={fieldClass} />
        </div>
        <div>
          <label htmlFor="phone" className={labelClass}>
            Phone
          </label>
          <input id="phone" name="phone" type="tel" placeholder="07000 000000" className={fieldClass} />
        </div>
      </div>

      <div className="mt-5">
        <label htmlFor="email" className={labelClass}>
          Email
        </label>
        <input id="email" name="email" type="email" required placeholder="you@yourfirm.co.uk" className={fieldClass} />
      </div>

      <div className="mt-5 grid gap-5 sm:grid-cols-2">
        <div>
          <label htmlFor="trade" className={labelClass}>
            Your trade
          </label>
          <select id="trade" name="trade" defaultValue="" className={fieldClass}>
            <option value="" disabled>
              Select a trade
            </option>
            {TRADES.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label htmlFor="budget" className={labelClass}>
            Rough budget
          </label>
          <select id="budget" name="budget" defaultValue="" className={fieldClass}>
            <option value="" disabled>
              Select a range
            </option>
            {BUDGETS.map((b) => (
              <option key={b} value={b}>
                {b}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="mt-5">
        <label htmlFor="message" className={labelClass}>
          About the job
        </label>
        <textarea
          id="message"
          name="message"
          required
          rows={5}
          placeholder="Tell me about your firm, the jobs you want more of, and anything you like or hate about your current site."
          className={`${fieldClass} resize-none`}
        />
      </div>

      {status === 'error' && (
        <p role="alert" className="mt-4 text-sm text-destructive">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={status === 'loading'}
        className="btn-chamfer group mt-6 inline-flex w-full items-center justify-center gap-2 bg-blueprint px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background disabled:cursor-not-allowed disabled:opacity-70"
      >
        {status === 'loading' ? (
          <>
            <Loader2 className="h-4 w-4 animate-spin" />
            Sending
          </>
        ) : (
          <>
            Send enquiry
            <span className="transition-transform group-hover:translate-x-1">&rarr;</span>
          </>
        )}
      </button>
      <p className="mt-4 text-center font-mono text-[11px] uppercase tracking-[0.15em] text-muted-foreground">
        I reply within 2 hours · no sales call
      </p>
    </form>
  )
}
