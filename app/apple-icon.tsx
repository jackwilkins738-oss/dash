import { ImageResponse } from 'next/og'

// Replaces a static apple-icon.png that was, literally, v0.app's own
// logo - the icon shown on an iPhone home screen if someone added this
// site there. Generated instead of a static asset for the same reason
// as icon.tsx.
export const size = { width: 180, height: 180 }
export const contentType = 'image/png'

export default function AppleIcon() {
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
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', color: 'white', fontSize: 84, fontWeight: 800 }}>
          <span>S</span>
          <span style={{ color: '#8fc4ee', margin: '0 2px' }}>·</span>
          <span>D</span>
        </div>
      </div>
    ),
    { ...size }
  )
}
