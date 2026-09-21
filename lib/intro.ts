// The site's opening sequence is a two-part handoff: the preloader plays a
// ~1.3s build animation, then its curtain lifts and the hero animates in.
// Both halves have to agree on whether the preloader is going to run, or the
// hero either waits on a curtain that never comes (a blank second) or
// animates underneath one that is still up.
//
// That agreement used to be an implicit constant - the hero's delay was
// tuned to the preloader's runtime. Once the preloader began playing once
// per tab instead of on every load, a returning visitor got no curtain but
// the hero still waited for it. This module is the single place that knows.

const SEEN_KEY = 'scalar-preloaded'

// Matches the preloader's curtain-lift, in seconds. See components/preloader.tsx.
export const INTRO_DELAY_AFTER_PRELOADER = 1.1

export function preloaderAlreadySeen(): boolean {
  // sessionStorage throws in a private window with site data blocked. Treat
  // that as "not seen": the preloader plays, which is the safe default.
  try {
    return window.sessionStorage.getItem(SEEN_KEY) === '1'
  } catch {
    return false
  }
}

export function markPreloaderSeen(): void {
  try {
    window.sessionStorage.setItem(SEEN_KEY, '1')
  } catch {
    // Not remembered: the preloader replays next load, as it always used to.
  }
}
