import { getProspect } from '@/lib/prospect-api'

// Their own logo and photos for "your homepage, rebuilt" on their preview page,
// served from this site. Fetched here rather than linked straight from their
// site so the page's content security policy stays tight (img-src is 'self'),
// their site never sees the visitor, and hotlink protection can't break it.
//
// Not an open proxy: it only ever fetches a URL the dashboard saved for this
// one prospect (logo, or photo 0-3) - already checked to be an https
// jpg/png/webp - and only passes back a raster image of a sensible size.

const MAX_BYTES = 3_000_000
const OK_TYPES = /^image\/(jpeg|png|webp)$/

function notFound() {
  return new Response('Not found', { status: 404, headers: { 'Cache-Control': 'public, max-age=300' } })
}

export async function GET(_req: Request, props: { params: Promise<{ slug: string; which: string }> }) {
  const { slug, which } = await props.params
  const p = await getProspect(slug)
  const t = p?.teardown
  const url = which === 'logo' ? t?.logo : /^[0-3]$/.test(which) ? t?.photos?.[Number(which)] : undefined
  if (!url || !url.startsWith('https://')) return notFound()

  let res: Response
  try {
    res = await fetch(url, {
      headers: { 'User-Agent': 'ScalarDigitalPreview/1.0', Accept: 'image/jpeg,image/png,image/webp' },
      redirect: 'follow',
      signal: AbortSignal.timeout(8000),
      cache: 'no-store',
    })
  } catch {
    return notFound()
  }
  const type = (res.headers.get('content-type') || '').split(';')[0].trim().toLowerCase()
  const length = Number(res.headers.get('content-length') || 0)
  if (!res.ok || !OK_TYPES.test(type) || length > MAX_BYTES) return notFound()
  const body = await res.arrayBuffer()
  if (body.byteLength > MAX_BYTES) return notFound()

  return new Response(body, {
    headers: {
      'Content-Type': type,
      'Cache-Control': 'public, max-age=86400, s-maxage=86400',
      'X-Content-Type-Options': 'nosniff',
      'Content-Security-Policy': "default-src 'none'",
      'X-Robots-Tag': 'noindex',
    },
  })
}
