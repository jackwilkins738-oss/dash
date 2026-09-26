'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'

// Phones only. Once the hero - and its own buttons - have scrolled away, the
// next step stays under the thumb instead of 12,000px back up the page. It
// replaces the floating WhatsApp bubble below `sm` (see whatsapp-button.tsx)
// rather than stacking a second fixed thing on top of it.
//
// It steps aside again whenever the page is already asking for the same
// action in-line - the closing CTA band and the footer - so there are never
// two identical asks on screen at once.
export function MobileActionBar() {
  const pathname = usePathname()
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    let pastHero = false
    let ctaInView = false
    const update = () => setVisible(pastHero && !ctaInView)

    const onScroll = () => {
      const next = window.scrollY > window.innerHeight * 0.85
      if (next !== pastHero) {
        pastHero = next
        update()
      }
    }

    const inView = new Set<Element>()
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        if (e.isIntersecting) inView.add(e.target)
        else inView.delete(e.target)
      }
      ctaInView = inView.size > 0
      update()
    })
    document.querySelectorAll('[data-hide-action-bar], footer').forEach((el) => io.observe(el))

    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => {
      io.disconnect()
      window.removeEventListener('scroll', onScroll)
    }
  }, [pathname])

  if (pathname === '/contact') return null

  return (
    <div
      className={`mab fixed inset-x-0 bottom-0 z-40 border-t border-border bg-background/85 px-4 pt-3 backdrop-blur-md sm:hidden ${
        visible ? 'mab-in' : ''
      }`}
      style={{ paddingBottom: 'max(0.75rem, env(safe-area-inset-bottom))' }}
      aria-hidden={!visible}
      inert={!visible}
    >
      <div className="flex items-center gap-2.5">
        <Link
          href="/contact"
          className="btn-chamfer flex flex-1 items-center justify-center gap-2 bg-blueprint px-5 py-3 font-mono text-xs font-semibold uppercase tracking-[0.15em] text-primary-foreground"
        >
          Start your build <span aria-hidden="true">&rarr;</span>
        </Link>
        <a
          href="https://wa.me/66638306449"
          target="_blank"
          rel="noopener noreferrer"
          aria-label="Message on WhatsApp"
          className="btn-chamfer flex h-[42px] w-12 flex-none items-center justify-center bg-[#25D366]"
        >
          <svg viewBox="0 0 24 24" className="h-5 w-5 text-white" fill="currentColor" aria-hidden="true">
            <path d="M12.001 2C6.478 2 2 6.477 2 12c0 1.99.582 3.845 1.588 5.404L2 22l4.71-1.554A9.953 9.953 0 0 0 12.001 22C17.523 22 22 17.523 22 12S17.523 2 12.001 2zm0 18.2a8.174 8.174 0 0 1-4.415-1.29l-.317-.19-3.03 1.001.999-2.995-.207-.318A8.166 8.166 0 0 1 3.8 12c0-4.529 3.672-8.2 8.201-8.2 4.529 0 8.199 3.671 8.199 8.2 0 4.528-3.67 8.2-8.199 8.2zm4.49-6.1c-.246-.123-1.453-.717-1.678-.8-.225-.082-.389-.123-.553.124-.164.246-.635.8-.778.964-.143.164-.287.185-.533.062-.246-.123-1.038-.383-1.977-1.22-.73-.652-1.224-1.457-1.367-1.703-.143-.246-.015-.379.108-.501.11-.11.246-.287.369-.43.123-.144.164-.246.246-.41.082-.164.041-.308-.02-.43-.062-.124-.554-1.334-.758-1.826-.2-.479-.403-.414-.553-.422l-.472-.008a.905.905 0 0 0-.656.308c-.225.246-.86.84-.86 2.05 0 1.209.88 2.377 1.003 2.541.123.164 1.733 2.646 4.198 3.71.587.253 1.044.404 1.4.517.589.187 1.124.16 1.548.098.472-.07 1.453-.594 1.658-1.168.205-.574.205-1.066.143-1.168-.061-.103-.225-.164-.471-.287z" />
          </svg>
        </a>
      </div>
    </div>
  )
}
