import Link from 'next/link'
import { Fragment, type CSSProperties, type ReactNode } from 'react'
import { Reveal } from '@/components/reveal'

type PageHeaderProps = {
  eyebrow: string
  title: string
  body: string
  /** Use when a breadcrumb bar sits above the header (it already clears the fixed nav) */
  compact?: boolean
  /** Optional buttons/links under the body - for pages people land on cold */
  actions?: ReactNode
}

// Every inner page opens the way the homepage does: the headline rises word
// by word out of its own mask (app/intro.css, .ph-word), a drafted rule
// measures in under the eyebrow, and a hairline is drawn across the foot of
// the header. All CSS, no JavaScript; phones and reduced-motion visitors get
// the finished page straight away, as with the homepage hero.
export function PageHeader({ eyebrow, title, body, compact = false, actions }: PageHeaderProps) {
  const words = title.split(' ')
  return (
    <section className="relative overflow-hidden border-b border-border">
      <div className="blueprint-grid pointer-events-none absolute inset-0 opacity-40" aria-hidden="true" />
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(90% 80% at 50% 0%, oklch(0.62 0.135 244 / 0.14), transparent 55%), linear-gradient(to bottom, transparent 60%, var(--background))',
        }}
        aria-hidden="true"
      />
      <div
        className={`hero-recede relative mx-auto max-w-6xl px-5 sm:px-8 ${compact ? 'pt-14 pb-16 sm:pt-16 sm:pb-20' : 'pt-36 pb-20 sm:pt-44 sm:pb-24'}`}
      >
        <Reveal className="ph-stagger max-w-3xl">
          <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.3em] text-blueprint">{eyebrow}</span>
          <h1 className="mt-5 font-display text-balance text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
            {words.map((word, i) => (
              <Fragment key={i}>
                <span className="inline-block overflow-hidden pb-[0.14em] -mb-[0.14em] align-bottom">
                  <span className="ph-word" style={{ ['--i' as string]: i } as CSSProperties}>
                    {word}
                  </span>
                </span>
                {i < words.length - 1 ? ' ' : null}
              </Fragment>
            ))}
          </h1>
          <p className="mt-6 max-w-xl text-pretty text-base leading-relaxed text-muted-foreground sm:text-lg">
            {body}
          </p>
          {actions ? <div className="mt-8">{actions}</div> : null}
        </Reveal>
      </div>
      {/* The measured line across the foot of the header. */}
      <span className="ph-rule pointer-events-none absolute inset-x-0 bottom-0 h-px" aria-hidden="true" />
    </section>
  )
}

/** The standard pair of header actions, plus the three-promise reassurance line. */
export function HeaderActions({
  secondary,
  primaryHref = '/contact',
}: {
  secondary?: { href: string; label: string }
  primaryHref?: string
}) {
  return (
    <>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Link
          href={primaryHref}
          data-magnetic
          className="btn-chamfer btn-sheen group inline-flex items-center justify-center gap-2 bg-blueprint px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-primary-foreground transition-colors hover:bg-brass hover:text-background"
        >
          Start your build
          <span className="transition-transform group-hover:translate-x-1">&rarr;</span>
        </Link>
        {secondary ? (
          <Link
            href={secondary.href}
            data-magnetic
            className="btn-chamfer inline-flex items-center justify-center gap-2 border border-border px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-foreground transition-colors hover:border-blueprint hover:text-blueprint"
          >
            {secondary.label}
          </Link>
        ) : null}
      </div>
      <p className="mt-4 font-mono text-[11px] uppercase tracking-[0.14em] text-muted-foreground">
        Fixed price <span className="text-blueprint/60">/</span> Plan within 2 hours{' '}
        <span className="text-blueprint/60">/</span> No sales call
      </p>
    </>
  )
}
