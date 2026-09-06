import { Reveal } from '@/components/reveal'

const SPECS = [
  { k: 'Time to dead lead', v: 'Under 24 hours, unanswered' },
  { k: 'Time to reply here', v: 'Under 2 hours, every time' },
  { k: 'What that’s worth', v: 'The job that would’ve gone elsewhere' },
]

export function BrokenWire() {
  return (
    <section className="relative overflow-hidden border-y border-border py-24 sm:py-32">
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-5 sm:px-8 lg:grid-cols-2 lg:gap-14">
        <Reveal>
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">
            It&apos;s called a lead for a reason
          </span>
          <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Cut the wire and it&apos;s dead in seconds. Same with an enquiry.
          </h2>
          <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
            A lead that sits unanswered for a day is a lead that&apos;s already gone cold. Every site I build gets
            your enquiries to you the second they land — because the difference between a live wire and a dead one
            is exactly how fast someone gets to it.
          </p>

          <dl className="mt-10 space-y-4 border-t border-border pt-8">
            {SPECS.map((s) => (
              <div key={s.k} className="flex items-baseline justify-between gap-4">
                <dt className="font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground">{s.k}</dt>
                <dd className="text-right text-sm text-foreground">{s.v}</dd>
              </div>
            ))}
          </dl>
        </Reveal>

        <div className="relative order-first flex h-[360px] w-full items-center justify-center sm:h-[460px] lg:order-last lg:h-[520px]">
          <svg viewBox="0 0 300 400" className="h-full max-w-full" fill="none" strokeLinecap="round">
            <defs>
              <filter id="spark-glow" x="-100%" y="-100%" width="300%" height="300%">
                <feGaussianBlur stdDeviation="4" result="blur" />
                <feMerge>
                  <feMergeNode in="blur" />
                  <feMergeNode in="SourceGraphic" />
                </feMerge>
              </filter>
            </defs>

            {/* Cable insulation - bottom run into the break, dim/dead */}
            <path
              d="M60 390 L90 340 L70 300 L140 260 L112 232"
              stroke="#1a3a5c"
              strokeWidth="16"
              strokeLinejoin="round"
              opacity="0.6"
            />
            <path
              d="M60 390 L90 340 L70 300 L140 260 L112 232"
              stroke="#4d84c4"
              strokeWidth="9"
              strokeLinejoin="round"
              opacity="0.35"
            />

            {/* Cable insulation - top run out of the break, live */}
            <path
              d="M170 190 L200 160 L180 120 L230 90 L210 50 L240 30"
              stroke="#1a3a5c"
              strokeWidth="16"
              strokeLinejoin="round"
            />
            <path
              d="M170 190 L200 160 L180 120 L230 90 L210 50 L240 30"
              stroke="#4d84c4"
              strokeWidth="9"
              strokeLinejoin="round"
            />

            {/* Exposed copper strands bridging the break, frayed */}
            <g stroke="#c9a15a" strokeWidth="1.6" opacity="0.9">
              <path d="M112 232 Q128 218 142 214 Q156 210 170 190" />
              <path d="M110 226 Q126 210 138 206 Q152 200 168 184" />
              <path d="M116 240 Q132 228 146 222 Q158 216 172 198" />
            </g>

            {/* The spark - flashes across the break */}
            <g className="wire-spark" filter="url(#spark-glow)">
              <circle cx="141" cy="212" r="5" fill="#fff7e6" />
              <path
                d="M141 212 L131 200 M141 212 L152 198 M141 212 L127 218 M141 212 L154 222"
                stroke="#fff7e6"
                strokeWidth="2"
              />
            </g>
          </svg>
        </div>
      </div>
    </section>
  )
}
