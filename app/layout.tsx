import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { Space_Grotesk, Geist_Mono } from 'next/font/google'
import './globals.css'
import { SmoothScroll } from '@/components/smooth-scroll'
import { Preloader } from '@/components/preloader'
import { SiteNav } from '@/components/site-nav'
import { SiteFooter } from '@/components/site-footer'

const spaceGrotesk = Space_Grotesk({
  subsets: ['latin'],
  variable: '--font-space-grotesk',
  display: 'swap',
})

const geistMono = Geist_Mono({
  subsets: ['latin'],
  variable: '--font-geist-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Scalar Digital — Pure-code websites for high-end UK trades',
  description:
    'We build fast, hand-coded websites for driveways, landscaping, loft conversions, extensions and roofing firms. No WordPress bloat. Full ownership. From £2,500.',
  generator: 'v0.app',
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
  themeColor: '#0a0d10',
  maximumScale: 5,
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en-GB" className={`${spaceGrotesk.variable} ${geistMono.variable}`}>
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
