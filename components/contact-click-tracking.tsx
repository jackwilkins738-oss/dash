'use client'

import { useEffect } from 'react'
import { track } from '@vercel/analytics'

type Gtag = (...args: unknown[]) => void

// Most trades ring or WhatsApp rather than fill in a form, so a tap on any
// tel:, WhatsApp, mailto: or booking (cal.com) link is counted as a conversion - otherwise the
// analytics only ever see the minority who use the contact form, and there's
// no telling which pages actually bring enquiries in.
//
// One listener on the document covers every such link on every page (nav,
// footer, floating button, mobile bar, preview pages) without touching each
// component. Vercel Analytics is cookieless; the GA event only goes anywhere
// if the visitor accepted analytics cookies (consent mode drops it otherwise).
// Nothing personal is sent: the kind of link and the page it was on.
export function ContactClickTracking() {
  useEffect(() => {
    function onClick(e: MouseEvent) {
      const link = (e.target as Element | null)?.closest?.('a[href]') as HTMLAnchorElement | null
      if (!link) return
      const href = link.getAttribute('href') ?? ''
      const kind = href.startsWith('tel:')
        ? 'call'
        : /(^|\/\/)(wa\.me|api\.whatsapp\.com)\//.test(href)
          ? 'whatsapp'
          : href.startsWith('mailto:')
            ? 'email'
            : /(^|\/\/)cal\.com\//.test(href)
              ? 'book_call'
              : null
      if (!kind) return
      // Preview pages are grouped under /for, so one prospect's page doesn't become its own row.
      const page = window.location.pathname.startsWith('/for/') ? '/for/[prospect]' : window.location.pathname
      track(`${kind}_click`, { page })
      const gtag = (window as unknown as { gtag?: Gtag }).gtag
      gtag?.('event', `${kind}_click`, { page_path: page })
    }
    document.addEventListener('click', onClick, { capture: true })
    return () => document.removeEventListener('click', onClick, { capture: true })
  }, [])
  return null
}
