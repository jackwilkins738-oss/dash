import Link from 'next/link'
import { CalendarClock } from 'lucide-react'
import { Reveal } from '@/components/reveal'
import { SITE } from '@/lib/site'

// For anyone who'd rather talk than type: a 15-minute call, booked straight
// from the page. The calendar is Cal.com's own, embedded - it shows the real
// free slots, and loads only when it scrolls into view so it never slows the
// page down.

// Cal.com's own embed script frames app.cal.com with ?embed=true - the same URL, without the script.
const EMBED = `${SITE.booking.replace('https://cal.com/', 'https://app.cal.com/')}?embed=true&layout=month_view&theme=dark`

/** The live calendar: pick a day, pick a slot, done. */
export function BookingCalendar({ className = '' }: { className?: string }) {
  return (
    <div className={`overflow-hidden rounded-2xl border border-border bg-card ${className}`}>
      <iframe
        src={EMBED}
        title="Book a 15-minute call with Scalar Digital"
        loading="lazy"
        className="block h-[720px] w-full sm:h-[640px]"
        referrerPolicy="strict-origin-when-cross-origin"
      />
      <p className="border-t border-border px-4 py-3 text-center text-xs text-muted-foreground">
        Calendar not loading?{' '}
        <a href={SITE.booking} target="_blank" rel="noopener" className="text-blueprint underline underline-offset-4">
          Open it in a new tab
        </a>
        .
      </p>
    </div>
  )
}

/** A clear button that jumps to the calendar on the same page. */
export function BookCallButton({ href = '#book', label = 'Book a 15-minute call' }: { href?: string; label?: string }) {
  return (
    <a
      href={href}
      className="btn-chamfer inline-flex items-center justify-center gap-2 border border-blueprint/60 bg-blueprint/10 px-6 py-3 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-foreground transition-colors hover:bg-blueprint hover:text-primary-foreground"
    >
      <CalendarClock className="h-4 w-4" />
      {label}
    </a>
  )
}

/** The contact page's booking section: heading, one line, the calendar. */
export function BookCallSection() {
  return (
    <section id="book" data-print="hide" className="scroll-mt-24 border-t border-border py-16 sm:py-20">
      <div className="mx-auto max-w-4xl px-5 sm:px-8">
        <Reveal>
          <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Rather talk?</span>
          <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl">
            Book a 15-minute call.
          </h2>
          <p className="mt-4 max-w-2xl text-pretty leading-relaxed text-muted-foreground">
            Pick a day and time that suits you. I&apos;ll ring you on the number you give - no slides, no pressure, just
            what you need and what it would cost.
          </p>
        </Reveal>
        <BookingCalendar className="mt-8" />
      </div>
    </section>
  )
}

/** The preview pages' band: message, or book a call on the calendar right here. */
export function BookCallBand({ contactHref, firmName }: { contactHref: string; firmName: string }) {
  return (
    <section id="book" data-print="hide" className="scroll-mt-24 border-t border-border py-16 sm:py-20">
      <div className="mx-auto max-w-4xl px-5 sm:px-8">
        <Reveal className="rounded-2xl border border-blueprint/40 bg-card p-7 sm:p-10">
          <h2 className="font-display text-balance text-2xl font-bold tracking-tight sm:text-3xl">
            Like what you see for {firmName}?
          </h2>
          <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
            Pick a time below for a 15-minute call, or send a quick message - no obligation, nothing to prepare.
          </p>
          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <Link
              href={contactHref}
              className="btn-chamfer inline-flex items-center justify-center gap-2 bg-blueprint px-6 py-3 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background"
            >
              Send a message
            </Link>
          </div>
        </Reveal>
        <BookingCalendar className="mt-6" />
      </div>
    </section>
  )
}
