import { readFile } from 'node:fs/promises'
import { join } from 'node:path'
import { ImageResponse } from 'next/og'

// The link-preview card (WhatsApp, Facebook, LinkedIn, iMessage). One design, so a shared trade
// page or guide looks like the same firm as the homepage, with its own headline on it.

export const OG_SIZE = { width: 1200, height: 630 }
export const OG_TYPE = 'image/png'

const GOLD = '#d9b16a'
const BLUE = '#4d9be0'

type Card = { eyebrow: string; title: string; stats?: [string, string][] }

export async function ogCard({ eyebrow, title, stats }: Card) {
  // The brand mark, embedded so the preview matches it wherever the link is shared.
  const mark = await readFile(join(process.cwd(), 'public', 'brand', 'mark.png'))
  const markSrc = `data:image/png;base64,${mark.toString('base64')}`
  const titleSize = title.length > 70 ? 50 : title.length > 50 ? 58 : 64

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
              {eyebrow}
            </div>
          </div>
          <div
            style={{
              marginTop: 34,
              color: 'white',
              fontSize: titleSize,
              fontWeight: 800,
              lineHeight: 1.08,
              letterSpacing: -1.5,
            }}
          >
            {title}
          </div>
          {stats ? (
            <div style={{ display: 'flex', gap: 48, marginTop: 46 }}>
              {stats.map(([value, label]) => (
                <div key={label} style={{ display: 'flex', flexDirection: 'column' }}>
                  <div style={{ color: BLUE, fontSize: 38, fontWeight: 800 }}>{value}</div>
                  <div style={{ color: '#8a99ad', fontSize: 19, marginTop: 4 }}>{label}</div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{ display: 'flex', marginTop: 46, color: '#8a99ad', fontSize: 24, letterSpacing: 2 }}>
              scalardigital.co.uk
            </div>
          )}
        </div>

        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={markSrc} width={340} height={333} alt="" style={{ marginRight: 30 }} />
      </div>
    ),
    { ...OG_SIZE },
  )
}
