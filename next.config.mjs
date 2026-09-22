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
  // Static example builds live as plain HTML under public/examples/<slug>/index.html
  // (see components/example-build.tsx) - files in public/ are served at their
  // literal path, with no directory-index resolution, so without this a
  // visitor typing the clean URL gets a 404. Add one rewrite per example as
  // they're built.
  async rewrites() {
    return [
      { source: '/examples/verdigris-roofing', destination: '/examples/verdigris-roofing/index.html' },
      { source: '/examples/verdigris-roofing/', destination: '/examples/verdigris-roofing/index.html' },
    ]
  },
  // experimental.inlineCss was tried and removed. The Next docs recommend it for
  // small Tailwind CSS with mostly first-time visitors, which describes this
  // site, so it was enabled - and then measured properly (Lighthouse mobile,
  // median of 3, one variable changed): it made things WORSE. Inlining
  // duplicates the styles in the page payload, tripling the HTML from 33KB to
  // 84KB, and first paint slipped from 1.10s to 1.43s. The render-blocking
  // request it saves costs less than the bytes it adds. Worth re-testing if
  // the CSS ever gets much smaller, but not before.
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
              // googleapis.com is the live PageSpeed Insights check on the
              // homepage (components/speed-check.tsx) - it calls Google
              // directly from the visitor's own browser, no server involved.
              "connect-src 'self' https://admin.scalardigital.co.uk https://wfyzsnyfliohevpjpuib.supabase.co https://*.google-analytics.com https://*.analytics.google.com https://www.googletagmanager.com https://www.googleapis.com",
              "frame-ancestors 'none'",
              "object-src 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join('; '),
          },
        ],
      },
      // Images in public/ are served by Next with `max-age=0`, so every visit
      // re-checks them (Lighthouse: "Use efficient cache lifetimes"). They are
      // not content-hashed, so they cannot be marked immutable - but a day of
      // freshness plus a week of stale-while-revalidate stops the re-check on
      // every page view, while a changed logo still shows up within a day.
      {
        source: '/brand/:path*',
        headers: [{ key: 'Cache-Control', value: 'public, max-age=86400, stale-while-revalidate=604800' }],
      },
      {
        source: '/examples/:path*',
        headers: [{ key: 'Cache-Control', value: 'public, max-age=86400, stale-while-revalidate=604800' }],
      },
    ]
  },
}

export default nextConfig
