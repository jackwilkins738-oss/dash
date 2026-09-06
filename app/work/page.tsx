import type { Metadata } from 'next'
import { Services } from '@/components/services'
import { Work } from '@/components/work'
import { Pricing } from '@/components/pricing'
import { CtaBand } from '@/components/cta-band'
import { PageHeader } from '@/components/page-header'

export const metadata: Metadata = {
  title: 'Services & Work — Scalar Digital',
  description:
    'What I build and who I build it for. Fast, hand-coded websites for UK trades, real case-study results, and one fixed price from £2,500.',
}

export default function WorkPage() {
  return (
    <main>
      <PageHeader
        eyebrow="Services & Work"
        title="Built to sell your trade harder than you can."
        body="Every site does the same six things properly, backed by results you can measure and a price fixed before we start."
      />
      <Services />
      <Work />
      <Pricing />
      <CtaBand />
    </main>
  )
}
