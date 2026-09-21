import Link from 'next/link'
import { JsonLd } from '@/components/json-ld'
import { SITE } from '@/lib/site'

export type Crumb = { name: string; href: string }

// Visible breadcrumb trail plus matching BreadcrumbList structured data.
export function Breadcrumbs({ items }: { items: Crumb[] }) {
  const trail: Crumb[] = [{ name: 'Home', href: '/' }, ...items]
  return (
    <>
      <JsonLd
        data={{
          '@context': 'https://schema.org',
          '@type': 'BreadcrumbList',
          itemListElement: trail.map((c, i) => ({
            '@type': 'ListItem',
            position: i + 1,
            name: c.name,
            item: `${SITE.url}${c.href === '/' ? '' : c.href}`,
          })),
        }}
      />
      <nav aria-label="Breadcrumb" className="border-b border-border pt-24 sm:pt-28">
        <ol className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-2 gap-y-1 px-5 py-3 font-mono text-[11px] uppercase tracking-[0.15em] text-muted-foreground sm:px-8">
          {trail.map((c, i) => (
            <li key={c.href} className="flex items-center gap-2">
              {i < trail.length - 1 ? (
                <>
                  <Link href={c.href} className="transition-colors hover:text-blueprint">
                    {c.name}
                  </Link>
                  <span aria-hidden="true">/</span>
                </>
              ) : (
                <span aria-current="page" className="text-foreground/80">
                  {c.name}
                </span>
              )}
            </li>
          ))}
        </ol>
      </nav>
    </>
  )
}
