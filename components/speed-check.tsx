'use client'

import { useEffect, useRef, useState, type FormEvent } from 'react'
import Link from 'next/link'
import { ArrowRight, Gauge, Loader2, TriangleAlert } from 'lucide-react'
import { Reveal } from '@/components/reveal'
import { SITE } from '@/lib/site'

/*
 * A real, live speed check - not another illustration. Calls Google's own
 * PageSpeed Insights API (the same tool "ran your site through Google's own
 * speed test" in the cold emails refers to) from the visitor's own browser,
 * for whatever URL they paste in. No server, no stored data: the request
 * goes straight from their browser to Google and the result renders from
 * the response. Scalar's own score is fetched alongside it, the same way,
 * so the comparison is two real numbers, not one real and one claimed.
 */

const OWN_URL = SITE.url
const CACHE_KEY = 'scalar-own-speed-score'
const CACHE_TTL_MS = 6 * 60 * 60 * 1000 // 6 hours - the site rarely changes score-affecting code more often than that

type Score = { score: number; lcp: string; fcp: string }
type Status = 'idle' | 'loading' | 'done' | 'error'

function normalizeUrl(input: string): string | null {
  const trimmed = input.trim()
  if (!trimmed) return null
  const withProtocol = /^https?:\/\//i.test(trimmed) ? trimmed : `https://${trimmed}`
  try {
    const u = new URL(withProtocol)
    if (!u.hostname.includes('.')) return null
    return u.toString()
  } catch {
    return null
  }
}

async function fetchScore(url: string, signal: AbortSignal): Promise<Score> {
  const key = process.env.NEXT_PUBLIC_PAGESPEED_API_KEY
  const params = new URLSearchParams({ url, strategy: 'mobile', category: 'performance' })
  if (key) params.set('key', key)
  const res = await fetch(`https://www.googleapis.com/pagespeedonline/v5/runPagespeed?${params}`, { signal })
  if (!res.ok) {
    if (res.status === 429) throw new Error('rate-limited')
    throw new Error('failed')
  }
  const data = await res.json()
  const perf = data?.lighthouseResult?.categories?.performance?.score
  const lcp = data?.lighthouseResult?.audits?.['largest-contentful-paint']?.displayValue
  const fcp = data?.lighthouseResult?.audits?.['first-contentful-paint']?.displayValue
  if (typeof perf !== 'number') throw new Error('unscorable')
  return { score: Math.round(perf * 100), lcp: lcp ?? '—', fcp: fcp ?? '—' }
}

