'use client'

import { useState, type CSSProperties } from 'react'

// "Your homepage, rebuilt": their own logo, photos, services and colour, laid
// out the way a Scalar build would put them - on their private preview page.
// The images come through /for/[slug]/img/[which] (never straight from their
// site); any that fail to load simply drop out, so a blocked photo never leaves
// a broken-image icon on a page meant to impress.

const HEX = /^#[0-9a-f]{6}$/i

type Props = {
  slug: string
  name: string
  /** "Roofing", "Driveways" - shown in the headline when known. */
  tradeLabel?: string | null
  area?: string | null
  domain?: string | null
  accent?: string | null
  services?: string[]
  hasLogo: boolean
  photoCount: number
}

function Img({ src, alt, className, style }: { src: string; alt: string; className?: string; style?: CSSProperties }) {
  const [failed, setFailed] = useState(false)
  if (failed) return null
  // Plain <img>: these are their own photos at whatever size their site uses, served by our route.
  // eslint-disable-next-line @next/next/no-img-element
  return <img src={src} alt={alt} className={className} style={style} loading="lazy" decoding="async" onError={() => setFailed(true)} />
}

export function RebuiltPreview({ slug, name, tradeLabel, area, domain, accent, services = [], hasLogo, photoCount }: Props) {
  const colour = accent && HEX.test(accent) ? accent : '#1f5f8b'
  const img = (which: string) => `/for/${slug}/img/${which}`
  const headline = tradeLabel && area ? `${tradeLabel} in ${area}, done properly.` : `${name}, done properly.`
  const gallery = Array.from({ length: Math.max(0, Math.min(photoCount, 4) - 1) }, (_, i) => String(i + 1))

  return (
    <div className="mx-auto w-full max-w-[340px]">
      <div className="rounded-[2.4rem] border border-border bg-[#0b0d12] p-2.5 shadow-2xl shadow-black/40">
        <div className="overflow-hidden rounded-[1.9rem] bg-white text-[#1a1a1a]" aria-label={`A concept homepage for ${name}`}>
          {/* Header: their logo, or their name when there isn't one we can use */}
          <div className="flex items-center justify-between gap-3 border-b border-black/10 px-4 py-3">
            <div className="flex min-h-8 min-w-0 items-center">
              {hasLogo ? (
                <Img src={img('logo')} alt={`${name} logo`} className="max-h-8 max-w-[150px] object-contain" />
              ) : (
                <span className="truncate text-sm font-bold">{name}</span>
              )}
            </div>
            <span className="shrink-0 rounded-full px-3 py-1.5 text-[11px] font-bold text-white" style={{ background: colour }}>
              Call now
            </span>
          </div>

          {/* Hero: their first photo behind the headline, or their colour if there isn't one */}
          <div className="relative isolate overflow-hidden" style={{ background: colour }}>
            {photoCount > 0 && <Img src={img('0')} alt="" className="absolute inset-0 -z-10 h-full w-full object-cover" />}
            <div className="absolute inset-0 -z-10 bg-gradient-to-t from-black/75 via-black/40 to-black/10" />
            <div className="px-5 pb-6 pt-16">
              <p className="text-[22px] font-extrabold leading-tight text-white">{headline}</p>
              <p className="mt-2 text-xs text-white/85">Free quotes · Fast replies · {area ? `Covering ${area} and nearby` : 'Local and trusted'}</p>
              <div className="mt-4 flex gap-2">
                <span className="rounded-lg px-3 py-2 text-xs font-bold text-white" style={{ background: colour }}>Get a free quote</span>
                <span className="rounded-lg bg-white/95 px-3 py-2 text-xs font-bold text-[#1a1a1a]">WhatsApp us</span>
              </div>
            </div>
          </div>

          {/* What they do, in their words */}
          {services.length > 0 && (
            <div className="px-5 py-4">
              <p className="text-[11px] font-bold uppercase tracking-wider text-black/50">What we do</p>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {services.map((s) => (
                  <span key={s} className="rounded-full border px-2.5 py-1 text-[11px] font-semibold" style={{ borderColor: colour, color: colour }}>
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Their work */}
          {gallery.length > 0 && (
            <div className="px-5 pb-5">
              <p className="text-[11px] font-bold uppercase tracking-wider text-black/50">Recent work</p>
              <div className="mt-2 grid grid-cols-3 gap-1.5">
                {gallery.map((w) => (
                  <Img key={w} src={img(w)} alt={`${name} - a recent job`} className="aspect-square w-full rounded-md object-cover" />
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center justify-between border-t border-black/10 px-5 py-3 text-[10px] text-black/50">
            <span className="truncate">{domain ?? 'your-domain.co.uk'}</span>
            <span>Built for 90+ on Google&apos;s speed test</span>
          </div>
        </div>
      </div>
    </div>
  )
}
