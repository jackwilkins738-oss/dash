import Link from 'next/link'
import { ArrowUp, ArrowUpRight, BadgeCheck, Code2, KeyRound, Mail, MessageCircle, Phone, Tag } from 'lucide-react'

const WHATSAPP = 'https://wa.me/66638306449'
const LINKEDIN = 'https://www.linkedin.com/in/scalar-digital-868841438/'

const linkClass = 'text-sm text-foreground/75 transition-colors hover:text-blueprint'
const headingClass = 'font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground'

const SERVICES = [
  { href: '/work#pricing', label: 'Landing page', note: 'from £750' },
  { href: '/work#pricing', label: 'The Scalar build', note: '£2,500' },
  { href: '/#dash', label: 'Client dashboard', note: 'included' },
  { href: '/work#estimate', label: 'Price estimator', note: '' },
]

const COMPANY = [
  { href: '/', label: 'Home' },
  { href: '/work', label: 'Services & Pricing' },
  { href: '/process', label: 'Process' },
  { href: '/refer', label: 'Refer & save 15%' },
  { href: '/contact', label: 'Contact' },
  { href: '/privacy', label: 'Privacy Policy' },
]

const PRINCIPLES = [
  { icon: Code2, label: 'Hand-coded' },
  { icon: Tag, label: 'Fixed prices' },
  { icon: KeyRound, label: 'You own the site' },
  { icon: BadgeCheck, label: 'Est. 2026' },
]

export function SiteFooter() {
  return (
    <footer className="relative overflow-hidden border-t border-border bg-card/30">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px"
        style={{ background: 'linear-gradient(90deg, transparent, oklch(0.62 0.135 244 / 0.7), transparent)' }}
        aria-hidden="true"
      />

      <div className="mx-auto max-w-6xl px-5 pt-16 sm:px-8 sm:pt-20">
        {/* Call to action */}
        <div className="relative overflow-hidden rounded-2xl border border-blueprint/30 bg-card/60 p-8 sm:p-10">
          <div
            className="pointer-events-none absolute inset-0"
            style={{
              background:
                'radial-gradient(70% 120% at 100% 0%, oklch(0.62 0.135 244 / 0.16), transparent 60%), radial-gradient(50% 100% at 0% 100%, oklch(0.78 0.1 80 / 0.07), transparent 60%)',
            }}
            aria-hidden="true"
          />
          <div className="relative flex flex-col gap-8 lg:flex-row lg:items-center lg:justify-between">
            <div className="max-w-xl">
              <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Ready when you are</span>
              <h2 className="mt-3 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl">
                A site that wins the jobs worth having.
              </h2>
              <p className="mt-3 text-pretty text-sm leading-relaxed text-muted-foreground sm:text-base">
                Tell me about your business and what you need. You get a fixed price before a line of code is written.
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row lg:flex-none">
              <Link
                href="/contact"
                className="group btn-chamfer inline-flex items-center justify-center gap-2 bg-blueprint px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background"
              >
                Start your build
                <ArrowUpRight className="h-4 w-4 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5" />
              </Link>
              <a
                href={WHATSAPP}
                target="_blank"
                rel="noopener noreferrer"
                className="btn-chamfer inline-flex items-center justify-center gap-2 border border-border px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-foreground transition-colors hover:border-blueprint hover:text-blueprint"
              >
                <MessageCircle className="h-4 w-4" />
                WhatsApp
              </a>
            </div>
          </div>
        </div>

        {/* Main grid */}
        <div className="grid gap-12 py-14 lg:grid-cols-12">
          <div className="lg:col-span-4">
            <div className="flex items-center gap-4">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src="/brand/crest-88.png"
                alt=""
                width={56}
                height={56}
                loading="lazy"
                className="h-14 w-14 rounded-full"
              />
              <div>
                <div className="font-mono text-lg font-bold tracking-tight">
                  S<span className="text-blueprint">·</span>D
                </div>
                <div className="font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground">
                  Scalar Digital
                </div>
              </div>
            </div>
            <p className="mt-5 max-w-sm text-sm leading-relaxed text-muted-foreground">
              Hand-coded websites for trades who take their work seriously. Built to load fast, rank locally and win
              the jobs worth having.
            </p>
            <ul className="mt-6 flex flex-wrap gap-2" aria-label="How I work">
              {PRINCIPLES.map(({ icon: Icon, label }) => (
                <li
                  key={label}
                  className="inline-flex items-center gap-2 rounded-full border border-border bg-background/40 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground"
                >
                  <Icon className="h-3.5 w-3.5 text-blueprint" />
                  {label}
                </li>
              ))}
            </ul>
          </div>

          <nav aria-label="Services" className="lg:col-span-3">
            <div className={headingClass}>Services</div>
            <ul className="mt-5 space-y-3">
              {SERVICES.map((s) => (
                <li key={s.label}>
                  <Link href={s.href} className={`${linkClass} group flex items-baseline gap-2 whitespace-nowrap`}>
                    {s.label}
                    {s.note && (
                      <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted-foreground/70">
                        {s.note}
                      </span>
                    )}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          <nav aria-label="Company" className="lg:col-span-2">
            <div className={headingClass}>Company</div>
            <ul className="mt-5 space-y-3">
              {COMPANY.map((c) => (
                <li key={c.label}>
                  <Link href={c.href} className={linkClass}>
                    {c.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>

          <div className="lg:col-span-3">
            <div className={headingClass}>Get in touch</div>
            <ul className="mt-5 space-y-3.5">
              <li>
                <a href="mailto:hello@scalardigital.co.uk" className={`${linkClass} flex items-center gap-3 break-all`}>
                  <Mail className="h-4 w-4 flex-none text-blueprint" />
                  hello@scalardigital.co.uk
                </a>
              </li>
              <li>
                <a href="tel:+447401696272" className={`${linkClass} flex items-center gap-3`}>
                  <Phone className="h-4 w-4 flex-none text-blueprint" />
                  +44 7401 696272
                </a>
              </li>
              <li>
                <a href={WHATSAPP} target="_blank" rel="noopener noreferrer" className={`${linkClass} flex items-center gap-3`}>
                  <MessageCircle className="h-4 w-4 flex-none text-blueprint" />
                  WhatsApp
                </a>
              </li>
              <li>
                <a href={LINKEDIN} target="_blank" rel="noopener noreferrer" className={`${linkClass} flex items-center gap-3`}>
                  <ArrowUpRight className="h-4 w-4 flex-none text-blueprint" />
                  LinkedIn
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col gap-4 border-t border-border py-6 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>&copy; {new Date().getFullYear()} Scalar Digital. All rights reserved.</span>
          <span className="hidden md:inline">Pure code. No WordPress. No excuses.</span>
          <a href="#top" className="group inline-flex items-center gap-2 transition-colors hover:text-blueprint">
            Back to top
            <ArrowUp className="h-3.5 w-3.5 transition-transform group-hover:-translate-y-0.5" />
          </a>
        </div>
      </div>
    </footer>
  )
}
