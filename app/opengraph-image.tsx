import { ogCard, OG_SIZE, OG_TYPE } from '@/lib/og-card'
import { PRICES } from '@/lib/site'

export const size = OG_SIZE
export const contentType = OG_TYPE

export default function OpengraphImage() {
  return ogCard({
    eyebrow: 'Scalar Digital',
    title: 'Websites that look more expensive than the job you’re quoting.',
    stats: [
      ['<1s', 'Load time on desktop'],
      ['100', 'Lighthouse target'],
      [`£${PRICES.landing}`, 'Fixed from'],
    ],
  })
}