function readOwnScoreCache(): Score | null {
  try {
    const raw = window.localStorage.getItem(CACHE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as { score: Score; at: number }
    if (Date.now() - parsed.at > CACHE_TTL_MS) return null
    return parsed.score
  } catch {
    return null
  }
}

function writeOwnScoreCache(score: Score) {
  try {
    window.localStorage.setItem(CACHE_KEY, JSON.stringify({ score, at: Date.now() }))
  } catch {}
}

function band(score: number): { label: string; color: string } {
  if (score >= 90) return { label: 'Fast', color: '#4d9be0' } // site blueprint
  if (score >= 50) return { label: 'Needs work', color: '#d9b16a' } // site brass
  return { label: 'Slow', color: '#d0554a' }
}

function Gap({ score, label, sub, highlight }: { score: number; label: string; sub: string; highlight?: boolean }) {
  const b = band(score)
  const r = 42
  const c = 2 * Math.PI * r
  return (
    <div
      className={`flex flex-col items-center gap-3 rounded-2xl border p-6 text-center ${
        highlight ? 'border-blueprint/40 bg-card' : 'border-border bg-card/40'
      }`}
    >
      <div className="relative h-28 w-28">
        <svg viewBox="0 0 100 100" className="h-28 w-28 -rotate-90">
          <circle cx="50" cy="50" r={r} fill="none" stroke="var(--border)" strokeWidth="8" />
          <circle
            cx="50"
            cy="50"
            r={r}
            fill="none"
            stroke={b.color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={c - (score / 100) * c}
            style={{ transition: 'stroke-dashoffset 900ms cubic-bezier(0.16, 1, 0.3, 1)' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="font-mono text-2xl font-bold" style={{ color: b.color }}>
            {score}
          </span>
          <span className="font-mono text-[9px] uppercase tracking-[0.15em] text-muted-foreground">{b.label}</span>
        </div>
      </div>
      <div>
        <p className="text-sm font-semibold text-foreground">{label}</p>
        <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>
      </div>
    </div>
  )
}

export function SpeedCheck({
  linkToFullPage = false,
  initialUrl = '',
}: { linkToFullPage?: boolean; /** Pre-filled on a prospect's preview page */ initialUrl?: string } = {}) {
  const [input, setInput] = useState(initialUrl)
  const [status, setStatus] = useState<Status>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [theirs, setTheirs] = useState<Score | null>(null)
  const [ownScore, setOwnScore] = useState<Score | null>(null)
  const [checkedHost, setCheckedHost] = useState('')
  const [elapsed, setElapsed] = useState(0)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => () => {
    if (timerRef.current) clearInterval(timerRef.current)
  }, [])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    const url = normalizeUrl(input)
    if (!url) {
      setStatus('error')
      setErrorMsg("That doesn't look like a website address — try something like yourbusiness.co.uk.")
      return
    }

    setStatus('loading')
    setErrorMsg('')
    setElapsed(0)
    if (timerRef.current) clearInterval(timerRef.current)
    timerRef.current = setInterval(() => setElapsed((s) => s + 1), 1000)
    const controller = new AbortController()
    // Live testing found 90s still wasn't enough on repeated real runs - a
    // genuine Lighthouse audit's latency on Google's end is highly variable
    // and firing two in parallel (their site + Scalar's own) compounds it.
    // This is purely the browser waiting, no server or quota cost to us, so
    // there's no reason to cut it off early - 3 minutes covers it.
    const timeout = setTimeout(() => controller.abort(), 180_000)

    try {
      const cachedOwn = readOwnScoreCache()
      const [theirScore, ownScoreResult] = await Promise.all([
        fetchScore(url, controller.signal),
        cachedOwn ? Promise.resolve(cachedOwn) : fetchScore(OWN_URL, controller.signal),
      ])
      if (!cachedOwn) writeOwnScoreCache(ownScoreResult)
      setTheirs(theirScore)
      setOwnScore(ownScoreResult)
      setCheckedHost(new URL(url).hostname.replace(/^www\./, ''))
      setStatus('done')
    } catch (err) {
      setStatus('error')
      if (err instanceof Error && err.name === 'AbortError') {
        setErrorMsg("That's taken over 3 minutes without an answer — Google's checker is having real trouble right now. Try again shortly.")
      } else if (err instanceof Error && err.message === 'rate-limited') {
        setErrorMsg("Google's checker is busy right now — give it a minute and try again.")
      } else {
        setErrorMsg("Couldn't check that one — make sure it's a live, public website and try again.")
      }
    } finally {
      clearTimeout(timeout)
      if (timerRef.current) {
        clearInterval(timerRef.current)
        timerRef.current = null
      }
    }
  }

  return (
    <section className="border-t border-border py-24 sm:py-28">
      <div className="mx-auto max-w-4xl px-5 sm:px-8">
        <Reveal className="text-center">
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-card/50 px-4 py-1.5 font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground">
            <Gauge className="h-3.5 w-3.5 text-blueprint" />
            Check your own site
          </span>
          <h2 className="mt-5 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            How fast is your website, really?
          </h2>
          <p className="mx-auto mt-4 max-w-xl text-pretty leading-relaxed text-muted-foreground">
            Paste your site below and I&apos;ll run it through Google&apos;s own speed test, live, right here — the
            same test Google uses to help decide where you rank. No sign-up, nothing stored.
          </p>
          {linkToFullPage && (
            <Link
              href="/speed-test"
              className="mt-3 inline-block text-xs text-muted-foreground underline underline-offset-4 hover:text-blueprint"
            >
              Open this as its own page — worth bookmarking or sharing
            </Link>
          )}
        </Reveal>

        <Reveal className="mt-10">
          <form onSubmit={onSubmit} className="mx-auto flex max-w-lg flex-col gap-3 sm:flex-row">
            <input
              type="text"
              inputMode="url"
              autoCapitalize="off"
              autoCorrect="off"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="yourbusiness.co.uk"
              aria-label="Your website address"
              disabled={status === 'loading'}
              className="w-full rounded-lg border border-border bg-card/60 px-4 py-3.5 font-mono text-sm text-foreground placeholder:text-muted-foreground/70 focus:border-blueprint focus:outline-none disabled:opacity-60"
            />
            <button
              type="submit"
              disabled={status === 'loading'}
              className="btn-chamfer group inline-flex flex-none items-center justify-center gap-2 bg-blueprint px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background disabled:cursor-wait disabled:opacity-80"
            >
              {status === 'loading' ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Checking&hellip;
                </>
              ) : (
                <>
                  Check speed
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </>
              )}
            </button>
          </form>

          {status === 'loading' && (
            <p className="mt-4 text-center font-mono text-xs uppercase tracking-[0.15em] text-muted-foreground">
              Running Google&apos;s real test&hellip; {elapsed}s
              <span className="block normal-case tracking-normal text-muted-foreground/70">
                {elapsed < 20
                  ? 'A genuine Lighthouse audit, not a shortcut — real ones can take a minute or two.'
                  : elapsed < 60
                    ? 'Still going — Google is genuinely measuring the page, not stuck.'
                    : "Taking a while today, but still working — Google's own servers set the pace here, not this site."}
              </span>
            </p>
          )}

          {status === 'error' && (
            <p className="mt-4 flex items-center justify-center gap-2 text-center text-sm text-muted-foreground">
              <TriangleAlert className="h-4 w-4 flex-none text-brass" />
              {errorMsg}
            </p>
          )}
        </Reveal>

        {status === 'done' && theirs && ownScore && (
          <Reveal className="mt-12">
            <div className="grid gap-5 sm:grid-cols-2">
              <Gap score={theirs.score} label={checkedHost} sub={`LCP ${theirs.lcp} · FCP ${theirs.fcp}`} />
              <Gap score={ownScore.score} label="scalardigital.co.uk" sub={`LCP ${ownScore.lcp} · FCP ${ownScore.fcp}`} highlight />
            </div>

            <p className="mt-6 text-center text-xs text-muted-foreground">
              Live results from{' '}
              <a
                href="https://pagespeed.web.dev/"
                target="_blank"
                rel="noreferrer"
                className="underline underline-offset-4 hover:text-blueprint"
              >
                Google PageSpeed Insights
              </a>
              , run in your browser just now. Scores can vary slightly between runs.
            </p>

            {theirs.score < 90 && (
              <div className="mx-auto mt-8 flex max-w-lg flex-col items-center gap-4 rounded-2xl border border-blueprint/40 bg-card p-7 text-center">
                <p className="text-pretty leading-relaxed text-foreground/90">
                  That gap is real customers leaving before your site finishes loading. A Scalar build is
                  hand-coded to score like the one on the right.
                </p>
                <Link
                  href="/contact"
                  className="btn-chamfer group inline-flex items-center justify-center gap-2 bg-blueprint px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background"
                >
                  Fix it — start your build
                  <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                </Link>
              </div>
            )}
          </Reveal>
        )}
      </div>
    </section>
  )
}
