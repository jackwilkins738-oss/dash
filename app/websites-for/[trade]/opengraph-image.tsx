import { ogCard, OG_SIZE, OG_TYPE } from '@/lib/og-card'
import { TRADES, TRADE_BY_SLUG } from '@/lib/trades'

export const size = OG_SIZE
export const contentType = OG_TYPE

export function generateStaticParams() {
  return TRADES.map((t) => ({ trade: t.slug }))
}

export default async function OpengraphImage({ params }: { params: Promise<{ trade: string }> }) {
  const { trade } = await params
  const t = TRADE_BY_SLUG[trade]
  return ogCard({ eyebrow: t?.eyebrow ?? 'Scalar Digital', title: t?.h1 ?? 'Websites for UK trades.' })
}
