// Their homepage loading, frame by frame, as Google's own mobile test recorded
// it - real captures, not a mock-up, so a blank first second is shown as it was.
// Inline JPEGs only (checked by the dashboard and again in lib/teardown), so
// nothing is fetched from their site.

import type { Frame } from '@/lib/teardown'

const seconds = (ms: number) => `${(ms / 1000).toFixed(1)}s`

export function LoadFilmstrip({ frames, domain }: { frames: Frame[]; domain: string }) {
  return (
    <figure className="mx-auto w-full max-w-xl">
      <div className="grid grid-cols-3 gap-3 sm:gap-5">
        {frames.map((f) => (
          <div key={f.t} className="text-center">
            <div className="overflow-hidden rounded-xl border border-border bg-white p-1 shadow-lg shadow-black/30">
              {/* eslint-disable-next-line @next/next/no-img-element -- a tiny inline capture, nothing to optimise */}
              <img src={f.img} alt={`${domain} after ${seconds(f.t)}`} className="block h-auto w-full rounded-lg" />
            </div>
            <div className="mt-2 font-mono text-sm font-semibold text-foreground">{seconds(f.t)}</div>
          </div>
        ))}
      </div>
      <figcaption className="mt-5 text-center font-mono text-[10px] uppercase leading-relaxed tracking-[0.12em] text-muted-foreground/70">
        {domain} loading in Google&apos;s mobile test &middot; real captures, not a mock-up
      </figcaption>
    </figure>
  )
}

/** Their homepage as it looks today, once loaded - the "before" beside the rebuild. */
