import { Reveal } from '@/components/reveal'

// A short screen recording made for this one firm: the owner walking through their preview. Only on
// pages that have one (set from the panel), and only from Loom, YouTube or Vimeo (lib/preview-extras).
export function PreviewVideo({ src, firmName }: { src: string; firmName: string }) {
  return (
    <section id="video" className="scroll-mt-20 border-t border-border py-16 sm:py-20" data-print="hide">
      <div className="mx-auto max-w-4xl px-5 sm:px-8">
        <Reveal>
          <span className="draft-rule font-mono text-[11px] uppercase tracking-[0.25em] text-blueprint">Recorded for you</span>
          <h2 className="mt-4 font-display text-balance text-3xl font-bold tracking-tight sm:text-4xl">
            A quick walk through this page for {firmName}.
          </h2>
          <p className="mt-4 text-pretty leading-relaxed text-muted-foreground">
            Under two minutes: what I found on your current site and what I&apos;d change first.
          </p>
          <div className="mt-8 aspect-video overflow-hidden rounded-2xl border border-border bg-card">
            <iframe
              src={src}
              title={`Walkthrough for ${firmName}`}
              className="h-full w-full"
              loading="lazy"
              allow="fullscreen; picture-in-picture"
              allowFullScreen
              referrerPolicy="strict-origin-when-cross-origin"
            />
          </div>
        </Reveal>
      </div>
    </section>
  )
}
