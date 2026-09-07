import { Zap, Smartphone, Feather, KeyRound, MessageCircle, MapPin } from 'lucide-react'
import { Reveal } from '@/components/reveal'

const SERVICES = [
  {
    icon: Zap,
    title: 'Genuinely fast',
    body: 'Hand-coded and lightweight, so your site loads before a customer even thinks about hitting back. Amazon found every extra 0.1 seconds of load time cost them 1% in sales — yours won’t have that problem.',
  },
  {
    icon: Smartphone,
    title: 'Mobile-first, always',
    body: 'Most of your customers are on a phone in a driveway or a garden. A site that isn’t built for that loses visitors 5 times faster than one that is — yours is built for the thumb first, not squeezed to fit it after.',
  },
  {
    icon: Feather,
    title: 'No WordPress bloat',
    body: 'No themes, no 30 plugins, no security holes. 9 in 10 hacked business websites run WordPress — almost always through a plugin, not WordPress itself. Yours has none to break in through.',
  },
  {
    icon: KeyRound,
    title: 'Full ownership',
    body: 'You pay once and own everything — code, domain, content. No monthly rental and no being locked out of your own website.',
  },
  {
    icon: MessageCircle,
    title: 'WhatsApp built in',
    body: 'One tap and the customer is messaging you directly. The fastest way to catch a hot lead before they ring the next name on the list.',
  },
  {
    icon: MapPin,
    title: 'Local SEO',
    body: 'Structured to rank for the towns and services you actually work in, so the right people in the right postcode find you first.',
  },
]

export function Services() {
  return (
    <section id="services" className="py-24 sm:py-28">
      <div className="mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal className="max-w-2xl">
          <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">What you get</span>
          <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl lg:text-5xl">
            Everything a trade site needs. Nothing it doesn&apos;t.
          </h2>
          <p className="mt-5 text-pretty leading-relaxed text-muted-foreground">
            Six things every site I build does properly — because these are the things that actually turn a scroll
            into a phone call.
          </p>
        </Reveal>

        {/* A spec sheet, not a feature grid - numbered rows with hairline
            dividers read as a real technical enumeration, fitting the
            blueprint concept, rather than six identical bordered cards. */}
        <Reveal stagger className="mt-14 divide-y divide-border border-y border-border">
          {SERVICES.map((s, i) => {
            const Icon = s.icon
            return (
              <div key={s.title} className="group flex flex-col gap-4 py-8 sm:flex-row sm:items-center sm:gap-6">
                <div className="flex flex-none items-center gap-4 sm:w-36">
                  <span className="font-mono text-sm text-muted-foreground">{String(i + 1).padStart(2, '0')}</span>
                  <div className="btn-chamfer-sm flex h-11 w-11 items-center justify-center border border-blueprint/30 bg-blueprint/10 text-blueprint transition-colors group-hover:border-blueprint/60 group-hover:bg-blueprint/15">
                    <Icon className="h-5 w-5" strokeWidth={1.75} />
                  </div>
                </div>
                <div>
                  <h3 className="font-display text-lg font-semibold">{s.title}</h3>
                  <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{s.body}</p>
                </div>
              </div>
            )
          })}
        </Reveal>
      </div>
    </section>
  )
}
