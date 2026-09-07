import type { Metadata } from 'next'
import Link from 'next/link'
import { PageHeader } from '@/components/page-header'
import { CtaBand } from '@/components/cta-band'
import { Reveal } from '@/components/reveal'

export const metadata: Metadata = {
  title: 'Process — Scalar Digital',
  description:
    'How a build actually runs, start to finish: fixed price agreed up front, hand-coded, no surprises, no retainer once it ships.',
  alternates: { canonical: '/process' },
}

const STEPS = [
  {
    n: '01',
    title: 'Enquiry & fit check',
    body: 'You tell me about your trade and the jobs you want more of. I read every enquiry myself — if it’s not a good fit, I’ll say so straight away instead of stringing you along.',
  },
  {
    n: '02',
    title: 'One number, no surprises',
    body: 'Within 2 hours you get a plan and a fixed price. That number doesn’t move once we start, whatever the job turns out to involve.',
  },
  {
    n: '03',
    title: 'Hand-coded design & build',
    body: 'Every page is written from scratch — no page-builder, no theme, no plugin waiting to break. You see real progress as it happens, not radio silence until launch day.',
  },
  {
    n: '04',
    title: 'You check it before it goes live',
    body: 'Load it on your own phone, on your own site, before anything is public. Tweaks during this stage are included, not billed as extras.',
  },
  {
    n: '05',
    title: '30 days of aftercare, then it’s yours',
    body: 'Free tweaks for a month after launch. After that the code and the domain are outright yours — no monthly retainer, no being locked to me to make a change.',
  },
]

export default function ProcessPage() {
  return (
    <main>
      <PageHeader
        eyebrow="Process"
        title="How a build actually runs."
        body="No discovery workshops, no sign-off committees. One person, a fixed price, and a straight line from enquiry to a site that's yours outright."
      />

      <section className="py-20 sm:py-24">
        <div className="mx-auto max-w-4xl px-5 sm:px-8">
          <ol className="relative border-l border-border pl-8 sm:pl-10">
            {STEPS.map((s, i) => (
              <Reveal
                as="li"
                key={s.n}
                delay={i * 0.06}
                className={i === STEPS.length - 1 ? 'relative' : 'relative pb-14 sm:pb-16'}
              >
                <span className="absolute -left-[calc(2rem+5px)] top-0 flex h-[9px] w-[9px] -translate-x-1/2 items-center justify-center rounded-full bg-blueprint sm:-left-[calc(2.5rem+5px)]" />
                <span className="font-mono text-xs text-blueprint">{s.n}</span>
                <h2 className="mt-2 font-display text-xl font-semibold sm:text-2xl">{s.title}</h2>
                <p className="mt-3 max-w-xl text-pretty leading-relaxed text-muted-foreground">{s.body}</p>
              </Reveal>
            ))}
          </ol>
        </div>
      </section>

      <section className="border-t border-border py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <Reveal className="max-w-2xl">
            <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">
              What that actually means
            </span>
            <h2 className="mt-4 font-display text-balance text-2xl font-bold tracking-tight sm:text-3xl">
              No stage of this involves a project manager who isn&apos;t also the person writing the code.
            </h2>
          </Reveal>
          <Reveal stagger className="mt-10 grid gap-5 sm:grid-cols-3">
            {[
              ['1', 'Person you deal with, start to finish'],
              ['2 hrs', 'Typical time to a fixed price'],
              ['0', 'Retainers or monthly fees once it ships'],
            ].map(([value, label]) => (
              <div key={label} className="rounded-xl border border-border bg-card/40 p-6">
                <div className="font-mono text-3xl font-bold text-blueprint">{value}</div>
                <div className="mt-2 text-sm text-muted-foreground">{label}</div>
              </div>
            ))}
          </Reveal>
          <p className="mt-8 text-sm text-muted-foreground">
            Curious what your build would actually cost?{' '}
            <Link href="/work#estimate" className="text-blueprint underline-offset-4 hover:underline">
              Try the instant estimate
            </Link>
            .
          </p>
        </div>
      </section>

      <CtaBand />
    </main>
  )
}
