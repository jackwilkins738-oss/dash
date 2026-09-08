/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'Strict-Transport-Security', value: 'max-age=63072000' },
          { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
          {
            key: 'Content-Security-Policy',
            value: [
              "default-src 'self'",
              // admin.scalardigital.co.uk serves track.js - the dashboard
              // product's tracking snippet used on this site itself.
              "script-src 'self' 'unsafe-inline' https://admin.scalardigital.co.uk",
              "style-src 'self' 'unsafe-inline'",
              // Storage public URLs for the "currently on site" project
              // photos (gallery.js) are served from this same Supabase
              // project.
              "img-src 'self' data: blob: https://wfyzsnyfliohevpjpuib.supabase.co",
              "font-src 'self' data:",
              // track.js posts page views straight to Supabase, and leads
              // through admin.scalardigital.co.uk/api/leads - both need to
              // be reachable or the script loads but every fetch it makes
              // gets silently blocked too.
              "connect-src 'self' https://admin.scalardigital.co.uk https://wfyzsnyfliohevpjpuib.supabase.co",
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
