import type { Metadata } from 'next'
import Link from 'next/link'
import { PageHeader } from '@/components/page-header'
import { Breadcrumbs } from '@/components/breadcrumbs'
import { SpeedCheck } from '@/components/speed-check'
import { Faq, type QA } from '@/components/faq'
import { CtaBand } from '@/components/cta-band'
import { Reveal } from '@/components/reveal'

export const metadata: Metadata = {
  title: 'Free Website Speed Test for Trade Businesses',
  description:
    "Check your website's real Google PageSpeed score for free, live, against Scalar's own — the same test Google uses to help decide where you rank.",
  alternates: { canonical: '/speed-test' },
}

const FAQS: QA[] = [
  {
    q: 'Is this the same test Google actually uses?',
    a: "Yes. It calls Google's own PageSpeed Insights API directly from your browser — the same tool behind web.dev and the same signal Google factors into mobile search ranking. Nothing here is simulated or estimated.",
  },
  {
    q: 'Why does it sometimes take a minute or more?',
    a: "A real Lighthouse audit loads your site properly and measures it, rather than guessing from a cached snapshot — that's what makes the number trustworthy. Google's own servers set the pace, not this page, so a slow or heavy site can take longer to test.",
  },
  {
    q: "What's a good score?",
    a: '90 and above is fast. 50 to 89 means there is real room to improve. Below 50 means a meaningful number of visitors on mobile are likely leaving before the page finishes loading.',
  },
  {
    q: 'My score is bad — what actually fixes it?',
    a: 'Usually it is the platform, not the content: heavy themes, page-builders and a stack of plugins all add code that has to load before anything useful appears. A hand-coded site has none of that to strip out in the first place, which is the main reason a Scalar build tends to score well without any extra optimisation work.',
  },
]

export default function SpeedTestPage() {
  return (
    <main>
      <Breadcrumbs items={[{ name: 'Free speed test', href: '/speed-test' }]} />
      <PageHeader
        compact
        eyebrow="Free tool"
        title="Test your website's real speed, free."
        body="Not a lead magnet gimmick — the same live Google test used to help decide where you rank, run right here against your own site."
      />

      <SpeedCheck />

      <section className="border-t border-border py-20 sm:py-24">
        <div className="mx-auto max-w-4xl px-5 sm:px-8">
          <Reveal>
            <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Why it matters</span>
            <h2 className="mt-4 font-display text-balance text-2xl font-bold tracking-tight sm:text-3xl">
              A slow site is a quiet way to lose jobs you never hear about.
            </h2>
            <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
              Google has reported that more than half of mobile visits are abandoned when a page takes longer than
              three seconds to load. Nobody complains about a slow site — they just leave, and call the next name on
              the list instead. Speed also feeds directly into Google&apos;s own ranking signals, so a slow site is
              working against you twice: fewer people find it, and fewer of the people who do stay long enough to
              get in touch.
            </p>
            <p className="mt-8 text-sm text-muted-foreground">
              Want the number fixed, not just measured?{' '}
              <Link href="/work#pricing" className="text-blueprint underline-offset-4 hover:underline">
                See what a hand-coded build costs
              </Link>
              .
            </p>
          </Reveal>
        </div>
      </section>

      <Faq items={FAQS} title="About this speed test" eyebrow="FAQ" />
      <CtaBand />
    </main>
  )
}
