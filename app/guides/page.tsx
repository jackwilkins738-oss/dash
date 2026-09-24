import type { Metadata } from 'next'
import Link from 'next/link'
import { ArrowRight } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Breadcrumbs } from '@/components/breadcrumbs'
import { Reveal } from '@/components/reveal'

export const metadata: Metadata = {
  title: 'Website Guides for UK Trades',
  description: 'Plain-English guides for tradespeople on website costs, what a trade website needs and how to choose who builds it.',
  alternates: { canonical: '/guides' },
}

const GUIDES = [
  {
    href: '/guides/how-much-does-a-tradesman-website-cost',
    title: 'How much does a website cost for a tradesman?',
    body: 'DIY builders, freelancers, agencies and fixed-price builds compared, plus the costs people forget and the questions to ask first.',
  },
  {
    href: '/guides/website-or-facebook-page-for-tradesmen',
    title: 'Website or Facebook page? What actually wins work.',
    body: 'A fair comparison of running your trade business on a Facebook or Instagram page versus your own website, and where relying on one alone costs you jobs.',
  },
]

export default function GuidesPage() {
  return (
    <main>
      <Breadcrumbs items={[{ name: 'Guides', href: '/guides' }]} />
      <PageHeader compact
        eyebrow="Guides"
        title="Website guides for UK trades."
        body="Plain-English answers to the questions tradespeople ask before they commission a website."
      />
      <section className="py-20 sm:py-24">
        <div className="mx-auto max-w-4xl px-5 sm:px-8">
          <Reveal stagger className="grid gap-5">
            {GUIDES.map((g) => (
              <Link
                key={g.href}
                href={g.href}
                className="group rounded-2xl border border-border bg-card/40 p-7 transition-colors hover:border-blueprint/40"
              >
                <h2 className="font-display text-2xl font-semibold group-hover:text-blueprint">{g.title}</h2>
                <p className="mt-3 max-w-2xl text-sm leading-relaxed text-muted-foreground">{g.body}</p>
                <span className="mt-5 inline-flex items-center gap-2 font-mono text-xs uppercase tracking-[0.15em] text-blueprint">
                  Read the guide
                  <ArrowRight className="h-3.5 w-3.5 transition-transform group-hover:translate-x-1" />
                </span>
              </Link>
            ))}
          </Reveal>
        </div>
      </section>
    </main>
  )
}
