'use client'

import Link from 'next/link'
import { useMemo, useState } from 'react'
import { Minus, Plus } from 'lucide-react'
import { Reveal } from '@/components/reveal'

const TIERS = {
  landing: { label: 'Landing page', price: 750, pages: 1 },
  build: { label: 'Full build', price: 2500, pages: 5 },
} as const

type TierKey = keyof typeof TIERS

const PRICE_PER_EXTRA_PAGE = 150
const PRICE_PER_SERVICE_AREA = 120

const FEATURES = [
  { key: 'booking', label: 'Online booking / enquiry calendar', price: 300 },
  { key: 'gallery', label: 'Photo gallery with before/after slider', price: 200 },
  { key: 'blog', label: 'Blog or news section', price: 250 },
] as const

type FeatureKey = (typeof FEATURES)[number]['key']

const gbp = (n: number) => `£${n.toLocaleString('en-GB')}`

export function CostCalculator() {
  const [tier, setTier] = useState<TierKey>('build')
  const [extraPages, setExtraPages] = useState(0)
  const [serviceAreas, setServiceAreas] = useState(0)
  const [features, setFeatures] = useState<Record<FeatureKey, boolean>>({
    booking: false,
    gallery: false,
    blog: false,
  })

  const basePrice = TIERS[tier].price
  const basePages = TIERS[tier].pages

  const total = useMemo(() => {
    let sum = basePrice
    sum += extraPages * PRICE_PER_EXTRA_PAGE
    sum += serviceAreas * PRICE_PER_SERVICE_AREA
    FEATURES.forEach((f) => {
      if (features[f.key]) sum += f.price
    })
    return sum
  }, [basePrice, extraPages, serviceAreas, features])

  const contactHref = `/contact?budget=${encodeURIComponent(nearestBand(total))}&estimate=${total}`

  return (
    <section id="estimate" className="scroll-mt-24 border-t border-border py-24 sm:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal className="max-w-2xl">
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Instant estimate</span>
          <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            What would your site actually cost?
          </h2>
          <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
            A rough guide, not a quote — the real number is agreed and fixed before a line of code is written.
          </p>
        </Reveal>

        <div className="mt-12 grid gap-8 lg:grid-cols-[1.2fr_1fr] lg:gap-12">
          <Reveal className="space-y-8">
            <div>
              <div className="mb-3 font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                Starting point
              </div>
              <div className="grid grid-cols-2 gap-3">
                {(Object.keys(TIERS) as TierKey[]).map((key) => {
                  const t = TIERS[key]
                  const active = tier === key
                  return (
                    <button
                      key={key}
                      type="button"
                      onClick={() => setTier(key)}
                      className={`rounded-lg border px-4 py-3.5 text-left transition-colors ${
                        active
                          ? 'border-blueprint bg-blueprint/[0.08]'
                          : 'border-border bg-card/40 hover:border-blueprint/40'
                      }`}
                    >
                      <div className="text-sm font-medium text-foreground">{t.label}</div>
                      <div className="mt-0.5 font-mono text-xs text-muted-foreground">
                        {gbp(t.price)} · {t.pages} page{t.pages > 1 ? 's' : ''}
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            <Stepper
              label={`Extra pages beyond the first ${basePages}`}
              hint={`${gbp(PRICE_PER_EXTRA_PAGE)} each`}
              value={extraPages}
              onChange={setExtraPages}
              max={10}
            />
            <Stepper
              label="Extra towns / service areas covered"
              hint={`${gbp(PRICE_PER_SERVICE_AREA)} each`}
              value={serviceAreas}
              onChange={setServiceAreas}
              max={6}
            />

            <div>
              <div className="mb-3 font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                Extras
              </div>
              <div className="space-y-2.5">
                {FEATURES.map((f) => (
                  <label
                    key={f.key}
                    className="flex cursor-pointer items-center justify-between gap-4 rounded-lg border border-border bg-card/40 px-4 py-3.5 transition-colors hover:border-blueprint/40"
                  >
                    <span className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        checked={features[f.key]}
                        onChange={(e) => setFeatures((prev) => ({ ...prev, [f.key]: e.target.checked }))}
                        className="h-4 w-4 accent-[var(--blueprint)]"
                      />
                      <span className="text-sm text-foreground">{f.label}</span>
                    </span>
                    <span className="font-mono text-xs text-muted-foreground">+{gbp(f.price)}</span>
                  </label>
                ))}
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="sticky top-24 rounded-2xl border border-blueprint/40 bg-card p-8">
              <span className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">
                Estimated build
              </span>
              <div className="mt-3 flex items-end gap-2">
                <span className="text-5xl font-bold tracking-tight">{gbp(total)}</span>
              </div>
              <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                One-off. No monthly rental, no hidden extras once we agree the number.
              </p>
              <div className="my-6 h-px w-full bg-border" />
              <dl className="space-y-2 text-sm">
                <Row label={`${TIERS[tier].label} — ${basePages} page${basePages > 1 ? 's' : ''}`} value={gbp(basePrice)} />
                {extraPages > 0 && (
                  <Row label={`${extraPages} extra page${extraPages > 1 ? 's' : ''}`} value={`+${gbp(extraPages * PRICE_PER_EXTRA_PAGE)}`} />
                )}
                {serviceAreas > 0 && (
                  <Row
                    label={`${serviceAreas} extra service area${serviceAreas > 1 ? 's' : ''}`}
                    value={`+${gbp(serviceAreas * PRICE_PER_SERVICE_AREA)}`}
                  />
                )}
                {FEATURES.filter((f) => features[f.key]).map((f) => (
                  <Row key={f.key} label={f.label} value={`+${gbp(f.price)}`} />
                ))}
              </dl>
              <Link
                href={contactHref}
                className="btn-chamfer group mt-8 inline-flex w-full items-center justify-center gap-2 bg-blueprint px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background"
              >
                Get the real number
                <span className="transition-transform group-hover:translate-x-1">&rarr;</span>
              </Link>
            </div>
          </Reveal>
        </div>
      </div>
    </section>
  )
}

function nearestBand(total: number) {
  if (total < 1500) return '£750 – £1,500'
  if (total < 2500) return '£1,500 – £2,500'
  if (total < 4000) return '£2,500 – £4,000'
  return '£4,000+'
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="shrink-0 font-mono text-foreground">{value}</dd>
    </div>
  )
}

function Stepper({
  label,
  hint,
  value,
  onChange,
  max,
}: {
  label: string
  hint: string
  value: number
  onChange: (updater: (v: number) => number) => void
  max: number
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg border border-border bg-card/40 px-4 py-3.5">
      <div>
        <div className="text-sm text-foreground">{label}</div>
        <div className="mt-0.5 font-mono text-[11px] uppercase tracking-[0.15em] text-muted-foreground">{hint}</div>
      </div>
      <div className="flex shrink-0 items-center gap-3">
        <button
          type="button"
          aria-label={`Decrease ${label}`}
          onClick={() => onChange((v) => Math.max(0, v - 1))}
          disabled={value === 0}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-foreground transition-colors hover:border-blueprint disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Minus className="h-3.5 w-3.5" />
        </button>
        <span className="w-4 text-center font-mono text-sm tabular-nums">{value}</span>
        <button
          type="button"
          aria-label={`Increase ${label}`}
          onClick={() => onChange((v) => Math.min(max, v + 1))}
          disabled={value === max}
          className="flex h-8 w-8 items-center justify-center rounded-md border border-border text-foreground transition-colors hover:border-blueprint disabled:cursor-not-allowed disabled:opacity-40"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}
