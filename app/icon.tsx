import { ImageResponse } from 'next/og'

// Replaces a static icon.svg that turned out to be a leftover v0.app
// logo mark, not Scalar Digital's own branding - generated at request
// time instead, so there's no static asset to accidentally leave stale.
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
        }}
      >
        <div style={{ color: 'white', fontSize: 32, fontWeight: 800, letterSpacing: -1 }}>SD</div>
      </div>
    ),
    { ...size }
  )
}
