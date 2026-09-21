import { Analytics } from '@vercel/analytics/next'
import type { Metadata, Viewport } from 'next'
import { Bricolage_Grotesque, Instrument_Sans, IBM_Plex_Mono } from 'next/font/google'
import './globals.css'
import './showcase.css'
import './race.css'
import './intro.css'
import { INTRO_HEAD_SCRIPT } from '@/lib/intro'
import { SmoothScroll } from '@/components/smooth-scroll'
import { Preloader } from '@/components/preloader'
import { SiteNav } from '@/components/site-nav'
import { SiteFooter } from '@/components/site-footer'
import { WhatsAppButton } from '@/components/whatsapp-button'
import { InteractionLayer } from '@/components/interaction-layer'
import { JsonLd } from '@/components/json-ld'
import { GoogleAnalytics } from '@/components/google-analytics'
import { PRICES, SITE } from '@/lib/site'

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
  metadataBase: new URL(SITE.url),
  title: {
    default: 'Scalar Digital | Web Design for UK Trades, From £750',
    template: '%s | Scalar Digital',
  },
  description: SITE.description,
  applicationName: SITE.name,
  authors: [{ name: SITE.name, url: SITE.url }],
  creator: SITE.name,
  publisher: SITE.name,
  alternates: { canonical: '/' },
  openGraph: {
    title: 'Scalar Digital | Web Design for UK Trades',
    description:
      'Websites that look more expensive than the jobs you quote. Fast, hand-coded, fully owned. Fixed price from £750.',
    type: 'website',
    url: '/',
    siteName: SITE.name,
    locale: 'en_GB',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Scalar Digital | Web Design for UK Trades',
    description: 'Websites that look more expensive than the jobs you quote. Fixed price from £750.',
  },
  robots: {
    index: true,
    follow: true,
    googleBot: { index: true, follow: true, 'max-image-preview': 'large', 'max-snippet': -1, 'max-video-preview': -1 },
  },
}

// One connected graph: the business, the website, and what it sells. Nothing here claims reviews,
// ratings, a street address or credentials the business does not have.
const structuredData = {
  '@context': 'https://schema.org',
  '@graph': [
    {
      '@type': ['Organization', 'ProfessionalService'],
      '@id': `${SITE.url}/#organization`,
      name: SITE.name,
      url: SITE.url,
      description: SITE.description,
      logo: { '@type': 'ImageObject', url: SITE.logo, width: 520, height: 520 },
      image: SITE.logo,
      email: SITE.email,
      telephone: SITE.phone,
      sameAs: [SITE.linkedin],
      areaServed: { '@type': 'Country', name: 'United Kingdom' },
      knowsAbout: [
        'Web design for tradespeople',
        'Hand-coded websites',
        'Website performance',
        'Local SEO for trades',
      ],
      hasOfferCatalog: {
        '@type': 'OfferCatalog',
        name: 'Website design for UK trades',
        itemListElement: [
          {
            '@type': 'Offer',
            name: 'Landing page',
            price: PRICES.landing,
            priceCurrency: 'GBP',
            itemOffered: { '@type': 'Service', name: 'One hand-coded, mobile-first landing page' },
          },
          {
            '@type': 'Offer',
            name: 'The Scalar build',
            price: PRICES.build,
            priceCurrency: 'GBP',
            itemOffered: {
              '@type': 'Service',
              name: 'Five hand-coded pages plus a private dashboard for enquiries, quotes, jobs and invoices',
            },
          },
        ],
      },
    },
    {
      '@type': 'WebSite',
      '@id': `${SITE.url}/#website`,
      url: SITE.url,
      name: SITE.name,
      inLanguage: 'en-GB',
      publisher: { '@id': `${SITE.url}/#organization` },
    },
  ],
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
    // suppressHydrationWarning: the script in <head> below adds `pl-seen` to
    // this element before React hydrates, so its className legitimately
    // differs from the server's by that one class. It only covers this
    // element's own attributes, not anything inside it.
    <html
      lang="en-GB"
      className={`${bricolage.variable} ${instrumentSans.variable} ${plexMono.variable}`}
      suppressHydrationWarning
    >
      <head>
        {/* Decides, before the first paint, whether this visitor has already
            seen the opening sequence this session (lib/intro.ts). It has to be
            synchronous and inline: anything deferred runs after paint, which
            for a returning visitor means the intro flashes first. ~150 bytes. */}
        <script dangerouslySetInnerHTML={{ __html: INTRO_HEAD_SCRIPT }} />
        {/* Both are talked to on every page load (track.js itself, then
            its own pageview/lead calls to Supabase) - preconnecting gets
            the DNS+TLS handshake done ahead of when those requests
            actually fire, instead of paying that latency inline. */}
        <link rel="preconnect" href="https://admin.scalardigital.co.uk" />
        <link rel="preconnect" href="https://wfyzsnyfliohevpjpuib.supabase.co" />
      </head>
      <body className="antialiased font-sans">
        <JsonLd data={structuredData} />
        <Preloader />
        <SmoothScroll />
        <InteractionLayer />
        <SiteNav />
        {children}
        <SiteFooter />
        <WhatsAppButton />
        {process.env.NODE_ENV === 'production' && <Analytics />}
        {process.env.NODE_ENV === 'production' && <GoogleAnalytics />}
        {/* Scalar Digital's own dashboard product, tracking this site as a
            real test tenant - page views and leads (via the contact
            form's data-lead-form attribute) flow into /admin's dashboard,
            same as any real customer's site. */}
        <script
          src="https://admin.scalardigital.co.uk/track.js"
          data-tenant="abdc6408-1fd5-4fb6-9c4c-53600b571a6d"
          data-site-key="4bdac492-8a7d-4826-8e25-059326f5c07f"
          defer
        />
      </body>
    </html>
  )
}
