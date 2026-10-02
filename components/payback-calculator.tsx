'use client'

import Link from 'next/link'
import { useState } from 'react'
import { PRICES } from '@/lib/site'
import { payback } from '@/lib/payback'

const gbp = (n: number) => `${n < 0 ? '-' : ''}£${Math.abs(Math.round(n)).toLocaleString('en-GB')}`

const PACKAGES = [
  { key: 'landing', label: 'Landing page', price: PRICES.landing },
  { key: 'build', label: 'Full build', price: PRICES.build },
] as const

// Their own numbers in, the plain sum out. Deliberately no claim about how
// many jobs a website brings: the visitor sets that, starting low.
export function PaybackCalculator() {
  const [jobValue, setJobValue] = useState(3000)
  const [margin, setMargin] = useState(25)
  const [jobs, setJobs] = useState(2)
  const [pkg, setPkg] = useState<(typeof PACKAGES)[number]['key']>('build')
  const price = PACKAGES.find((p) => p.key === pkg)!.price
  const r = payback({ jobValue, marginPercent: margin, extraJobsPerYear: jobs, sitePrice: price })

  return (
    <div className="mt-8 grid gap-6 rounded-2xl border border-border bg-card/40 p-6 sm:p-8 lg:grid-cols-[1.1fr_1fr]">
      <div className="space-y-6">
        <Field label="Your average job" suffix="£" value={jobValue} onChange={setJobValue} step={250} max={100000} />
        <Field label="Profit on a job, after materials and labour" suffix="%" value={margin} onChange={setMargin} step={5} max={90} />
        <Field label="Extra jobs a year from the website" value={jobs} onChange={setJobs} step={1} max={50} />
        <div>
          <div className="mb-2 font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">The site</div>
          <div className="grid grid-cols-2 gap-3">
            {PACKAGES.map((p) => (
              <button
                key={p.key}
                type="button"
                onClick={() => setPkg(p.key)}
                aria-pressed={pkg === p.key}
                className={`rounded-lg border px-4 py-3 text-left transition-colors ${
                  pkg === p.key ? 'border-blueprint bg-blueprint/[0.08]' : 'border-border hover:border-blueprint/40'
                }`}
              >
                <div className="text-sm font-medium text-foreground">{p.label}</div>
                <div className="mt-0.5 font-mono text-xs text-muted-foreground">{gbp(p.price)} one-off</div>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="rounded-2xl border border-blueprint/40 bg-card p-6 sm:p-7" aria-live="polite">
        <span className="font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground">Pays for itself after</span>
        <div className="mt-2 text-5xl font-bold tracking-tight">
          {r.jobsToPayBack === null ? '—' : `${r.jobsToPayBack} job${r.jobsToPayBack === 1 ? '' : 's'}`}
        </div>
        <dl className="mt-6 space-y-2 text-sm">
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">Profit on each job</dt>
            <dd className="font-mono text-foreground">{gbp(r.profitPerJob)}</dd>
          </div>
          <div className="flex justify-between gap-4">
            <dt className="text-muted-foreground">First year, after paying for the site</dt>
            <dd className={`font-mono ${r.firstYear >= 0 ? 'text-foreground' : 'text-muted-foreground'}`}>{gbp(r.firstYear)}</dd>
          </div>
        </dl>
        <p className="mt-5 text-xs leading-relaxed text-muted-foreground">
          Your numbers, not a promise: no one can honestly tell you how many jobs a website will bring. The price is
          one-off, so once it&apos;s covered every job the site brings is profit. With the full build, the dashboard is
          free for 12 months, then £{PRICES.dashboardMonthly} a month if you keep it.
        </p>
        <Link
          href="/work#pricing"
          className="mt-5 inline-block font-mono text-xs font-semibold uppercase tracking-[0.15em] text-blueprint underline underline-offset-4"
        >
          See what each option includes
        </Link>
      </div>
    </div>
  )
}

function Field({
  label,
  suffix,
  value,
  onChange,
  step,
  max,
}: {
  label: string
  suffix?: string
  value: number
  onChange: (n: number) => void
  step: number
  max: number
}) {
  return (
    <label className="block">
      <span className="mb-2 block font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">{label}</span>
      <span className="flex items-center gap-2 rounded-lg border border-border bg-background px-4 py-3 focus-within:border-blueprint">
        {suffix === '£' && <span className="font-mono text-muted-foreground">£</span>}
        <input
          type="number"
          inputMode="numeric"
          min={0}
          max={max}
          step={step}
          value={Number.isFinite(value) ? value : ''}
          onChange={(e) => onChange(e.target.value === '' ? 0 : Math.min(max, Math.max(0, Number(e.target.value))))}
          className="w-full bg-transparent font-mono text-lg text-foreground outline-none"
        />
        {suffix === '%' && <span className="font-mono text-muted-foreground">%</span>}
      </span>
    </label>
  )
}
