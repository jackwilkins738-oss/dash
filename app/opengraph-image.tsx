import { ImageResponse } from 'next/og'

export const size = { width: 1200, height: 630 }
export const contentType = 'image/png'

export default function OpengraphImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          padding: '80px',
          background: 'linear-gradient(155deg, #0a0e16 0%, #101827 55%, #14263c 100%)',
          fontFamily: 'sans-serif',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div
            style={{
              display: 'flex',
              width: 14,
              height: 14,
              borderRadius: 999,
              background: '#4d84c4',
            }}
          />
          <div style={{ color: '#8a99ad', fontSize: 26, letterSpacing: 6, textTransform: 'uppercase' }}>
            Web design for high-end UK trades
          </div>
        </div>
        <div
          style={{
            marginTop: 36,
            color: 'white',
            fontSize: 68,
            fontWeight: 800,
            lineHeight: 1.08,
            letterSpacing: -1.5,
            maxWidth: 980,
          }}
        >
          Websites that look more expensive than the job you&apos;re quoting.
        </div>
        <div style={{ display: 'flex', gap: 56, marginTop: 56 }}>
          {[
            ['0.4s', 'Average load time'],
            ['100', 'Lighthouse target'],
            ['£2,500', 'Fixed from'],
          ].map(([value, label]) => (
            <div key={label} style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ color: '#4d84c4', fontSize: 40, fontWeight: 800 }}>{value}</div>
              <div style={{ color: '#8a99ad', fontSize: 20, marginTop: 4 }}>{label}</div>
            </div>
          ))}
        </div>
      </div>
    ),
    { ...size },
  )
}
