import { AlertTriangle, Check, ShieldCheck, X } from 'lucide-react'
import { Reveal } from '@/components/reveal'

// Illustrative, not a real client deployment - see the site mockup below
// and its own copy. It exists to show what a dashboard behind a build can
// do, not to claim any specific example site runs one.

export function CaseStudy() {
  return (
    <section className="border-t border-border py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal className="max-w-2xl">
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">
            Site &amp; system, paired
          </span>
          <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            The site brings the lead in. This is what runs the job after.
          </h2>
          <p className="mt-5 max-w-2xl text-pretty leading-relaxed text-muted-foreground">
            A worked example, not a real client&apos;s dashboard — a walkthrough of what I can build behind any
            trade site: a private system that turns an enquiry into a tracked job, with nothing to log into three
            different apps for.
          </p>
        </Reveal>

        <Reveal className="mt-14 overflow-hidden rounded-2xl border border-border">
          <div className="flex items-center gap-2 border-b border-border bg-card/60 px-4 py-3">
            <span className="h-2.5 w-2.5 rounded-full bg-destructive/60" />
            <span className="h-2.5 w-2.5 rounded-full bg-brass/60" />
            <span className="h-2.5 w-2.5 rounded-full bg-blueprint/60" />
            <span className="ml-3 truncate font-mono text-[11px] text-muted-foreground">
              dashboard.example-loftco.co.uk
            </span>
          </div>

          <div className="grid gap-px bg-border sm:grid-cols-2 lg:grid-cols-3">
            {/* Leads */}
            <div className="bg-card p-6">
              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                New leads
              </span>
              <ul className="mt-4 space-y-3">
                {[
                  ['J. Fenwick', 'Loft conversion enquiry', '4m ago'],
                  ['R. Okafor', 'Site visit requested', '31m ago'],
                  ['S. Meadows', 'Price range sent', 'Yesterday'],
                ].map(([name, note, when]) => (
                  <li key={name} className="rounded-lg border border-border bg-background/60 p-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium">{name}</span>
                      <span className="font-mono text-[10px] text-muted-foreground">{when}</span>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">{note}</p>
                  </li>
                ))}
              </ul>
            </div>

            {/* Quote approval */}
            <div className="bg-card p-6">
              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                Customer portal
              </span>
              <div className="mt-4 rounded-lg border border-border bg-background/60 p-4">
                <p className="text-sm">Quote #402 — dormer conversion</p>
                <p className="mt-1 text-xs text-muted-foreground">Sent to customer for approval</p>
                <div className="mt-4 flex gap-2">
                  <span className="inline-flex items-center gap-1.5 rounded-md bg-blueprint/15 px-3 py-1.5 font-mono text-[11px] font-semibold text-blueprint">
                    <Check className="h-3 w-3" strokeWidth={2.5} />
                    Approved
                  </span>
                  <span className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 font-mono text-[11px] text-muted-foreground/60">
                    <X className="h-3 w-3" strokeWidth={2.5} />
                    Decline
                  </span>
                </div>
              </div>
              <div className="mt-3 flex items-start gap-2 rounded-lg border border-brass/30 bg-brass/10 p-3">
                <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brass" strokeWidth={2.5} />
                <p className="text-xs text-foreground/90">
                  Site visit clashes with Job #114 — Tue 09:00&ndash;11:00
                </p>
              </div>
            </div>

            {/* Audit log & access */}
            <div className="bg-card p-6 sm:col-span-2 lg:col-span-1">
              <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-muted-foreground">
                Audit log
              </span>
              <ul className="mt-4 space-y-2.5 font-mono text-[11px] text-muted-foreground">
                <li>14:32 — Sam approved quote #402</li>
                <li>11:08 — Jack edited price on #402</li>
                <li>09:10 — Sam viewed Leads</li>
              </ul>
              <div className="mt-5 flex items-center gap-2 border-t border-border pt-4">
                <ShieldCheck className="h-4 w-4 shrink-0 text-blueprint" strokeWidth={2.5} />
                <p className="text-xs text-muted-foreground">
                  <span className="font-medium text-foreground">Owner</span> sees everything.{' '}
                  <span className="font-medium text-foreground">Member</span> can&apos;t touch Settings.
                </p>
              </div>
            </div>
          </div>
        </Reveal>

        <p className="mt-8 max-w-2xl text-sm leading-relaxed text-muted-foreground">
          Leads, quotes a customer can approve themselves, a calendar that flags double-bookings before they
          happen, who-did-what on every job — built the same way as the site: hand-coded, fixed price, yours
          outright once it&apos;s done.
        </p>
      </div>
    </section>
  )
}
