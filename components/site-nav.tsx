'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

const links = [
  { href: '/', label: 'Home' },
  { href: '/work', label: 'Services & Pricing' },
  { href: '/contact', label: 'Contact' },
]

export function SiteNav() {
  const pathname = usePathname()
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  useEffect(() => {
    setOpen(false)
  }, [pathname])

  return (
    <header
      className={cn(
        'fixed inset-x-0 top-0 z-50 transition-colors duration-300',
        scrolled || open
          ? 'border-b border-border bg-background/80 backdrop-blur-xl'
          : 'border-b border-transparent bg-transparent',
      )}
    >
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
        <Link href="/" className="font-mono text-lg font-bold tracking-tight" aria-label="Scalar Digital home">
          S<span className="text-blueprint">·</span>D
          <span className="ml-2 hidden align-middle font-sans text-xs font-medium uppercase tracking-[0.25em] text-muted-foreground sm:inline">
            Scalar
          </span>
        </Link>

        <div className="hidden items-center gap-8 md:flex">
          {links.map((l) => (
            <Link
              key={l.href}
              href={l.href}
              className={cn(
                'font-mono text-xs uppercase tracking-[0.15em] transition-colors',
                pathname === l.href ? 'text-foreground' : 'text-muted-foreground hover:text-foreground',
              )}
            >
              {l.label}
            </Link>
          ))}
          <Link
            href="/contact"
            className="group relative inline-flex items-center gap-2 rounded-full bg-blueprint px-5 py-2 font-mono text-xs font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-transform hover:scale-[1.03]"
          >
            Start your build
            <span className="transition-transform group-hover:translate-x-0.5">&rarr;</span>
          </Link>
        </div>

        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex h-10 w-10 items-center justify-center rounded-md border border-border md:hidden"
          aria-label="Toggle menu"
          aria-expanded={open}
        >
          <div className="flex flex-col gap-1.5">
            <span className={cn('h-px w-5 bg-foreground transition-transform', open && 'translate-y-[3px] rotate-45')} />
            <span className={cn('h-px w-5 bg-foreground transition-transform', open && '-translate-y-[3px] -rotate-45')} />
          </div>
        </button>
      </nav>

      {open && (
        <div className="border-t border-border md:hidden">
          <div className="mx-auto flex max-w-6xl flex-col gap-1 px-5 py-4 sm:px-8">
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={cn(
                  'rounded-md px-3 py-3 font-mono text-sm uppercase tracking-[0.15em]',
                  pathname === l.href ? 'bg-secondary text-foreground' : 'text-muted-foreground',
                )}
              >
                {l.label}
              </Link>
            ))}
            <Link
              href="/contact"
              className="mt-2 inline-flex items-center justify-center rounded-full bg-blueprint px-5 py-3 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground"
            >
              Start your build &rarr;
            </Link>
          </div>
        </div>
      )}
    </header>
  )
}
