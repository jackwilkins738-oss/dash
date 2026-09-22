'use client'

import { useState, type ReactNode } from 'react'
import Link from 'next/link'
import {
  ArrowRight,
  BellRing,
  CalendarClock,
  Check,
  FileText,
  HardHat,
  History,
  LayoutDashboard,
  Mail,
  Smartphone,
  Users,
  UserCheck,
  Wallet,
} from 'lucide-react'
import { Reveal } from '@/components/reveal'

/*
 * An interactive preview of the dash, drawn with the real product's own
 * design tokens (dark theme, warm orange brand, dark brand-tinted sidebar)
 * and populated with its demo tenant's data - "Ridgeview Lofts &
 * Extensions" - so nothing here is invented beyond a few sample leads.
 * Every capability listed below exists in the shipped product.
 */

const C = {
  page: '#0d1015',
  surface: '#171c24',
  surface2: '#232a37',
  ink: '#f5f1e6',
  ink2: '#c2c6cc',
  muted: '#838894',
  hairline: '#2e3542',
  brand: '#e8935e',
  brandStrong: '#f5b488',
  brandTint: 'rgba(232,147,94,0.16)',
  good: '#0ca30c',
  warning: '#fab219',
  critical: '#d03b3b',
}

type ViewId = 'dashboard' | 'cashflow' | 'customers' | 'team' | 'audit'

const NAV: { id: ViewId; label: string; Icon: typeof LayoutDashboard }[] = [
  { id: 'dashboard', label: 'Dashboard', Icon: LayoutDashboard },
  { id: 'cashflow', label: 'Cashflow', Icon: Wallet },
  { id: 'customers', label: 'Customers', Icon: Users },
  { id: 'team', label: 'Team', Icon: HardHat },
  { id: 'audit', label: 'Audit log', Icon: History },
]

const gbp = (n: number) => '£' + n.toLocaleString('en-GB')

function Pill({ tone, children }: { tone: 'good' | 'warning' | 'critical' | 'brand' | 'muted'; children: ReactNode }) {
  const color = tone === 'good' ? C.good : tone === 'warning' ? C.warning : tone === 'critical' ? C.critical : tone === 'brand' ? C.brand : C.muted
  return (
    <span
      className="inline-flex whitespace-nowrap rounded-full px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-[0.08em]"
      style={{ color, background: `color-mix(in srgb, ${color} 16%, transparent)` }}
    >
      {children}
    </span>
  )
}

