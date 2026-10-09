'use client'

import { useEffect, useState } from 'react'
import { Phone, MessageCircle, X } from 'lucide-react'
import { SITE } from '@/lib/site'

// The one-tap reply, pinned to the bottom of the preview. Viewers typically
// leave about a third of the way down, before they ever reach the reply
// section, so the ask comes to them: it appears once they start scrolling,
// steps aside while the full reply section is on screen, and goes for good
// after a choice or a close. Same endpoint as QuickReply.
export function StickyReply({ slug, firmName }: { slug: string; firmName: string }) {
  const [scrolled, setScrolled] = useState(false)
  const [replyInView, setReplyInView] = useState(false)
  const [state, setState] = useState<'open' | 'rang' | 'closed'>('open')

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 400)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    const reply = document.getElementById('reply')
    const io = reply ? new IntersectionObserver(([e]) => setReplyInView(e.isIntersecting), { threshold: 0.2 }) : null
    if (reply && io) io.observe(reply)
    return () => {
      window.removeEventListener('scroll', onScroll)
      io?.disconnect()
    }
  }, [])

  const send = (choice: 'call' | 'whatsapp') => {
    void fetch('/api/preview-choice', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ slug, choice, phone: '' }),
      keepalive: true,
    }).catch(() => {})
  }

  if (state === 'closed' || !scrolled || (replyInView && state === 'open')) return null
  const whatsapp = `${SITE.whatsapp}?text=${encodeURIComponent(`Hi, it's ${firmName} - I've seen the website preview you made for us.`)}`

  return (
    <div data-print="hide" className="fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/95 px-4 py-3 shadow-[0_-8px_30px_rgba(0,0,0,0.12)] backdrop-blur">
      <div className="mx-auto flex max-w-3xl items-center gap-3">
        {state === 'rang' ? (
          <p className="flex-1 text-sm font-semibold" role="status">
            Thanks - I&apos;ll ring you shortly on the number on your website.
          </p>
        ) : (
          <>
            <p className="hidden flex-1 text-sm font-semibold sm:block">Like it? One tap and I&apos;ll take it from there.</p>
            <button
              type="button"
              onClick={() => {
                send('call')
                setState('rang')
              }}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-blueprint px-4 py-3 text-sm font-semibold text-white hover:bg-brass sm:flex-none"
            >
              <Phone className="h-4 w-4" aria-hidden />
              Yes, ring me
            </button>
            <a
              href={whatsapp}
              target="_blank"
              rel="noopener"
              onClick={() => send('whatsapp')}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl border border-border px-4 py-3 text-sm font-semibold hover:border-blueprint sm:flex-none"
            >
              <MessageCircle className="h-4 w-4" aria-hidden />
              WhatsApp
            </a>
          </>
        )}
        <button type="button" onClick={() => setState('closed')} aria-label="Close" className="p-2 text-muted-foreground hover:text-foreground">
          <X className="h-4 w-4" aria-hidden />
        </button>
      </div>
    </div>
  )
}
