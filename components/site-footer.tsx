import Link from 'next/link'
import { ArrowUpRight } from 'lucide-react'

const linkClass = 'text-foreground/80 transition-colors hover:text-blueprint'
const headingClass = 'font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground'

export function SiteFooter() {
  return (
    <footer className="relative overflow-hidden border-t border-border bg-card/30">
      <div
        className="pointer-events-none absolute inset-x-0 top-0 h-px"
        style={{ background: 'linear-gradient(90deg, transparent, oklch(0.62 0.135 244 / 0.7), transparent)' }}
        aria-hidden="true"
      />

      <div className="mx-auto max-w-6xl px-5 pt-16 sm:px-8 sm:pt-20">
        <div className="flex flex-col gap-8 border-b border-border pb-14 md:flex-row md:items-end md:justify-between">
          <div className="max-w-xl">
            <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Ready when you are</span>
            <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl">
              A site that wins the jobs worth having.
            </h2>
          </div>
          <Link
            href="/contact"
            className="group btn-chamfer inline-flex w-fit items-center gap-2 bg-blueprint px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background"
          >
            Start your build
            <ArrowUpRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </Link>
        </div>

        <div className="grid gap-12 py-14 md:grid-cols-[1.4fr_2fr]">
          <div className="max-w-sm">
            <div className="font-mono text-2xl font-bold tracking-tight">
              S<span className="text-blueprint">·</span>D
              <span className="ml-3 text-sm font-medium tracking-[0.2em] text-muted-foreground">SCALAR DIGITAL</span>
            </div>
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Hand-coded websites for trades who take their work seriously. Built to load fast, rank locally and win
              the jobs worth having.
            </p>
            <p className="mt-5 inline-flex items-center gap-2 font-mono text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
              <span className="h-1.5 w-1.5 rounded-full bg-blueprint" aria-hidden="true" />
              Fixed prices · You own the code
            </p>
          </div>

          <div className="grid grid-cols-2 gap-10 sm:grid-cols-3">
            <div>
              <div className={headingClass}>Pages</div>
              <ul className="mt-4 space-y-2.5 text-sm">
                <li><Link href="/" className={linkClass}>Home</Link></li>
                <li><Link href="/work" className={linkClass}>Services &amp; Pricing</Link></li>
                <li><Link href="/process" className={linkClass}>Process</Link></li>
                <li><Link href="/contact" className={linkClass}>Contact</Link></li>
              </ul>
            </div>

            <div>
              <div className={headingClass}>Explore</div>
              <ul className="mt-4 space-y-2.5 text-sm">
                <li><Link href="/#dash" className={linkClass}>The client dashboard</Link></li>
                <li><Link href="/#estimate" className={linkClass}>Price estimator</Link></li>
                <li><Link href="/privacy" className={linkClass}>Privacy Policy</Link></li>
              </ul>
            </div>

            <div className="col-span-2 sm:col-span-1">
              <div className={headingClass}>Contact</div>
              <ul className="mt-4 space-y-2.5 text-sm">
                <li>
                  <a href="mailto:hello@scalardigital.co.uk" className={`${linkClass} break-all`}>
                    hello@scalardigital.co.uk
                  </a>
                </li>
                <li>
                  <a href="tel:+447401696272" className={linkClass}>
                    +44 7401 696272
                  </a>
                </li>
                <li>
                  <a
                    href="https://www.linkedin.com/in/scalar-digital-868841438/"
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`${linkClass} inline-flex items-center gap-1.5`}
                  >
                    LinkedIn
                    <ArrowUpRight className="h-3.5 w-3.5" />
                  </a>
                </li>
              </ul>
            </div>
          </div>
        </div>

        <div className="flex flex-col gap-3 border-t border-border py-6 font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>&copy; {new Date().getFullYear()} Scalar Digital. All rights reserved.</span>
          <span>Pure code. No WordPress. No excuses.</span>
        </div>
      </div>
    </footer>
  )
}
