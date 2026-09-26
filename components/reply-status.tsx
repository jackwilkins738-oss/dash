'use client'

import { useSyncExternalStore } from 'react'
import { statusFor, ukNow, type UkNow } from '@/lib/reply-status'

// A live answer to the one question everyone has at the moment they're about
// to send an enquiry: "when will I actually hear back?" Worked out from the
// real UK time against the working hours stated on the contact page
// (Mon-Sat, 7am-7pm UK time), so it is always true, never a fake "online now".

// Re-read the clock every 30 seconds; nothing else needs to change it.
const subscribe = (onChange: () => void) => {
  const id = window.setInterval(onChange, 30_000)
  return () => window.clearInterval(id)
}
let cached: { key: string; value: UkNow } | null = null
const getSnapshot = () => {
  const n = ukNow()
  // useSyncExternalStore needs a stable object while nothing has changed.
  if (!cached || cached.key !== n.label + n.day) cached = { key: n.label + n.day, value: n }
  return cached.value
}
const getServerSnapshot = () => null

export function ReplyStatus() {
  const now = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot)

  // Server render and first paint: the plain promise, which is true either way.
  if (!now) {
    return (
      <Badge tone="on">
        <span className="text-foreground">Reply within 2 hours</span>
      </Badge>
    )
  }

  const { open, next } = statusFor(now)
  return open ? (
    <Badge tone="on">
      <span className="text-foreground">Working now</span>
      <span className="text-muted-foreground">· {now.label} UK · reply within 2 hours</span>
    </Badge>
  ) : (
    <Badge tone="off">
      <span className="text-foreground">{now.label} in the UK</span>
      <span className="text-muted-foreground">· first in the queue at {next}</span>
    </Badge>
  )
}

function Badge({ tone, children }: { tone: 'on' | 'off'; children: React.ReactNode }) {
  return (
    <div
      className="inline-flex flex-wrap items-center gap-x-2 gap-y-1 rounded-full border border-blueprint/40 bg-card/50 px-4 py-1.5 font-mono text-[11px] uppercase tracking-[0.16em]"
      aria-live="polite"
    >
      <span className="relative flex h-2 w-2 flex-none" aria-hidden="true">
        {tone === 'on' && (
          <span className="absolute inset-0 rounded-full bg-blueprint opacity-60 motion-safe:animate-ping" />
        )}
        <span className={`relative h-2 w-2 rounded-full ${tone === 'on' ? 'bg-blueprint' : 'bg-brass'}`} />
      </span>
      {children}
    </div>
  )
}