function Panel({ title, aside, children }: { title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <div
      className="rounded-xl border p-4 sm:p-5"
      style={{ background: C.surface, borderColor: C.hairline, boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.05)' }}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <h4 className="text-[13px] font-bold" style={{ color: C.ink }}>
          {title}
        </h4>
        {aside}
      </div>
      {children}
    </div>
  )
}

function Kpi({ label, value, tone }: { label: string; value: string; tone?: 'critical' }) {
  return (
    <div className="rounded-xl border p-4" style={{ background: C.surface, borderColor: C.hairline }}>
      <p className="text-[10px] font-bold uppercase tracking-[0.12em]" style={{ color: C.muted }}>
        {label}
      </p>
      <p className="mt-1.5 font-display text-2xl font-bold" style={{ color: tone === 'critical' ? C.critical : C.ink }}>
        {value}
      </p>
    </div>
  )
}

function Table({ head, rows }: { head: string[]; rows: ReactNode[][] }) {
  return (
    <div className="-mx-1 overflow-x-auto">
      <table className="w-full min-w-[520px] text-left text-xs">
        <thead>
          <tr>
            {head.map((h) => (
              <th
                key={h}
                className="px-1 pb-2 text-[10px] font-bold uppercase tracking-[0.1em]"
                style={{ color: C.muted }}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t" style={{ borderColor: C.hairline }}>
              {r.map((c, j) => (
                <td key={j} className="px-1 py-2.5 align-middle" style={{ color: j === 0 ? C.ink : C.ink2 }}>
                  {c}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function Bar({ label, value, pct, color, right }: { label: string; value?: string; pct: number; color: string; right?: string }) {
  return (
    <div className="py-1.5">
      <div className="flex items-center justify-between text-xs">
        <span style={{ color: C.ink }}>{label}</span>
        <span className="font-mono text-[11px] font-semibold" style={{ color: C.ink2 }}>
          {right ?? value}
        </span>
      </div>
      <div className="mt-1.5 h-1.5 overflow-hidden rounded-full" style={{ background: C.surface2 }}>
        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  )
}

function DashboardView() {
  const alerts: { tone: string; text: string; meta: string }[] = [
    { tone: C.critical, text: 'INV-3187 overdue — Sinclair household', meta: '14 days late · £18,400' },
    { tone: C.warning, text: 'Okafor residence at risk — dormer loft', meta: 'Target 19 Dec · awaiting planning decision' },
    { tone: C.brand, text: 'New lead not followed up — M. Lawson', meta: 'Website enquiry · 2 days ago' },
    { tone: C.good, text: 'Site visit tomorrow 09:00 — Whitfield residence', meta: 'Guildford · Sam O.' },
  ]
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label="Active jobs" value="3" />
        <Kpi label="Live pipeline" value={gbp(166500)} />
        <Kpi label="Outstanding" value={gbp(39650)} />
        <Kpi label="Overdue" value={gbp(18400)} tone="critical" />
      </div>
      <div className="grid gap-4 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <Panel title="Needs attention" aside={<BellRing className="h-4 w-4" style={{ color: C.brand }} />}>
            <ul className="space-y-2.5">
              {alerts.map((a) => (
                <li key={a.text} className="flex gap-3">
                  <span className="mt-1.5 h-2 w-2 flex-none rounded-full" style={{ background: a.tone }} />
                  <div className="min-w-0">
                    <p className="text-xs font-semibold" style={{ color: C.ink }}>
                      {a.text}
                    </p>
                    <p className="text-[11px]" style={{ color: C.muted }}>
                      {a.meta}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          </Panel>
        </div>
        <div className="lg:col-span-2">
          <Panel title="Trade capacity">
            <Bar label="Roofers" pct={80} right="80% booked" color={C.brand} />
            <Bar label="Electricians" pct={100} right="100% booked" color={C.warning} />
            <Bar label="Plasterers" pct={45} right="45% booked" color={C.brand} />
            <Bar label="Carpenters" pct={65} right="65% booked" color={C.brand} />
          </Panel>
        </div>
      </div>
      <Panel title="Projects">
        <Table
          head={['Ref', 'Client', 'Stage', 'PM', 'Target', 'Value', 'Status']}
          rows={[
            ['LC-2026-041', 'Whitfield residence, Guildford', 'On site — first fix', 'Sam O.', '14 Nov', gbp(58400), <Pill key="a" tone="good">On track</Pill>],
            ['RE-2026-038', 'Carrow family, Farnham', 'Building control', 'Priya A.', '28 Nov', gbp(46200), <Pill key="b" tone="good">On track</Pill>],
            ['LC-2026-039', 'Okafor residence, Woking', 'Planning decision', 'Sam O.', '19 Dec', gbp(61900), <Pill key="c" tone="warning">At risk</Pill>],
          ]}
        />
      </Panel>
    </div>
  )
}

function CashflowView() {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi label="Outstanding" value={gbp(39650)} />
        <Kpi label="Overdue" value={gbp(18400)} tone="critical" />
        <Kpi label="Due in 7 days" value={gbp(9250)} />
        <Kpi label="Paid to date" value={gbp(26000)} />
      </div>
      <Panel title="Who owes you, and for how long">
        <Bar label="Not yet due" pct={54} right={gbp(21250)} color={C.brand} />
        <Bar label="1–30 days overdue" pct={46} right={gbp(18400)} color={C.critical} />
        <Bar label="31–60 days overdue" pct={0} right={gbp(0)} color={C.warning} />
        <Bar label="60+ days overdue" pct={0} right={gbp(0)} color={C.critical} />
      </Panel>
      <Panel title="Invoices" aside={<FileText className="h-4 w-4" style={{ color: C.brand }} />}>
        <Table
          head={['Invoice', 'Client', 'Amount', 'Due', 'Status']}
          rows={[
            ['INV-3187', 'Sinclair household', gbp(18400), '14 days ago', <Pill key="1" tone="critical">Overdue</Pill>],
            ['INV-3201', 'Carrow family', gbp(9250), 'In 4 days', <Pill key="2" tone="brand">Unpaid</Pill>],
            ['INV-3199', 'Bevan household', gbp(12000), 'In 21 days', <Pill key="3" tone="brand">Unpaid</Pill>],
            ['INV-3150', 'Whitfield residence', gbp(26000), 'Paid', <Pill key="4" tone="good">Paid</Pill>],
          ]}
        />
        <p className="mt-3 text-[11px]" style={{ color: C.muted }}>
          Every quote and invoice downloads as a branded PDF.
        </p>
      </Panel>
    </div>
  )
}

function CustomersView() {
  return (
    <div className="space-y-4">
      <Panel title="Customers" aside={<Pill tone="brand">4 active</Pill>}>
        <Table
          head={['Customer', 'Location', 'Latest', 'Status']}
          rows={[
            ['Whitfield residence', 'Guildford', 'Quote Q-0412 · hip-to-gable loft', <Pill key="1" tone="good">Accepted</Pill>],
            ['Carrow family', 'Farnham', 'Quote Q-0408 · rear extension', <Pill key="2" tone="good">Accepted</Pill>],
            ['Okafor residence', 'Woking', 'Variation VAR-003 · extra steelwork', <Pill key="3" tone="warning">Awaiting approval</Pill>],
            ['M. Lawson', 'Godalming', 'Website enquiry · loft conversion', <Pill key="4" tone="brand">New lead</Pill>],
          ]}
        />
      </Panel>
      <div className="grid gap-4 sm:grid-cols-2">
        <Panel title="What the customer sees — quote">
          <p className="text-xs leading-relaxed" style={{ color: C.ink2 }}>
            Q-0412 · Hip-to-gable loft conversion · <strong style={{ color: C.ink }}>{gbp(58400)}</strong>
          </p>
          <div className="mt-3 flex gap-2">
            <span className="rounded-md px-3 py-1.5 text-[11px] font-bold" style={{ background: C.brand, color: '#1a0f08' }}>
              Accept quote
            </span>
            <span className="rounded-md border px-3 py-1.5 text-[11px] font-bold" style={{ borderColor: C.hairline, color: C.ink2 }}>
              Decline
            </span>
          </div>
          <p className="mt-2.5 text-[11px]" style={{ color: C.muted }}>
            A private link — no login, no app to download.
          </p>
        </Panel>
        <Panel title="What the customer sees — portal">
          <p className="text-xs leading-relaxed" style={{ color: C.ink2 }}>
            VAR-003 · Extra steelwork over the dormer · <strong style={{ color: C.ink }}>{gbp(1850)}</strong>
          </p>
          <div className="mt-3 flex gap-2">
            <span className="rounded-md px-3 py-1.5 text-[11px] font-bold" style={{ background: C.brand, color: '#1a0f08' }}>
              Approve
            </span>
            <span className="rounded-md border px-3 py-1.5 text-[11px] font-bold" style={{ borderColor: C.hairline, color: C.ink2 }}>
              Decline
            </span>
          </div>
          <p className="mt-2.5 text-[11px]" style={{ color: C.muted }}>
            Changes to the scope get agreed in writing, not on a WhatsApp thread.
          </p>
        </Panel>
      </div>
    </div>
  )
}

function TeamView() {
  return (
    <div className="space-y-4">
      <Panel title="Team">
        <Table
          head={['Name', 'Role', 'Current jobs', 'Access']}
          rows={[
            ['Sam O.', <Pill key="1" tone="brand">Owner</Pill>, 'LC-2026-041, LC-2026-039', 'Everything'],
            ['Priya A.', <Pill key="2" tone="muted">Member</Pill>, 'RE-2026-038', 'Everything except Settings and the Audit log'],
          ]}
        />
      </Panel>
      <div className="grid gap-4 sm:grid-cols-2">
        <Panel title="Two access levels" aside={<UserCheck className="h-4 w-4" style={{ color: C.brand }} />}>
          <p className="text-xs leading-relaxed" style={{ color: C.ink2 }}>
            <strong style={{ color: C.ink }}>Owner</strong> sees everything. <strong style={{ color: C.ink }}>Member</strong> runs the
            day-to-day but can&apos;t touch Settings or the audit trail.
          </p>
        </Panel>
        <Panel title="Site visits" aside={<CalendarClock className="h-4 w-4" style={{ color: C.brand }} />}>
          <p className="text-xs leading-relaxed" style={{ color: C.ink2 }}>
            A calendar that warns you when two visits clash — before it&apos;s a problem on the day. Optional Google Calendar sync.
          </p>
        </Panel>
      </div>
    </div>
  )
}

function AuditView() {
  const rows = [
    ['14:32', 'Customer approved VAR-003 via the portal', gbp(1850)],
    ['11:08', 'Sam O. edited the price on Q-0412', ''],
    ['09:10', 'Priya A. added a lead: M. Lawson', ''],
    ['Yesterday 16:45', 'Invoice INV-3201 sent to Carrow family', gbp(9250)],
    ['Yesterday 10:20', 'Sam O. marked INV-3150 as paid', gbp(26000)],
  ]
  return (
    <Panel title="Audit log — who did what, and when" aside={<History className="h-4 w-4" style={{ color: C.brand }} />}>
      <ul>
        {rows.map(([time, what, amount]) => (
          <li key={time + what} className="flex items-baseline gap-4 border-t py-2.5 first:border-none" style={{ borderColor: C.hairline }}>
            <span className="w-28 flex-none font-mono text-[11px]" style={{ color: C.muted }}>
              {time}
            </span>
            <span className="flex-1 text-xs" style={{ color: C.ink }}>
              {what}
            </span>
            {amount && (
              <span className="font-mono text-[11px] font-semibold" style={{ color: C.ink2 }}>
                {amount}
              </span>
            )}
          </li>
        ))}
      </ul>
    </Panel>
  )
}

const VIEWS: Record<ViewId, () => ReactNode> = {
  dashboard: DashboardView,
  cashflow: CashflowView,
  customers: CustomersView,
  team: TeamView,
  audit: AuditView,
}

const FEATURES: { Icon: typeof Users; title: string; body: string }[] = [
  { Icon: Users, title: 'Every enquiry, captured', body: 'Your site’s contact form drops straight into the dash. Leads nobody has followed up get flagged.' },
  { Icon: FileText, title: 'Quotes customers accept online', body: 'Send a branded PDF quote with a private link. They accept or decline — no login, no app.' },
  { Icon: Check, title: 'Scope changes agreed in writing', body: 'Variations go to your customer’s portal to approve or decline, and it’s logged.' },
  { Icon: Wallet, title: 'Invoices and who owes what', body: 'Invoices as PDFs, a cashflow view of what’s overdue, and a nudge before it becomes a chase.' },
  { Icon: HardHat, title: 'Jobs at risk, trades booked', body: 'Spot the job slipping and see which trades are fully booked before you promise a start date.' },
  { Icon: CalendarClock, title: 'A calendar that warns you', body: 'Site visits sit alongside your jobs, with clash warnings and optional Google Calendar sync.' },
  { Icon: History, title: 'Roles and an audit trail', body: 'Owner and member access, and a record of who changed what and when.' },
  { Icon: Mail, title: 'A Monday digest', body: 'One email a week with what needs attention. Nothing to report means no email.' },
]

export function DashShowcase() {
  const [view, setView] = useState<ViewId>('dashboard')
  const View = VIEWS[view]

  return (
    <section id="dash" className="relative overflow-hidden border-y border-[#e8935e]/25 py-24 sm:py-32">
      {/* A distinct product zone: the dash has its own brand (warm orange, dark
          sidebar) inside the mockup below - this wash carries that identity out
          into the marketing section itself, so the eye registers "a different
          product" before reading a word, then the mockup pays it off. */}
      <div
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            'radial-gradient(60% 55% at 50% 0%, rgba(232,147,94,0.10), transparent 65%), radial-gradient(45% 40% at 100% 100%, rgba(232,147,94,0.07), transparent 60%)',
        }}
        aria-hidden="true"
      />
      <div className="relative mx-auto max-w-6xl px-5 sm:px-8">
        <Reveal className="max-w-3xl">
          <span className="inline-flex items-center gap-2 rounded-full border border-[#e8935e]/40 bg-[#e8935e]/10 px-4 py-1.5 font-mono text-[11px] uppercase tracking-[0.25em] text-[#e8935e]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#e8935e]" />
            Included with every Scalar build — not an add-on
          </span>
          <h2 className="mt-5 font-display text-balance text-4xl font-bold tracking-tight sm:text-5xl lg:text-6xl">
            The site brings the lead in.
            <br className="hidden sm:block" /> <span className="text-[#e8935e]">The dash runs the job after.</span>
          </h2>
          <p className="mt-5 max-w-2xl text-pretty text-base leading-relaxed text-muted-foreground sm:text-lg">
            This is the part that separates a website from a business system. Enquiries, quotes, jobs, invoices and
            a customer portal, in your own name and colours, instead of five apps and a WhatsApp thread. Click
            around the preview below — same layout as the real product, shown here with sample data.
          </p>
        </Reveal>

        <Reveal stagger className="mt-10 grid gap-5 md:grid-cols-2">
          <div className="rounded-2xl border border-border bg-card/40 p-7">
            <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-muted-foreground">
              Most trades today
            </span>
            <ul className="mt-5 space-y-3.5 text-sm text-muted-foreground">
              {[
                'Enquiries scattered across WhatsApp, texts and voicemail',
                'Quotes typed up in Word and emailed one by one',
                'Invoices in a spreadsheet, chased by hand',
                'Scope changes agreed on the phone, then disputed',
              ].map((t) => (
                <li key={t} className="flex items-start gap-3">
                  <span className="mt-2 h-px w-3 flex-none bg-muted-foreground/60" aria-hidden="true" />
                  {t}
                </li>
              ))}
            </ul>
          </div>
          <div className="rounded-2xl border border-[#e8935e]/40 bg-card p-7">
            <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-[#e8935e]">With the dash</span>
            <ul className="mt-5 space-y-3.5 text-sm text-foreground/90">
              {[
                'Every enquiry in one list, and the ones nobody has followed up get flagged',
                'Branded quotes your customer accepts online, with no login',
                'Invoices, plus a clear view of who owes what',
                'Variations approved in the customer’s portal, and logged',
              ].map((t) => (
                <li key={t} className="flex items-start gap-3">
                  <Check className="mt-0.5 h-4 w-4 flex-none text-[#e8935e]" strokeWidth={2.5} />
                  {t}
                </li>
              ))}
            </ul>
          </div>
        </Reveal>

        <Reveal className="mt-12">
          <div className="overflow-hidden rounded-2xl border border-border shadow-[0_30px_70px_-30px_rgba(232,147,94,0.35)]">
            {/* Browser chrome */}
            <div className="flex items-center gap-2 border-b border-border bg-card/70 px-4 py-3">
              <span className="h-2.5 w-2.5 rounded-full bg-[#e8935e]/70" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#c2c6cc]/40" />
              <span className="h-2.5 w-2.5 rounded-full bg-[#838894]/40" />
              <span className="ml-3 truncate font-mono text-[11px] text-muted-foreground">
                ridgeview.scalardigital.co.uk/dashboard
              </span>
              <span className="ml-auto hidden rounded-full border border-border px-2.5 py-0.5 font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground sm:inline">
                Sample data
              </span>
            </div>

            <div className="grid lg:grid-cols-[13rem_1fr]" style={{ background: C.page }}>
              {/* Sidebar (rail on desktop, scrolling tab strip on phones) */}
              <div
                className="flex flex-row gap-1 overflow-x-auto p-3 lg:flex-col lg:overflow-visible lg:p-4"
                style={{ background: 'linear-gradient(175deg, color-mix(in srgb, black 83%, #e8935e 17%), color-mix(in srgb, black 91%, #e8935e 9%))' }}
                role="tablist"
                aria-label="Dashboard sections"
              >
                <div className="mb-3 hidden items-center gap-3 px-2 lg:flex">
                  <div
                    className="flex h-9 w-9 flex-none items-center justify-center rounded-xl font-display text-xs font-bold text-white"
                    style={{ background: 'linear-gradient(155deg, #e8935e, #a8481f)' }}
                  >
                    RL
                  </div>
                  <div className="min-w-0">
                    <p className="truncate font-display text-[13px] font-bold leading-tight text-white">Ridgeview Lofts</p>
                    <p className="text-[9px] font-semibold uppercase tracking-[0.12em] text-white/45">Operations</p>
                  </div>
                </div>
                {NAV.map(({ id, label, Icon }) => {
                  const active = id === view
                  return (
                    <button
                      key={id}
                      type="button"
                      role="tab"
                      aria-selected={active}
                      onClick={() => setView(id)}
                      className={`flex flex-none items-center gap-2.5 rounded-lg px-3 py-2.5 text-left text-[13px] font-semibold transition-colors ${
                        active ? 'bg-white/10 text-white' : 'text-white/55 hover:bg-white/5 hover:text-white'
                      }`}
                    >
                      <Icon className="h-4 w-4 flex-none" style={{ color: active ? C.brandStrong : undefined, opacity: active ? 1 : 0.7 }} />
                      {label}
                    </button>
                  )
                })}
              </div>

              <div className="min-w-0 p-4 sm:p-6" role="tabpanel">
                <View />
              </div>
            </div>
          </div>

          <p className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
            <Smartphone className="h-3.5 w-3.5 flex-none" />
            Installs on your phone like an app, in your own business name and colours.
          </p>
        </Reveal>

        <Reveal stagger className="mt-16 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map(({ Icon, title, body }) => (
            <div key={title}>
              <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-[#e8935e]/30 bg-[#e8935e]/10 text-[#e8935e]">
                <Icon className="h-4 w-4" strokeWidth={2.25} />
              </span>
              <h3 className="mt-4 font-display text-lg font-semibold">{title}</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{body}</p>
            </div>
          ))}
        </Reveal>

        <Reveal className="mt-16">
          <div className="relative overflow-hidden rounded-2xl border border-[#e8935e]/40 bg-card p-8 sm:p-10">
            <div
              className="pointer-events-none absolute inset-0 opacity-70"
              style={{ background: 'radial-gradient(80% 70% at 100% 0%, rgba(232,147,94,0.18), transparent 60%)' }}
              aria-hidden="true"
            />
            <div className="relative flex flex-col gap-6 sm:flex-row sm:items-center sm:justify-between">
              <div className="max-w-xl">
                <span className="font-mono text-[11px] uppercase tracking-[0.25em] text-[#e8935e]">Included, not an add-on</span>
                <p className="mt-3 font-display text-2xl font-bold sm:text-3xl">
                  The dash comes with The Scalar build. <span className="text-[#e8935e]">£2,500, fixed.</span>
                </p>
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">
                  Your five-page site and your own dashboard, agreed as one price before a line of code is written. Dashboard hosting is free for your first 12 months; after that it is a small optional monthly fee, agreed up front. Your website stays yours either way.
                </p>
              </div>
              <Link
                href="/contact"
                className="btn-chamfer group inline-flex flex-none items-center justify-center gap-2 bg-[#e8935e] px-7 py-3.5 font-mono text-sm font-semibold uppercase tracking-[0.15em] text-[#1a0f08] transition-colors hover:bg-[#f5b488]"
              >
                Start your build
                <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
              </Link>
            </div>
          </div>
        </Reveal>
      </div>
    </section>
  )
}
