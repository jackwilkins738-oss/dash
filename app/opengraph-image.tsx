import { readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { ImageResponse } from 'next/og'

export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

const GOLD = '#d9b16a'
const BLUE = '#4d9be0'

export default async function OpengraphImage() {
  // Same crest as the WhatsApp profile picture, embedded so the preview
  // matches it wherever the link is shared.
  const crest = await readFile(join(process.cwd(), 'public', 'brand', 'crest.png'))
  const crestSrc = `data:image/png;base64,${crest.toString('base64')}`

  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '64px 72px',
          background:
            'radial-gradient(70% 90% at 82% 50%, rgba(58,155,230,0.22), rgba(58,155,230,0) 65%), linear-gradient(155deg, #070b13 0%, #0d1524 55%, #12233a 100%)',
          fontFamily: 'sans-serif',
          position: 'relative',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: 22,
            left: 22,
            right: 22,
            bottom: 22,
            display: 'flex',
            border: '1.5px solid rgba(217,177,106,0.35)',
          }}
        />

        <div style={{ display: 'flex', flexDirection: 'column', width: 640 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ display: 'flex', width: 44, height: 2, background: GOLD }} />
            <div style={{ color: GOLD, fontSize: 24, letterSpacing: 7, textTransform: 'uppercase', fontWeight: 700 }}>
              Scalar Digital
            </div>
          </div>
          <div
            style={{
              marginTop: 34,
              color: 'white',
              fontSize: 64,
              fontWeight: 800,
              lineHeight: 1.08,
              letterSpacing: -1.5,
            }}
          >
            Websites that look more expensive than the job you&apos;re quoting.
          </div>
          <div style={{ display: 'flex', gap: 48, marginTop: 46 }}>
            {[
              ['0.4s', 'Average load time'],
              ['100', 'Lighthouse target'],
              ['£750', 'Fixed from'],
            ].map(([value, label]) => (
              <div key={label} style={{ display: 'flex', flexDirection: 'column' }}>
                <div style={{ color: BLUE, fontSize: 38, fontWeight: 800 }}>{value}</div>
                <div style={{ color: '#8a99ad', fontSize: 19, marginTop: 4 }}>{label}</div>
              </div>
            ))}
          </div>
        </div>

        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={crestSrc} width={400} height={400} alt="" style={{ borderRadius: 999 }} />
      </div>
    ),
    { ...size },
  )
}
