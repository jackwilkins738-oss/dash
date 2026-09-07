import { ImageResponse } from 'next/og'

// The "S·D" mark, matching the wordmark already used in the nav/footer/
// preloader (same brand gradient, same accent-colored center dot) - not a
// brand-new symbol invented just for the favicon. Rounded rather than
// chamfered: Satori (the renderer behind ImageResponse) doesn't reliably
// support clip-path, and a cut corner is barely perceptible at 32-64px
// anyway - a rounded square is the standard, safe choice at this size.
export const size = { width: 64, height: 64 }
export const contentType = 'image/png'

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(155deg, #4d84c4, #1f3a5c)',
          borderRadius: 14,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', color: 'white', fontSize: 30, fontWeight: 800 }}>
          <span>S</span>
          <span style={{ color: '#8fc4ee', margin: '0 1px' }}>·</span>
          <span>D</span>
        </div>
      </div>
    ),
    { ...size }
  )
}
