const TRADES = [
  'Loft Conversions',
  'Resin Driveways',
  'Landscaping',
  'House Extensions',
  'Roofing',
  'Block Paving',
  'Garden Design',
  'Kitchen Fitting',
  'Bathroom Renovation',
  'Bricklaying',
  'Groundworks',
  'Patios & Decking',
]

export function TrustMarquee() {
  const items = [...TRADES, ...TRADES]
  return (
    <div className="mask-fade-x relative flex overflow-hidden border-y border-border bg-card/40 py-4">
      <div className="animate-marquee flex shrink-0 items-center gap-3 pr-3">
        {items.map((t, i) => (
          <span
            key={i}
            className="btn-chamfer-sm whitespace-nowrap border border-blueprint/25 bg-blueprint/[0.06] px-3.5 py-1.5 font-mono text-xs uppercase tracking-[0.2em] text-muted-foreground"
          >
            {t}
          </span>
        ))}
      </div>
    </div>
  )
}
