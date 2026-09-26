import Link from 'next/link'
import { ArrowRight, FileText, LayoutDashboard, UserCheck } from 'lucide-react'
import { Reveal } from '@/components/reveal'

const POINTS = [
  {
    Icon: LayoutDashboard,
    title: 'Never lose an enquiry',
    body: 'Your site’s contact form feeds straight into the dash. Every lead is in one list, and any nobody has followed up is flagged.',
  },
  {
    Icon: FileText,
    title: 'Quote and invoice properly',
    body: 'Send branded quotes your customer accepts online with no login, then invoice and see who owes what at a glance.',
  },
  {
    Icon: UserCheck,
    title: 'Customers stay in the loop',
    body: 'A private portal for each customer. Scope changes are approved there and logged, so nothing is “agreed on the phone”.',
  },
]

export function DashPitch() {
  return (
    <section className="border-t border-border py-24 sm:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal className="max-w-2xl">
          <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">
            Included in The Scalar build
          </span>
          <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            The site brings the lead in. Your own dashboard runs the job after.
          </h2>
          <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
            Enquiries, quotes, jobs, invoices and a customer portal in one private place, in your business name and
            colours, instead of five apps and a WhatsApp thread.
          </p>
        </Reveal>

        <Reveal stagger className="mt-12 grid gap-5 md:grid-cols-3">
          {POINTS.map(({ Icon, title, body }) => (
            <div key={title} data-spotlight className="rounded-2xl border border-border bg-card/40 p-7 transition-colors hover:border-blueprint/40">
              <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-blueprint/40 text-blueprint">
                <Icon className="h-5 w-5" strokeWidth={1.75} />
              </span>
              <h3 className="mt-5 font-display text-lg font-semibold">{title}</h3>
              <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{body}</p>
            </div>
          ))}
        </Reveal>

        <Reveal className="mt-10 flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
          <p className="max-w-xl text-sm leading-relaxed text-muted-foreground">
            Hosted by me, free for your first 12 months, then a small optional monthly dashboard fee agreed up front. Your website
            is always yours, with or without the dashboard.
          </p>
          <Link
            href="/#dash"
            className="group inline-flex flex-none items-center gap-2 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-blueprint transition-colors hover:text-brass"
          >
            See the dashboard working
            <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
          </Link>
        </Reveal>
      </div>
    </section>
  )
}
