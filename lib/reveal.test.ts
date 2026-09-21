import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import {
  REVEAL_DURATION_MS,
  REVEAL_EASE,
  REVEAL_STAGGER_S,
  clearReveal,
  hideForReveal,
  revealDelay,
  revealTargets,
  shouldAnimate,
  showRevealed,
  type RevealElement,
  type RevealTarget,
} from './reveal.ts'

// A stand-in for a DOM element: enough surface for the reveal logic, and it
// starts in the state the server renders it in (no inline styles at all).
const target = (): RevealTarget => ({ style: { opacity: '', transform: '', transition: '' } })
const element = (opts: { reveal?: string; delay?: string; children?: number } = {}): RevealElement => ({
  ...target(),
  dataset: { reveal: opts.reveal ?? '', revealDelay: opts.delay },
  children: Array.from({ length: opts.children ?? 0 }, target),
})

describe('revealTargets', () => {
  it('animates the element itself by default', () => {
    const el = element()
    assert.deepEqual(revealTargets(el), [el])
  })

  it('animates the children instead when staggering', () => {
    const el = element({ reveal: 'stagger', children: 3 })
    assert.equal(revealTargets(el).length, 3)
    assert.ok(!revealTargets(el).includes(el))
  })
})

describe('revealDelay', () => {
  it('is zero when nothing asks for one', () => {
    assert.equal(revealDelay(element(), 0), 0)
  })

  it('honours an explicit delay', () => {
    assert.equal(revealDelay(element({ delay: '0.4' }), 0), 0.4)
  })

  it('offsets each staggered child by a fixed step', () => {
    const el = element({ reveal: 'stagger', children: 4 })
    assert.equal(revealDelay(el, 0), 0)
    assert.ok(Math.abs(revealDelay(el, 3) - 3 * REVEAL_STAGGER_S) < 1e-9)
  })

  it('adds the stagger to an explicit base delay', () => {
    const el = element({ reveal: 'stagger', delay: '0.2', children: 3 })
    assert.ok(Math.abs(revealDelay(el, 2) - (0.2 + 2 * REVEAL_STAGGER_S)) < 1e-9)
  })

  it('reads a floating-point artefact from the markup as the number it means', () => {
    // A call site computes 0.1 * 3 and the server writes "0.30000000000000004".
    assert.ok(Math.abs(revealDelay(element({ delay: '0.30000000000000004' }), 0) - 0.3) < 1e-9)
  })

  it('treats junk as no delay rather than NaN', () => {
    assert.equal(revealDelay(element({ delay: 'soon' }), 0), 0)
  })

  it('does not stagger a non-staggered element by index', () => {
    assert.equal(revealDelay(element({ delay: '0.1' }), 5), 0.1)
  })
})

describe('shouldAnimate', () => {
  it('animates something below the trigger line', () => {
    assert.equal(shouldAnimate(900, 800), true)
  })

  it('leaves alone something already in the first screen', () => {
    assert.equal(shouldAnimate(100, 800), false)
  })

  it('leaves alone something scrolled past, rather than hiding it out of sight', () => {
    assert.equal(shouldAnimate(-1500, 800), false)
  })

  it('draws the line at 85% of the viewport', () => {
    assert.equal(shouldAnimate(679, 800), false)
    assert.equal(shouldAnimate(680, 800), true)
  })
})

describe('hideForReveal / showRevealed / clearReveal', () => {
  it('hides the element and prepares the transition, with its delay', () => {
    const el = element({ delay: '0.4' })
    hideForReveal(el)
    assert.equal(el.style.opacity, '0')
    assert.equal(el.style.transform, 'translateY(28px)')
    assert.ok(el.style.transition.includes(`${REVEAL_DURATION_MS}ms ${REVEAL_EASE} 0.4s`))
  })

  it('gives each staggered child a later delay than the one before', () => {
    const el = element({ reveal: 'stagger', children: 3 })
    hideForReveal(el)
    const delays = (revealTargets(el) as RevealTarget[]).map((t) => Number(/ ([\d.]+)s,/.exec(t.style.transition)![1]))
    assert.ok(delays[0] < delays[1] && delays[1] < delays[2])
  })

  it('leaves a staggered container itself untouched - only its children move', () => {
    const el = element({ reveal: 'stagger', children: 2 })
    hideForReveal(el)
    assert.equal(el.style.opacity, '')
  })

  it('shows what was hidden', () => {
    const el = element()
    hideForReveal(el)
    showRevealed(el)
    assert.equal(el.style.opacity, '1')
    assert.equal(el.style.transform, 'translateY(0)')
  })

  it('clears back to the server-rendered state, so nothing is left invisible', () => {
    const el = element({ reveal: 'stagger', children: 2 })
    hideForReveal(el)
    clearReveal(el)
    for (const t of revealTargets(el)) {
      assert.deepEqual(t.style, { opacity: '', transform: '', transition: '' })
    }
  })
})
