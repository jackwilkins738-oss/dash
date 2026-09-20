import type { Metadata } from 'next'
import Link from 'next/link'
import { Check } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { ReferralLink } from '@/components/referral-link'
import { Reveal } from '@/components/reveal'

export const metadata: Metadata = {
  title: 'Refer a business — Scalar Digital',
  description:
    'Know a tradesperson who needs a better website? They get 15% off their build, and you get 10% off a future one.',
  alternates: { canonical: '/refer' },
}

const STEPS = [
  { n: '01', title: 'Get your link', body: 'Type your name below and copy your personal link.' },
  { n: '02', title: 'Send it on', body: 'Pass it to a tradesperson who needs a website that does their work justice.' },
  { n: '03', title: 'You both save', body: 'They get 15% off their build. You get 10% off yours, once theirs is paid for.' },
]

const TERMS = [
  'Discounts apply to the build price: £750 for a landing page, £2,500 for The Scalar build.',
  'Anyone can refer, and there’s no limit on how many people you refer.',
  'The person you refer gets 15% off their build when they get in touch through your link or give me your name.',
  'You get 10% off a future build once the person you referred has paid for theirs. If we agree it by phone, I can pay it as cash instead.',
]

export default function ReferPage() {
  return (
    <main>
      <PageHeader
        eyebrow="Refer a business"
        title="Know a tradesperson with a tired website? You both save."
        body="They get 15% off their build. You get 10% off a future one. Nothing to sign up for."
      />

      <section className="py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <Reveal stagger className="grid gap-5 md:grid-cols-3">
            {STEPS.map((s) => (
              <div key={s.n} className="rounded-2xl border border-border bg-card/40 p-7">
                <span className="font-mono text-sm text-blueprint">{s.n}</span>
                <h2 className="mt-4 font-display text-lg font-semibold">{s.title}</h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.body}</p>
              </div>
            ))}
          </Reveal>

          <div className="mt-14 grid gap-10 lg:grid-cols-[1.1fr_1fr] lg:gap-14">
            <Reveal>
              <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Your link</span>
              <h2 className="mt-3 font-display text-balance text-2xl font-bold tracking-tight sm:text-3xl">
                Make your referral link
              </h2>
              <div className="mt-6">
                <ReferralLink />
              </div>
            </Reveal>

            <Reveal delay={0.1}>
              <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">The details</span>
              <h2 className="mt-3 font-display text-balance text-2xl font-bold tracking-tight sm:text-3xl">
                How it works
              </h2>
              <ul className="mt-6 space-y-4">
                {TERMS.map((t) => (
                  <li key={t} className="flex items-start gap-3 text-sm leading-relaxed text-foreground/90">
                    <Check className="mt-0.5 h-4 w-4 flex-none text-blueprint" strokeWidth={2.5} />
                    {t}
                  </li>
                ))}
              </ul>
              <p className="mt-6 text-sm leading-relaxed text-muted-foreground">
                Questions?{' '}
                <Link href="/contact" className="text-blueprint underline-offset-4 hover:underline">
                  Get in touch
                </Link>
                .
              </p>
            </Reveal>
          </div>
        </div>
      </section>
    </main>
  )
}
