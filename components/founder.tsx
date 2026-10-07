import Image from 'next/image'
import { FOUNDER, SITE } from '@/lib/site'

// Trades buy from a person: a face, a name and a mobile number, not just a brand. Renders nothing
// until FOUNDER in lib/site.ts is filled in and switched on.
export function Founder() {
  if (!FOUNDER.show || !FOUNDER.name || FOUNDER.lines.length === 0) return null
  const phone = SITE.phone.replace('+44', '0').replace(/^(\d{5})(\d+)$/, '$1 $2')
  return (
    <section id="who" className="scroll-mt-20 border-t border-border py-16 sm:py-20">
      <div className="mx-auto grid max-w-4xl items-center gap-8 px-5 sm:grid-cols-[180px_1fr] sm:px-8">
        <Image
          src={FOUNDER.photo}
          alt={FOUNDER.name}
          width={180}
          height={180}
          className="h-36 w-36 rounded-2xl border border-border object-cover sm:h-44 sm:w-44"
        />
        <div>
          <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Who you&apos;ll deal with</span>
          <h2 className="mt-3 font-display text-2xl font-bold tracking-tight sm:text-3xl">{FOUNDER.name}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{FOUNDER.role}</p>
          {FOUNDER.lines.map((line) => (
            <p key={line} className="mt-3 text-pretty leading-relaxed text-foreground/90">
              {line}
            </p>
          ))}
          <a href={`tel:${SITE.phone}`} className="mt-4 inline-block font-semibold text-blueprint underline-offset-4 hover:underline">
            Ring me direct: {phone}
          </a>
        </div>
      </div>
    </section>
  )
}
