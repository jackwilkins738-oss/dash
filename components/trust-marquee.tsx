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
      <div className="animate-marquee flex shrink-0 items-center gap-8 pr-8">
        {items.map((t, i) => (
          <div key={i} className="flex items-center gap-8">
            <span className="whitespace-nowrap font-mono text-xs uppercase tracking-[0.25em] text-muted-foreground">
              {t}
            </span>
            <span className="text-blueprint" aria-hidden="true">
              &middot;
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
