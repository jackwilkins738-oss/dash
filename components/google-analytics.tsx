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
        // A slim bar pinned to the bottom edge rather than a floating card.
        // The card was ~140px tall sitting over the bottom-left of the
        // viewport, which on this site meant it covered the hero's CTA row
        // and then a heading or a paragraph of body copy on every section
        // as you scrolled - it stays until it's answered, so that's the
        // whole first visit. A full-width strip reads as browser chrome,
        // costs ~56px, and covers no column of text.
        //
        // pr-20/sm:pr-28 keeps the buttons clear of the WhatsApp button,
        // which is fixed at bottom-right and sits on top of this bar.
        <div
          role="dialog"
          aria-label="Analytics cookies"
          className="fixed inset-x-0 bottom-0 z-[60] border-t border-border bg-card/95 backdrop-blur-xl"
        >
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-5 py-2.5 pr-16 text-xs leading-snug sm:gap-6 sm:px-8 sm:pr-28 sm:text-sm">
            {/* Short form on phones. Beside the buttons there is only about
                130px of column left, and the full sentence wrapped to four
                lines - a 138px bar, taller than the card this replaced. */}
            <p className="leading-snug text-foreground/90">
              <span className="sm:hidden">Analytics cookies? Nothing is set unless you accept.</span>
              <span className="hidden sm:inline">
                I&apos;d like to use Google Analytics cookies to see which pages help people. Nothing is set
                unless you accept.
              </span>{' '}
              <a href="/privacy#cookies" className="text-blueprint underline-offset-4 hover:underline">
                Details
              </a>
            </p>
            <div className="flex shrink-0 gap-2">
              <button
                type="button"
                onClick={() => choose('granted')}
                className="btn-chamfer-sm border border-blueprint/40 bg-blueprint/10 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-foreground transition-colors hover:border-blueprint hover:text-blueprint sm:px-4 sm:py-2 sm:text-xs"
              >
                Accept
              </button>
              <button
                type="button"
                onClick={() => choose('denied')}
                className="btn-chamfer-sm border border-border px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-foreground transition-colors hover:border-blueprint hover:text-blueprint sm:px-4 sm:py-2 sm:text-xs"
              >
                Decline
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
