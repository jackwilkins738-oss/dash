import type { Metadata } from 'next'
import { Services } from '@/components/services'
import { Pricing } from '@/components/pricing'
import { CostCalculator } from '@/components/cost-calculator'
import { CtaBand } from '@/components/cta-band'
import { PageHeader } from '@/components/page-header'

export const metadata: Metadata = {
  title: 'Services & Pricing — Scalar Digital',
  description:
    'What I build and how it works. Fast, hand-coded websites for UK trades, fixed price from £750.',
  alternates: { canonical: '/work' },
}

export default function WorkPage() {
  return (
    <main>
      <PageHeader
        eyebrow="Services & Pricing"
        title="Built to sell your trade harder than you can."
        body="Every site does the same six things properly, at a price fixed before we start."
      />
      <Services />
      <Pricing />
      <CostCalculator />
      <CtaBand />
    </main>
  )
}
