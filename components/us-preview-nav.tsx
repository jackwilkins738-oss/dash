// The header on a US preview (lib/market.ts). The site's own nav is hidden there (data-uk-only):
// every page it links to - home, pricing, contact - is the UK site, in pounds with a UK phone number.
// So this one stays on the preview itself, where everything is already in dollars.

const links = [
  { href: '#preview', label: 'Your preview' },
  { href: '#findings', label: 'Your site today' },
  { href: '#pricing', label: 'Pricing' },
]

export function UsPreviewNav({ businessName }: { businessName: string }) {
  return (
    <header
      data-print="hide"
      className="fixed inset-x-0 top-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl"
    >
      <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-5 sm:px-8">
        <a href="#top" className="flex min-w-0 items-center" aria-label={`Back to the top of the preview for ${businessName}`}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/brand/mark-96.webp" alt="" width={195} height={191} className="h-7 w-auto" />
          <span className="ml-3 hidden font-sans text-xs font-medium uppercase tracking-[0.3em] text-foreground/80 sm:inline">
            Scalar Digital
          </span>
        </a>
        <div className="flex items-center gap-6">
          {links.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className="hidden font-mono text-xs uppercase tracking-[0.15em] text-muted-foreground transition-colors hover:text-foreground md:inline"
            >
              {l.label}
            </a>
          ))}
          <a
            href="#reply"
            className="btn-chamfer-sm inline-flex items-center gap-2 bg-blueprint px-4 py-2 font-mono text-xs font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background"
          >
            Get in touch
          </a>
        </div>
      </nav>
    </header>
  )
}
