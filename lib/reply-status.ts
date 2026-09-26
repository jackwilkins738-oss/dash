// When will an enquiry sent right now be answered? Worked out from the real UK
// time against the working hours the contact page states (Mon-Sat, 7am-7pm
// UK time). Used by components/reply-status.tsx.

export const OPEN_HOUR = 7
export const CLOSE_HOUR = 19

/** day: 0 = Sunday ... 6 = Saturday, as Date#getDay. */
export type UkNow = { day: number; hour: number; minute: number; label: string }

export function ukNow(date: Date = new Date()): UkNow {
  const parts = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/London',
    weekday: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date)
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? ''
  const day = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].indexOf(get('weekday'))
  return { day, hour: Number(get('hour')), minute: Number(get('minute')), label: `${get('hour')}:${get('minute')}` }
}

export function statusFor(now: Pick<UkNow, 'day' | 'hour'>): { open: boolean; next: string } {
  const workingDay = now.day >= 1 && now.day <= 6
  if (workingDay && now.hour >= OPEN_HOUR && now.hour < CLOSE_HOUR) return { open: true, next: '' }
  if (workingDay && now.hour < OPEN_HOUR) return { open: false, next: '7am today' }
  // After hours, or any time on a Sunday: the next working morning.
  const nextDay = (now.day + 1) % 7
  return { open: false, next: nextDay === 0 ? '7am Monday' : '7am tomorrow' }
}
