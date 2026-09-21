'use client'

import Script from 'next/script'
import { useEffect, useState } from 'react'

const GA_ID = 'G-6N9HXJFC90'
const KEY = 'scalar-analytics-consent'

type Gtag = (...args: unknown[]) => void

function readChoice(): 'granted' | 'denied' | null {
  try {
    const v = window.localStorage.getItem(KEY)
    return v === 'granted' || v === 'denied' ? v : null
  } catch {
    return null
  }
}

// Google Analytics 4, loaded with consent denied by default. No analytics cookies are set
// until the visitor accepts (UK PECR), and the choice is remembered on their device only.
export function GoogleAnalytics() {
  const [asked, setAsked] = useState(true)

  useEffect(() => {
    const choice = readChoice()
    if (choice === null) {
      setAsked(false)
    } else if (choice === 'granted') {
      const gtag = (window as unknown as { gtag?: Gtag }).gtag
      gtag?.('consent', 'update', { analytics_storage: 'granted' })
    }
  }, [])

  function choose(value: 'granted' | 'denied') {
    try {
      window.localStorage.setItem(KEY, value)
    } catch {}
    const gtag = (window as unknown as { gtag?: Gtag }).gtag
    gtag?.('consent', 'update', { analytics_storage: value })
    setAsked(true)
  }

  return (
    <>
      <Script src={`https://www.googletagmanager.com/gtag/js?id=${GA_ID}`} strategy="afterInteractive" />
      <Script id="ga4-init" strategy="afterInteractive">
        {`window.dataLayer = window.dataLayer || [];
function gtag(){dataLayer.push(arguments);}
window.gtag = gtag;
gtag('consent', 'default', { analytics_storage: 'denied', ad_storage: 'denied', ad_user_data: 'denied', ad_personalization: 'denied' });
gtag('js', new Date());
gtag('config', '${GA_ID}');`}
      </Script>

      {!asked && (
        <div
          role="dialog"
          aria-label="Analytics cookies"
          className="fixed bottom-4 left-4 right-4 z-[60] max-w-sm rounded-xl border border-border bg-card/95 p-4 text-sm shadow-2xl backdrop-blur-xl sm:right-auto"
        >
          <p className="leading-relaxed text-foreground/90">
            I&apos;d like to use Google Analytics cookies to see which pages help people. Nothing is set unless you
            accept.{' '}
            <a href="/privacy#cookies" className="text-blueprint underline-offset-4 hover:underline">
              Details
            </a>
          </p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() => choose('granted')}
              className="flex-1 rounded-md border border-border px-3 py-2 font-mono text-xs uppercase tracking-[0.12em] text-foreground transition-colors hover:border-blueprint hover:text-blueprint"
            >
              Accept
            </button>
            <button
              type="button"
              onClick={() => choose('denied')}
              className="flex-1 rounded-md border border-border px-3 py-2 font-mono text-xs uppercase tracking-[0.12em] text-foreground transition-colors hover:border-blueprint hover:text-blueprint"
            >
              Decline
            </button>
          </div>
        </div>
      )}
    </>
  )
}
