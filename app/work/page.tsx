import type { Metadata } from 'next'
import Link from 'next/link'
import { Services } from '@/components/services'
import { DashPitch } from '@/components/dash-pitch'
import { Pricing } from '@/components/pricing'
import { CostCalculator } from '@/components/cost-calculator'
import { CtaBand } from '@/components/cta-band'
import { PageHeader, HeaderActions } from '@/components/page-header'
import { Breadcrumbs } from '@/components/breadcrumbs'
import { Faq, type QA } from '@/components/faq'
import { TRADES } from '@/lib/trades'

export const metadata: Metadata = {
  title: 'Tradesman Website Prices, From £750',
  description:
    'Fixed-price, hand-coded websites for UK trades: a £750 landing page or a £2,500 five-page site with a private dashboard. Fast on a phone, and you own it outright.',
  alternates: { canonical: '/work' },
}

const FAQS: QA[] = [
  {
    q: 'How much does a website cost for a tradesman?',
    a: 'With Scalar Digital, a hand-coded landing page is £750 and the full five-page build is £2,500, which includes a private dashboard for enquiries, quotes, jobs and invoices. The price is fixed before any work starts. Elsewhere, DIY website builders cost roughly £10 to £30 a month, freelancers commonly charge £500 to £3,000, and agencies often charge more. See the cost guide for a full comparison.',
  },
  {
    q: 'Do I own the website and the domain?',
    a: 'Yes. You pay once and own the code and the domain outright. There is no monthly rental on your site. The private dashboard that comes with the full build is hosted for free for your first 12 months, then for a small optional monthly dashboard fee agreed up front. Your website is always yours, with or without the dashboard.',
  },
  {
    q: 'What is the difference between the £750 and £2,500 options?',
    a: 'The £750 option is a single hand-coded landing page with your services, a call and WhatsApp button and an enquiry form. The £2,500 option is five hand-coded pages, including a gallery and a service areas page, plus local SEO built into the structure, Google Business and reviews wired in, and a private dashboard.',
  },
  {
    q: 'Why hand-coded instead of WordPress?',
    a: 'Hand-coded pages carry no themes or plugins, so they load quickly on a phone and there is nothing extra to update or for someone to break into. Speed matters because most trade customers search on a mobile, often on a weak signal.',
  },
  {
    q: 'Will my website help me rank on Google?',
    a: 'A fast, well-structured site with clear pages for each service and area gives you the best foundation, and the full build includes local SEO in its structure. No one can honestly guarantee a ranking, though, because it also depends on competition, reviews and time. Be wary of anyone who promises first place.',
  },
]

export default function WorkPage() {
  return (
    <main>
      <Breadcrumbs items={[{ name: 'Services & pricing', href: '/work' }]} />
      <PageHeader compact
        eyebrow="Services & Pricing"
        title="Built to sell your trade harder than you can."
        body="Every site does the same six things properly, at a price fixed before we start."
        actions={<HeaderActions secondary={{ href: '#pricing', label: 'See the prices' }} />}
      />
      <Services />
      <DashPitch />
      <Pricing />

      <section className="border-t border-border py-12">
        <div className="mx-auto flex max-w-6xl flex-col gap-4 px-5 sm:flex-row sm:items-center sm:justify-between sm:px-8">
          <p className="text-sm text-muted-foreground">
            Comparing options? Read{' '}
            <Link
              href="/guides/how-much-does-a-tradesman-website-cost"
              className="text-blueprint underline-offset-4 hover:underline"
            >
              what a tradesman&apos;s website really costs
            </Link>
            .
          </p>
          <ul className="flex flex-wrap gap-2">
            {TRADES.map((t) => (
              <li key={t.slug}>
                <Link
                  href={`/websites-for/${t.slug}`}
                  className="rounded-full border border-border px-3 py-1.5 font-mono text-[11px] uppercase tracking-[0.12em] text-muted-foreground transition-colors hover:border-blueprint hover:text-blueprint"
                >
                  {t.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <CostCalculator />
      <Faq items={FAQS} title="Website prices and what you get" eyebrow="Pricing FAQ" />
      <CtaBand />
    </main>
  )
}
