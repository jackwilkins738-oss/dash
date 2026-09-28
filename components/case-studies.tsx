import { ArrowRight } from 'lucide-react'
import { Reveal } from '@/components/reveal'
import { publishable } from '@/lib/case-studies'

// Real before-and-after results from launched client sites (lib/case-studies.ts).
// Renders nothing until there's at least one client who has agreed to be named.
export function CaseStudies() {
  const studies = publishable()
  if (studies.length === 0) return null

  return (
    <section className="border-t border-border py-24 sm:py-32">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal className="max-w-2xl">
          <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Results</span>
          <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Before and after, measured the same way.
          </h2>
          <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
            Google&apos;s own mobile speed test on the old site, then on the new one. Real clients, named with their
            permission.
          </p>
        </Reveal>

        <Reveal stagger className="mt-12 grid gap-5 md:grid-cols-2">
          {studies.map((c) => (
            <article key={c.site} data-spotlight className="rounded-2xl border border-border bg-card/40 p-7">
              <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-muted-foreground">
                {c.trade} · {c.area}
              </p>
              <h3 className="mt-2 font-display text-2xl font-semibold">{c.business}</h3>

              <dl className="mt-6 grid grid-cols-2 gap-4">
                <div>
                  <dt className="text-xs text-muted-foreground">Speed score</dt>
                  <dd className="mt-1 flex items-center gap-2 font-display text-2xl font-bold">
                    <span className="text-muted-foreground line-through decoration-1">{c.scoreBefore}</span>
                    <ArrowRight className="h-4 w-4 text-blueprint" aria-label="to" />
                    <span className="text-blueprint">{c.scoreAfter}</span>
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Loads on a phone in</dt>
                  <dd className="mt-1 flex items-center gap-2 font-display text-2xl font-bold">
                    <span className="text-muted-foreground line-through decoration-1">{c.loadBefore.toFixed(1)}s</span>
                    <ArrowRight className="h-4 w-4 text-blueprint" aria-label="to" />
                    <span className="text-blueprint">{c.loadAfter.toFixed(1)}s</span>
                  </dd>
                </div>
              </dl>

              {c.fixed.length > 0 && (
                <ul className="mt-6 list-disc space-y-1.5 pl-5 text-sm text-muted-foreground marker:text-blueprint">
                  {c.fixed.slice(0, 4).map((f) => (
                    <li key={f}>Fixed: {f}</li>
                  ))}
                </ul>
              )}

              {c.quote && (
                <blockquote className="mt-6 border-l-2 border-blueprint pl-4 text-pretty text-foreground/90">
                  &ldquo;{c.quote.text}&rdquo;
                  <footer className="mt-2 text-xs text-muted-foreground">{c.quote.name}</footer>
                </blockquote>
              )}

              <a
                href={`https://${c.site}`}
                target="_blank"
                rel="noopener"
                className="mt-6 inline-block font-mono text-xs uppercase tracking-[0.15em] text-blueprint underline-offset-4 hover:underline"
              >
                {c.site}
              </a>
            </article>
          ))}
        </Reveal>
      </div>
    </section>
  )
}
