import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { INTRO_HEAD_SCRIPT, INTRO_SEEN_CLASS, INTRO_SEEN_KEY } from './intro.ts'

// The head script runs before first paint on every page load, so it has to be
// right and it has to never throw. It is a string, so it is exercised here by
// running it against a stand-in document and sessionStorage.

function run(store: Record<string, string> | 'throws', pathname = '/') {
  const classes = new Set<string>()
  const document = { documentElement: { classList: { add: (c: string) => classes.add(c) } } }
  const sessionStorage =
    store === 'throws'
      ? {
          getItem() {
            throw new Error('SecurityError')
          },
          setItem() {
            throw new Error('SecurityError')
          },
        }
      : {
          getItem: (k: string) => store[k] ?? null,
          setItem: (k: string, v: string) => {
            store[k] = v
          },
        }
  new Function('document', 'sessionStorage', 'location', INTRO_HEAD_SCRIPT)(document, sessionStorage, { pathname })
  return { classes, store }
}

describe('INTRO_HEAD_SCRIPT', () => {
  it('lets a first visit play the intro: no class, and the visit is recorded', () => {
    const { classes, store } = run({})
    assert.equal(classes.has(INTRO_SEEN_CLASS), false)
    assert.equal((store as Record<string, string>)[INTRO_SEEN_KEY], '1')
  })

  it('hides the intro for a returning visitor', () => {
    const { classes } = run({ [INTRO_SEEN_KEY]: '1' })
    assert.equal(classes.has(INTRO_SEEN_CLASS), true)
  })

  it('plays the intro when storage is blocked, rather than throwing', () => {
    assert.doesNotThrow(() => run('throws'))
    assert.equal(run('throws').classes.has(INTRO_SEEN_CLASS), false)
  })

  it('ignores an unexpected stored value', () => {
    assert.equal(run({ [INTRO_SEEN_KEY]: 'yes' }).classes.has(INTRO_SEEN_CLASS), false)
  })

  it('never plays the intro on a personalised preview page', () => {
    assert.equal(run({}, '/for/acme-driveways').classes.has(INTRO_SEEN_CLASS), true)
    assert.equal(run('throws', '/for/acme-driveways').classes.has(INTRO_SEEN_CLASS), true)
  })

  it('still plays it on other pages whose path merely contains "for"', () => {
    assert.equal(run({}, '/websites-for/plumbers').classes.has(INTRO_SEEN_CLASS), false)
  })

  it('is small enough to sit in <head> without costing anything', () => {
    assert.ok(INTRO_HEAD_SCRIPT.length < 250)
  })
})
