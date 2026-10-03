import type { Metadata } from 'next'
import Link from 'next/link'
import { Check } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { ReferralLink } from '@/components/referral-link'
import { Reveal } from '@/components/reveal'
import { PARTNER, PRICES } from '@/lib/site'
import { withSeo } from '@/lib/seo'

export const metadata: Metadata = withSeo('/partners', {
  title: 'Partner With Scalar Digital',
  description: `For accountants, bookkeepers, merchants and anyone who works with trades: recommend a website that wins them work, and get £${PARTNER.perBuild} for every client who signs.`,
  alternates: { canonical: '/partners' },
})

const WHO = [
  { title: 'Accountants & bookkeepers', body: 'You see which trade clients are growing and which are stuck. A site that brings in work helps both.' },
  { title: 'Builders’ & trade merchants', body: 'Your counter sees the same tradespeople every week. A good word from you carries weight.' },
  { title: 'Insurers, trade bodies, coaches', body: 'Anyone whose clients are UK trades and would be better off with a website that actually works.' },
]

const TERMS = [
  `£${PARTNER.perBuild} for every client who takes The Scalar build (£${PRICES.build.toLocaleString('en-GB')}), or £${PARTNER.perLanding} for a landing page (£${PRICES.landing}).`,
  `Your client gets ${PARTNER.clientDiscountPercent}% off their build, so recommending us is a favour to them too.`,
  'Paid by bank transfer within 14 days of their build being paid for. No limit on how many clients you send.',
  'Nothing to sign and nothing to sell: pass on your link, or have them mention your firm when they get in touch.',
  'I only take on work I can do properly, so if a client isn’t a good fit I’ll tell them honestly, and you won’t be embarrassed by a bad job.',
]

export default function PartnersPage() {
  return (
    <main>
      <PageHeader
        eyebrow="Partners"
        title="Work with trades? Recommend a website that wins them work."
        body={`Get £${PARTNER.perBuild} for every client who signs. They get ${PARTNER.clientDiscountPercent}% off. Nothing to sign up for.`}
      />

      <section className="py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <Reveal stagger className="grid gap-5 md:grid-cols-3">
            {WHO.map((w) => (
              <div key={w.title} data-spotlight className="rounded-2xl border border-border bg-card/40 p-7 transition-colors hover:border-blueprint/40">
                <h2 className="font-display text-lg font-semibold">{w.title}</h2>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{w.body}</p>
              </div>
            ))}
          </Reveal>

          <div className="mt-14 grid gap-10 lg:grid-cols-[1.1fr_1fr] lg:gap-14">
            <Reveal>
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Your link</span>
              <h2 className="mt-3 font-display text-balance text-2xl font-bold tracking-tight sm:text-3xl">Make your partner link</h2>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                Anyone who gets in touch through it is marked as yours, so there&apos;s never a question about who sent them.
              </p>
              <div className="mt-6">
                <ReferralLink partner />
              </div>
            </Reveal>

            <Reveal delay={0.1}>
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">The details</span>
              <h2 className="mt-3 font-display text-balance text-2xl font-bold tracking-tight sm:text-3xl">How it works</h2>
              <ul className="mt-6 space-y-4">
                {TERMS.map((t) => (
                  <li key={t} className="flex items-start gap-3 text-sm leading-relaxed text-foreground/90">
                    <Check className="mt-0.5 h-4 w-4 flex-none text-blueprint" strokeWidth={2.5} />
                    {t}
                  </li>
                ))}
              </ul>
              <p className="mt-6 text-sm leading-relaxed text-muted-foreground">
                Want to talk it through first?{' '}
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
