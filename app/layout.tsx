import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { Bricolage_Grotesque, Instrument_Sans, IBM_Plex_Mono } from 'next/font/google'
import './globals.css'
import { SmoothScroll } from '@/components/smooth-scroll'
import { Preloader } from '@/components/preloader'
import { SiteNav } from '@/components/site-nav'
import { SiteFooter } from '@/components/site-footer'

// Bricolage/Instrument/Plex Mono instead of Space Grotesk + Geist Mono -
// the latter pair is the recognizable "safe AI-generated site" default
// (Geist especially, being Vercel's own face used everywhere v0 generates).
// Plex Mono also ties this site's type system back to the dashboard
// product's own mono face for a consistent Scalar Digital signature.
const bricolage = Bricolage_Grotesque({
  subsets: ['latin'],
  variable: '--font-bricolage',
  display: 'swap',
})

const instrumentSans = Instrument_Sans({
  subsets: ['latin'],
  variable: '--font-instrument',
  display: 'swap',
})

const plexMono = IBM_Plex_Mono({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  variable: '--font-plex-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Scalar Digital — Pure-code websites for high-end UK trades',
  description:
    'We build fast, hand-coded websites for driveways, landscaping, loft conversions, extensions and roofing firms. No WordPress bloat. Full ownership. From £2,500.',
  keywords: [
    'web design for tradesmen',
    'driveway website design',
    'landscaping website',
    'loft conversion website',
    'builder website UK',
    'local SEO trades',
  ],
  openGraph: {
    title: 'Scalar Digital — Pure-code websites for high-end UK trades',
    description:
      'Websites that look more expensive than the jobs you quote. Fast, hand-coded, fully owned. From £2,500.',
    type: 'website',
  },
}

export const viewport: Viewport = {
  colorScheme: 'dark',
  themeColor: '#0a0e16',
  maximumScale: 5,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en-GB" className={`${bricolage.variable} ${instrumentSans.variable} ${plexMono.variable}`}>
      <body className="antialiased font-sans">
        <Preloader />
        <SmoothScroll />
        <SiteNav />
        {children}
        <SiteFooter />
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
