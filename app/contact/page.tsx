import type { Metadata } from 'next'
import { MessageCircle, Phone, Mail, Clock } from 'lucide-react'
import { PageHeader } from '@/components/page-header'
import { ContactForm } from '@/components/contact-form'
import { Reveal } from '@/components/reveal'

export const metadata: Metadata = {
  title: 'Contact — Scalar Digital',
  description:
    'Start your build. Send an enquiry, message on WhatsApp, or call directly. Reply within 2 hours, no sales call.',
}

const CHANNELS = [
  {
    icon: MessageCircle,
    label: 'WhatsApp',
    value: 'Message me directly',
    href: 'https://wa.me/447000000000',
    external: true,
  },
  {
    icon: Phone,
    label: 'Phone',
    value: '+44 7000 000 000',
    href: 'tel:+447000000000',
  },
  {
    icon: Mail,
    label: 'Email',
    value: 'hello@scalardigital.co.uk',
    href: 'mailto:hello@scalardigital.co.uk',
  },
]

export default function ContactPage() {
  return (
    <main>
      <PageHeader
        eyebrow="Contact"
        title="Start your build."
        body="Tell me about your trade and the jobs you want more of. I'll come back with a plan and a fixed price — usually within a couple of hours."
      />

      <section className="py-20 sm:py-24">
        <div className="mx-auto max-w-6xl px-5 sm:px-8">
          <div className="grid gap-12 lg:grid-cols-[1fr_1.15fr] lg:gap-16">
            <Reveal>
              <div className="inline-flex items-center gap-2 rounded-full border border-blueprint/40 bg-card/50 px-4 py-1.5">
                <Clock className="h-3.5 w-3.5 text-blueprint" strokeWidth={2} />
                <span className="font-mono text-[11px] uppercase tracking-[0.2em] text-foreground">
                  Reply within 2 hours
                </span>
              </div>

              <h2 className="mt-6 text-balance text-2xl font-bold tracking-tight sm:text-3xl">
                Prefer to skip the form?
              </h2>
              <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
                Fair enough — you&apos;re busy on site. Reach me however suits you. It&apos;s me you&apos;ll speak to,
                not a call centre or an account manager.
              </p>

              <div className="mt-8 flex flex-col gap-3">
                {CHANNELS.map((c) => {
                  const Icon = c.icon
                  return (
                    <a
                      key={c.label}
                      href={c.href}
                      target={c.external ? '_blank' : undefined}
                      rel={c.external ? 'noopener noreferrer' : undefined}
                      className="group flex items-center gap-4 rounded-xl border border-border bg-card/40 p-5 transition-colors hover:border-blueprint/40"
                    >
                      <div className="flex h-11 w-11 items-center justify-center rounded-lg border border-border bg-secondary text-blueprint">
                        <Icon className="h-5 w-5" strokeWidth={1.75} />
                      </div>
                      <div className="min-w-0">
                        <div className="font-mono text-[11px] uppercase tracking-[0.2em] text-muted-foreground">
                          {c.label}
                        </div>
                        <div className="mt-0.5 truncate text-sm font-medium text-foreground transition-colors group-hover:text-blueprint">
                          {c.value}
                        </div>
                      </div>
                      <span
                        className="ml-auto text-muted-foreground transition-all group-hover:translate-x-1 group-hover:text-blueprint"
                        aria-hidden="true"
                      >
                        &rarr;
                      </span>
                    </a>
                  )
                })}
              </div>

              <div className="mt-8 rounded-xl border border-border bg-card/40 p-5">
                <p className="text-sm leading-relaxed text-muted-foreground">
                  <span className="font-medium text-foreground">Working hours:</span> Mon–Sat, 7am–7pm. Send
                  anything outside those and it&apos;ll be first in the queue the next morning.
                </p>
              </div>
            </Reveal>

            <Reveal delay={0.1}>
              <ContactForm />
            </Reveal>
          </div>
        </div>
      </section>
    </main>
  )
}
