import { BadgeCheck, Code2, ShieldCheck } from 'lucide-react'

// Only claims that are actually true today. An ICO registration badge
// was discussed too, but Scalar Digital isn't registered yet - add it
// once there's a real registration number, not before.
const BADGES = [
  { icon: Code2, label: 'Hand-coded — no page-builder' },
  { icon: ShieldCheck, label: 'SSL secured' },
  { icon: BadgeCheck, label: 'Est. 2026' },
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
