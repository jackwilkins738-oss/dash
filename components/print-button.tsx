'use client'

// "Print or save as PDF" - for the owner who wants to show a partner or keep a copy.
// The page's print styles (globals.css) turn it into a clean document.
export function PrintButton({ className = '' }: { className?: string }) {
  return (
    <button
      type="button"
      data-print="hide"
      onClick={() => window.print()}
      className={`font-mono text-xs uppercase tracking-[0.18em] text-muted-foreground underline-offset-4 hover:text-foreground hover:underline ${className}`}
    >
      Print or save as PDF
    </button>
  )
}
