import { Code2, KeyRound, Lock } from 'lucide-react'

// Only claims that are actually true today. An ICO registration badge
// was discussed too, but Scalar Digital isn't registered yet - add it
// once there's a real registration number, not before.
// These used to include 'SSL secured' and 'Est. 2026'. Every site has SSL, so
// listing it reads as padding, and a founding year this recent works against
// the premium read rather than for it. What's here instead are the two
// promises that actually lower the risk of saying yes.
const BADGES = [
  { icon: Code2, label: 'Hand-coded — no page-builder' },
  { icon: Lock, label: 'Fixed price, agreed up front' },
  { icon: KeyRound, label: 'You own the site outright' },
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
