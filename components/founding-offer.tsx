import Link from 'next/link'
import { Check } from 'lucide-react'
import { FOUNDING, PRICES, foundingLeft } from '@/lib/site'

// The first builds pay for proof with extras, not a discount: cutting the price would undo the
// positioning. The limit is real - the owner's own number, set before any client existed - and the
// places left are the real count from lib/site.ts, stated plainly: no countdown, no timer. Gone
// once none are left.
export function FoundingOffer({ href }: { href: string }) {
  const left = foundingLeft()
  if (left === 0) return null
  return (
    <div
      data-spotlight
      className="relative overflow-hidden rounded-2xl border border-brass/35 bg-card/60 p-7 sm:p-9"
    >
      <div
        className="pointer-events-none absolute inset-0 opacity-60"
        style={{ background: 'radial-gradient(70% 90% at 0% 0%, oklch(0.78 0.1 80 / 0.12), transparent 60%)' }}
        aria-hidden="true"
      />
      <div className="relative grid gap-8 lg:grid-cols-[1.1fr_1fr] lg:gap-12">
        <div>
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-brass">
            Founding clients &middot; The Scalar build &middot; {FOUNDING.places} places &middot; {left} left
          </span>
          <h3 className="mt-4 font-display text-balance text-2xl font-bold tracking-tight sm:text-3xl">
            Same price, same standard. More behind it.
          </h3>
          <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
            The first {FOUNDING.places} Scalar builds get more than anyone after them, in return for helping prove the
            work: a short case study with your real before-and-after numbers, a 60-second video and a Google
            review.
          </p>
          <Link
            href={href}
            className="btn-chamfer group mt-7 inline-flex items-center justify-center gap-2 border border-brass/50 px-6 py-3 font-mono text-xs font-semibold uppercase tracking-[0.15em] text-brass transition-colors hover:bg-brass hover:text-background"
          >
            Ask for a founding place
            <span className="transition-transform group-hover:translate-x-1">&rarr;</span>
          </Link>
        </div>
        <ul className="space-y-4 self-center">
          {[
            ['Dashboard hosting free for 24 months', `Twice the usual 12, before the optional £${PRICES.dashboardMonthly} a month.`],
            [
              'A speed guarantee',
              '90+ on Google’s mobile speed test at launch, checked together on the live site, or the balance isn’t due.',
            ],
            ['First place in the build queue', 'Scheduled ahead of standard builds booked in the same month.'],
          ].map(([title, body]) => (
            <li key={title} className="flex items-start gap-3">
              <Check className="mt-1 h-4 w-4 shrink-0 text-brass" strokeWidth={2.5} />
              <span>
                <span className="block text-sm font-semibold text-foreground">{title}</span>
                <span className="mt-0.5 block text-sm leading-relaxed text-muted-foreground">{body}</span>
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
