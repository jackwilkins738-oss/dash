import { ogCard, OG_SIZE, OG_TYPE } from '@/lib/og-card'

export const size = OG_SIZE
export const contentType = OG_TYPE

export default function OpengraphImage() {
  return ogCard({ eyebrow: 'Scalar Digital guide', title: 'How to get your trade business on Google Maps.' })
}
