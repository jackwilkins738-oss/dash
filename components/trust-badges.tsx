import { Code2, ShieldCheck } from 'lucide-react'

// Only claims that are actually true today. Two more were discussed
// (an "Est. 20XX" / projects-completed counter, and an ICO
// registration badge) but need real numbers before they can go here -
// add them once there's a real founding year/count and a real ICO
// registration number, not before.
const BADGES = [
  { icon: Code2, label: 'Hand-coded — no page-builder' },
  { icon: ShieldCheck, label: 'SSL secured' },
]

export function TrustBadges({ className = '' }: { className?: string }) {
  return (
    <div className={`flex flex-wrap items-center gap-3 ${className}`}>
      {BADGES.map((b) => {
        const Icon = b.icon
        return (
          <span
            key={b.label}
            className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card/50 px-3 py-1.5 font-mono text-[10px] uppercase tracking-[0.15em] text-muted-foreground backdrop-blur"
          >
            <Icon className="h-3.5 w-3.5 text-blueprint" strokeWidth={2} />
            {b.label}
          </span>
        )
      })}
    </div>
  )
}
