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
      // Same gold-on-black medallion as icon.tsx, scaled up - no radius
      // here since iOS applies its own corner mask on top of this.
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'radial-gradient(circle at 50% 40%, #171c24, #0a0e16)',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 130,
            height: 130,
            borderRadius: '50%',
            border: '3px solid #c9a15a',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              color: '#c9a15a',
              fontSize: 54,
              fontWeight: 500,
              letterSpacing: 6,
            }}
          >
            <span>S</span>
            <span style={{ margin: '0 3px', opacity: 0.75 }}>·</span>
            <span>D</span>
          </div>
        </div>
      </div>
    ),
    { ...size }
  )
}
