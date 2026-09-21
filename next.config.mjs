// React's development build uses eval() to rebuild stack traces across
// environments, so `next dev` logs a CSP error and loses debugging features
// unless 'unsafe-eval' is allowed. It is added for development only - the
// production header is unchanged, and React never uses eval() in production.
const isDev = process.env.NODE_ENV === 'development'
const scriptSrc = [
  "script-src 'self' 'unsafe-inline'",
  isDev ? "'unsafe-eval'" : null,
  'https://admin.scalardigital.co.uk',
  // googletagmanager.com serves the GA4 tag. Without it the consent banner,
  // the analytics and the privacy-policy section describing them were all
  // live while the script itself was blocked by this very header.
  'https://www.googletagmanager.com',
]
  .filter(Boolean)
  .join(' ')

/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    // Puts the CSS in the HTML instead of a separate render-blocking request
    // (Lighthouse measured that request at ~316ms on a mobile connection, and
    // nothing can paint until it arrives). The trade-off in the Next docs is
    // that inlined CSS can't be cached between visits - which barely matters
    // here: the stylesheet is small (Tailwind), and most visitors are new
    // arrivals from cold email rather than people returning to the site.
    inlineCss: true,
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          // includeSubDomains covers admin.scalardigital.co.uk (the dashboard
          // product) as well as the apex; preload makes browsers enforce
          // HTTPS on a first-ever visit, before any response is seen.
          { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
          // frame-ancestors in the CSP below is the modern equivalent, but
          // this is still what older browsers honour.
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              // admin.scalardigital.co.uk serves track.js - the dashboard
              // product's tracking snippet used on this site itself.
              scriptSrc,
              "style-src 'self' 'unsafe-inline'",
              // Storage public URLs for the "currently on site" project
              // photos (gallery.js) are served from this same Supabase
              // project.
              // GA4 falls back to a tracking pixel when fetch/beacon isn't
              // available, so it needs img-src as well as connect-src.
              "img-src 'self' data: blob: https://wfyzsnyfliohevpjpuib.supabase.co https://*.google-analytics.com https://www.googletagmanager.com",
              "font-src 'self' data:",
              // track.js posts page views straight to Supabase, and leads
              // through admin.scalardigital.co.uk/api/leads - both need to
              // be reachable or the script loads but every fetch it makes
              // gets silently blocked too.
              // GA4 posts hits to google-analytics.com, and to a regional
              // endpoint (region1, region2...) depending on where the
              // visitor is - allowing only the bare domain drops EU traffic,
              // which is essentially all of it for a UK trades site.
              "connect-src 'self' https://admin.scalardigital.co.uk https://wfyzsnyfliohevpjpuib.supabase.co https://*.google-analytics.com https://*.analytics.google.com https://www.googletagmanager.com",
              "frame-ancestors 'none'",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join('; '),
          },
        ],
      },
    ]
  },
}

export default nextConfig
