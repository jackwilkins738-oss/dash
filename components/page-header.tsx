import { Reveal } from '@/components/reveal'

type PageHeaderProps = {
  eyebrow: string
  title: string
  body: string
}

export function PageHeader({ eyebrow, title, body }: PageHeaderProps) {
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
      <div className="relative mx-auto max-w-6xl px-5 pt-36 pb-20 sm:px-8 sm:pt-44 sm:pb-24">
        <Reveal className="max-w-3xl">
          <span className="font-mono text-[11px] uppercase tracking-[0.3em] text-blueprint">{eyebrow}</span>
          <h1 className="mt-5 font-display text-balance text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl lg:text-6xl">
            {title}
          </h1>
          <p className="mt-6 max-w-xl text-pretty text-base leading-relaxed text-muted-foreground sm:text-lg">
            {body}
          </p>
        </Reveal>
      </div>
    </section>
  )
}
