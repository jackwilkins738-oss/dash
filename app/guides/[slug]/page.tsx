import type { Metadata } from 'next'
import Link from 'next/link'
import { notFound } from 'next/navigation'
import { ArrowRight } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { Breadcrumbs } from '@/components/breadcrumbs'
import { Faq } from '@/components/faq'
import { JsonLd } from '@/components/json-ld'
import { CtaBand } from '@/components/cta-band'
import { Reveal } from '@/components/reveal'
import { SITE } from '@/lib/site'
import { withSeo } from '@/lib/seo'
import { loadGuides, guideBySlug } from '@/lib/guides'
import { pieces, plain } from '@/lib/guide-content'

// Guides the monthly SEO loop drafted (content/guides/<slug>.json), published when its pull request
// is merged. The hand-written guides keep their own folders, which take precedence over this route.
type Props = { params: Promise<{ slug: string }> }

export const dynamicParams = false

export function generateStaticParams() {
  return loadGuides().map((g) => ({ slug: g.slug }))
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params
  const g = guideBySlug(slug)
  if (!g) return {}
  const path = `/guides/${g.slug}`
  return withSeo(path, {
    title: g.metaTitle,
    description: g.description,
    alternates: { canonical: path },
    openGraph: { title: `${g.title} | ${SITE.name}`, description: g.description, url: path, type: 'article' },
  })
}

function Rich({ text }: { text: string }) {
  return (
    <>
      {pieces(text).map((p, i) =>
        p.href ? (
          <Link key={i} href={p.href} className="text-blueprint underline underline-offset-4">
            {p.text}
          </Link>
        ) : p.bold ? (
          <strong key={i} className="text-foreground">
            {p.text}
          </strong>
        ) : (
          <span key={i}>{p.text}</span>
        ),
      )}
    </>
  )
}

export default async function DraftedGuidePage({ params }: Props) {
  const { slug } = await params
  const g = guideBySlug(slug)
  if (!g) notFound()
  const path = `/guides/${g.slug}`

  return (
    <main>
      <JsonLd
        data={{
          '@context': 'https://schema.org',
          '@type': 'Article',
          headline: g.title,
          description: g.description,
          datePublished: g.published,
          dateModified: g.published,
          inLanguage: 'en-GB',
          mainEntityOfPage: `${SITE.url}${path}`,
          author: { '@type': 'Organization', name: SITE.name, url: SITE.url },
          publisher: { '@id': `${SITE.url}/#organization` },
        }}
      />
      <Breadcrumbs items={[{ name: 'Guides', href: '/guides' }, { name: g.title, href: path }]} />
      <PageHeader compact eyebrow="Guide" title={g.title} body={plain(g.description)} />

      <article className="py-20 sm:py-24">
        <div className="mx-auto max-w-3xl px-5 sm:px-8">
          <Reveal>
            <div className="rounded-2xl border border-blueprint/40 bg-card p-7">
              <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">The short answer</span>
              <p className="mt-3 text-pretty leading-relaxed text-foreground/90">
                <Rich text={g.summary} />
              </p>
            </div>
          </Reveal>

          {g.sections.map((s) => (
            <Reveal key={s.heading} className="mt-14">
              <h2 className="font-display text-balance text-3xl font-bold tracking-tight">{s.heading}</h2>
              {s.paragraphs.map((p, i) => (
                <p key={i} className="mt-4 text-pretty leading-relaxed text-muted-foreground">
                  <Rich text={p} />
                </p>
              ))}
              {s.bullets && s.bullets.length > 0 && (
                <ul className="mt-6 space-y-4 text-pretty leading-relaxed text-muted-foreground">
                  {s.bullets.map((b) => (
                    <li key={b.lead}>
                      <strong className="text-foreground">{b.lead}</strong> <Rich text={b.text} />
                    </li>
                  ))}
                </ul>
              )}
            </Reveal>
          ))}

          <Reveal className="mt-14 rounded-2xl border border-border bg-card/40 p-7">
            <h2 className="font-display text-2xl font-bold tracking-tight">Want a site that does this for you?</h2>
            <p className="mt-3 text-pretty leading-relaxed text-muted-foreground">
              The price is fixed and agreed before any work starts, and you own the site outright.
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
              <Link
                href="/work#pricing"
                className="group inline-flex items-center gap-2 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-blueprint transition-colors hover:text-brass"
              >
                See prices and what&apos;s included
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
              <Link
                href="/guides"
                className="font-mono text-sm uppercase tracking-[0.15em] text-muted-foreground transition-colors hover:text-blueprint"
              >
                More guides
              </Link>
            </div>
          </Reveal>
        </div>
      </article>

      {g.faqs.length > 0 && <Faq items={g.faqs} path={path} title="More questions" />}
      <CtaBand />
    </main>
  )
}
