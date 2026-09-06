import Link from 'next/link'

const socials = ['Instagram', 'LinkedIn', 'X', 'YouTube']

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-card/30">
      <div className="mx-auto max-w-6xl px-5 py-16 sm:px-8">
        <div className="flex flex-col gap-12 md:flex-row md:items-start md:justify-between">
          <div className="max-w-sm">
            <div className="font-mono text-2xl font-bold tracking-tight">
              S<span className="text-blueprint">·</span>D
            </div>
            <p className="mt-4 text-sm leading-relaxed text-muted-foreground">
              Hand-coded websites for trades who take their work seriously. Built to load fast, rank locally and win
              the jobs worth having.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-10 sm:grid-cols-3">
            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground">Pages</div>
              <ul className="mt-4 space-y-2 text-sm">
                <li>
                  <Link href="/" className="text-foreground/80 transition-colors hover:text-blueprint">
                    Home
                  </Link>
                </li>
                <li>
                  <Link href="/work" className="text-foreground/80 transition-colors hover:text-blueprint">
                    Services &amp; Work
                  </Link>
                </li>
                <li>
                  <Link href="/contact" className="text-foreground/80 transition-colors hover:text-blueprint">
                    Contact
                  </Link>
                </li>
              </ul>
            </div>

            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground">Contact</div>
              <ul className="mt-4 space-y-2 text-sm">
                <li>
                  <a href="mailto:hello@scalardigital.co.uk" className="text-foreground/80 transition-colors hover:text-blueprint">
                    hello@scalardigital.co.uk
                  </a>
                </li>
                <li>
                  <a href="tel:+447000000000" className="text-foreground/80 transition-colors hover:text-blueprint">
                    +44 7000 000 000
                  </a>
                </li>
              </ul>
            </div>

            <div>
              <div className="font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground">Social</div>
              <ul className="mt-4 space-y-2 text-sm">
                {socials.map((s) => (
                  <li key={s}>
                    <a href="#" className="text-foreground/80 transition-colors hover:text-blueprint">
                      {s}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-14 flex flex-col gap-3 border-t border-border pt-6 font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground sm:flex-row sm:items-center sm:justify-between">
          <span>&copy; {new Date().getFullYear()} Scalar Digital. All rights reserved.</span>
          <span>Pure code. No WordPress. No excuses.</span>
        </div>
      </div>
    </footer>
  )
}
