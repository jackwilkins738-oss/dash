// The pure half of the scroll-reveal (components/reveal-controller.tsx): which
// elements animate, with what delay, and what "shown" and "hidden" mean. It
// touches nothing but the element handed to it, so it can be tested without a
// browser.

export const REVEAL_EASE = 'cubic-bezier(0.165, 0.84, 0.44, 1)' // power3.out equivalent
export const REVEAL_DURATION_MS = 900
export const REVEAL_STAGGER_S = 0.09
export const REVEAL_RISE_PX = 28

// The observer fires once an element's top edge has scrolled into the bottom
// 15% of the viewport: the root is shrunk by 15% at the bottom, and anything
// whose top is already above that line counts as "already in view".
export const REVEAL_ROOT_MARGIN = '0px 0px -15% 0px'
export const REVEAL_TRIGGER_LINE = 0.85

type StyleLike = { opacity: string; transform: string; transition: string }
export type RevealTarget = { style: StyleLike }
export type RevealElement = RevealTarget & {
  dataset: { reveal?: string; revealDelay?: string }
  // The DOM types a parent's children as plain Elements, which have no `style`.
  // In practice every child of a staggered <Reveal> is an HTML or SVG element
  // and does, so it is narrowed where it is read, below.
  children: ArrayLike<unknown>
}

const isStagger = (el: RevealElement) => el.dataset.reveal === 'stagger'

/** The elements that actually move: the children when staggering, else the element itself. */
export function revealTargets(el: RevealElement): RevealTarget[] {
  return isStagger(el) ? Array.from(el.children as ArrayLike<RevealTarget>) : [el]
}

/** Seconds before target `index` of `el` starts to move. */
export function revealDelay(el: RevealElement, index: number): number {
  const base = Number(el.dataset.revealDelay) || 0
  return base + (isStagger(el) ? index * REVEAL_STAGGER_S : 0)
}

/** Should this element be hidden to await its reveal, or left exactly as it is? */
export function shouldAnimate(elementTop: number, viewportHeight: number): boolean {
  // Already in view, or scrolled past: hiding it only to fade it straight back
  // in would flash, and hiding something above the viewport would leave it
  // invisible until the visitor scrolled back up to it.
  return elementTop >= viewportHeight * REVEAL_TRIGGER_LINE
}

export function hideForReveal(el: RevealElement): void {
  revealTargets(el).forEach((t, i) => {
    const d = revealDelay(el, i)
    t.style.opacity = '0'
    t.style.transform = `translateY(${REVEAL_RISE_PX}px)`
    t.style.transition = `opacity ${REVEAL_DURATION_MS}ms ${REVEAL_EASE} ${d}s, transform ${REVEAL_DURATION_MS}ms ${REVEAL_EASE} ${d}s`
  })
}

export function showRevealed(el: RevealElement): void {
  for (const t of revealTargets(el)) {
    t.style.opacity = '1'
    t.style.transform = 'translateY(0)'
  }
}

/** Puts an element back exactly as the server rendered it. */
export function clearReveal(el: RevealElement): void {
  for (const t of revealTargets(el)) {
    t.style.opacity = ''
    t.style.transform = ''
    t.style.transition = ''
  }
}
