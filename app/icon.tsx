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
      // Gold on near-black, restrained weight, wide tracking - the
      // classic luxury-monogram signal (hospitality/jewelry branding),
      // rather than a bright saturated gradient with heavy bold text,
      // which reads as tech-startup rather than premium.
      <div
        style={{
          width: '100%',
          height: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'radial-gradient(circle at 50% 40%, #171c24, #0a0e16)',
          borderRadius: 14,
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: 46,
            height: 46,
            borderRadius: '50%',
            border: '1.5px solid #c9a15a',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              color: '#c9a15a',
              fontSize: 19,
              fontWeight: 500,
              letterSpacing: 2,
            }}
          >
            <span>S</span>
            <span style={{ margin: '0 1px', opacity: 0.75 }}>·</span>
            <span>D</span>
          </div>
        </div>
      </div>
    ),
    { ...size }
  )
}
