import Link from 'next/link'
import { CalendarClock } from 'lucide-react'
import { Reveal } from '@/components/reveal'
import { SITE } from '@/lib/site'

// The option for anyone who'd rather talk than type. Deliberately second to
// the enquiry form everywhere - most trades would sooner send two lines.

/** A single line under a form: "Prefer to talk it through? Book a 15-minute call." */
export function BookCallLine({ className = '' }: { className?: string }) {
  return (
    <p className={`text-sm text-muted-foreground ${className}`}>
      Prefer to talk it through?{' '}
      <a href={SITE.booking} target="_blank" rel="noopener" className="font-semibold text-blueprint underline-offset-4 hover:underline">
        Book a 15-minute call
      </a>
      {' '}at a time that suits you.
    </p>
  )
}

/** A band for the preview pages: message, or book a call. */
export function BookCallBand({ contactHref, firmName }: { contactHref: string; firmName: string }) {
  return (
    <section className="border-t border-border py-16 sm:py-20">
      <div className="mx-auto max-w-4xl px-5 sm:px-8">
        <Reveal className="rounded-2xl border border-blueprint/40 bg-card p-7 sm:p-10">
          <h2 className="font-display text-balance text-2xl font-bold tracking-tight sm:text-3xl">
            Like what you see for {firmName}?
          </h2>
          <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
            Send a quick message, or pick a time for a 15-minute call - no obligation, and nothing to prepare.
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Link
              href={contactHref}
              className="btn-chamfer inline-flex items-center justify-center gap-2 bg-blueprint px-6 py-3 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background"
            >
              Send a message
            </Link>
            <a
              href={SITE.booking}
              target="_blank"
              rel="noopener"
              className="btn-chamfer inline-flex items-center justify-center gap-2 border border-border px-6 py-3 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-foreground transition-colors hover:border-blueprint hover:text-blueprint"
            >
              <CalendarClock className="h-4 w-4" />
              Book a 15-minute call
            </a>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
