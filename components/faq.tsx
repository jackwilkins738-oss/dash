import { JsonLd } from '@/components/json-ld'
import { Reveal } from '@/components/reveal'

export type QA = { q: string; a: string }

// Visible FAQ (native <details>, no JS) with FAQPage structured data built from the very same text,
// so what Google reads always matches what a visitor sees.
export function Faq({ items, title = 'Common questions', eyebrow = 'FAQ' }: { items: QA[]; title?: string; eyebrow?: string }) {
  return (
    <section className="border-t border-border py-20 sm:py-24">
      <JsonLd
        data={{
          '@context': 'https://schema.org',
          '@type': 'FAQPage',
          mainEntity: items.map((i) => ({
            '@type': 'Question',
            name: i.q,
            acceptedAnswer: { '@type': 'Answer', text: i.a },
          })),
        }}
      />
      <div className="mx-auto max-w-3xl px-5 sm:px-8">
        <Reveal>
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">{eyebrow}</span>
          <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl">{title}</h2>
        </Reveal>
        <div className="mt-10 divide-y divide-border border-y border-border">
          {items.map((i) => (
            <details key={i.q} className="group py-5">
              <summary className="flex cursor-pointer list-none items-start justify-between gap-6 font-display text-lg font-semibold [&::-webkit-details-marker]:hidden">
                {i.q}
                <span className="mt-1 font-mono text-blueprint transition-transform group-open:rotate-45" aria-hidden="true">
                  +
                </span>
              </summary>
              <p className="mt-3 pr-8 text-pretty leading-relaxed text-muted-foreground">{i.a}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  )
}
