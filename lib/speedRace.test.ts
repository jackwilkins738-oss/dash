import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { RACE, STAGE_ORDER, formatSeconds, progressAt, reached, stageAt } from './speedRace.ts'

describe('stageAt', () => {
  it('starts blank, before anything has loaded', () => {
    assert.equal(stageAt(RACE.slow, 0), 'blank')
    assert.equal(stageAt(RACE.slow, RACE.slow.header - 1), 'blank')
  })

  it('reaches a stage exactly at its timestamp', () => {
    assert.equal(stageAt(RACE.slow, RACE.slow.header), 'header')
    assert.equal(stageAt(RACE.slow, RACE.slow.hero), 'hero')
    assert.equal(stageAt(RACE.slow, RACE.slow.done), 'done')
  })

  it('stays on the latest stage between timestamps', () => {
    assert.equal(stageAt(RACE.slow, RACE.slow.hero + 1), 'hero')
    assert.equal(stageAt(RACE.slow, RACE.slow.images - 1), 'banner')
  })

  it('stays done for any time after the end', () => {
    assert.equal(stageAt(RACE.slow, 60_000), 'done')
  })

  it('skips a stage a site does not have', () => {
    // The hand-built page injects no banner, so it goes hero -> images.
    assert.equal(stageAt(RACE.fast, RACE.fast.hero), 'hero')
    assert.equal(stageAt(RACE.fast, RACE.fast.images), 'images')
    assert.equal('banner' in RACE.fast, false)
  })
})

describe('the race itself', () => {
  it('has the fast site finished before the slow one has shown anything', () => {
    // This is the whole point of the section: at the moment the hand-built
    // page is done, the typical page is still on a blank screen.
    assert.ok(RACE.fast.done < RACE.slow.header)
  })

  it('stays under a second for the fast page', () => {
    assert.ok(RACE.fast.done < 1000)
  })

  it('keeps the slow page at the 6+ seconds the site quotes', () => {
    // components/transformation.tsx says "Loads in 6+ seconds on mobile".
    // If this drifts below 6s the illustration contradicts the copy.
    assert.ok(RACE.slow.done >= 6000)
  })

  it('lists stage times in increasing order for both sites', () => {
    for (const timeline of [RACE.slow, RACE.fast] as const) {
      const times = STAGE_ORDER.map((s) => (timeline as Record<string, number | undefined>)[s]).filter(
        (n): n is number => n !== undefined,
      )
      assert.deepEqual(times, [...times].sort((a, b) => a - b))
    }
  })
})

describe('reached', () => {
  it('is true for the stage itself and any later one', () => {
    assert.equal(reached('hero', 'hero'), true)
    assert.equal(reached('images', 'header'), true)
  })

  it('is false for an earlier stage', () => {
    assert.equal(reached('header', 'hero'), false)
    assert.equal(reached('blank', 'header'), false)
  })
})

describe('progressAt', () => {
  it('runs from 0 to 1', () => {
    assert.equal(progressAt(0, 600), 0)
    assert.equal(progressAt(300, 600), 0.5)
    assert.equal(progressAt(600, 600), 1)
  })

  it('clamps rather than overshooting or going negative', () => {
    assert.equal(progressAt(9999, 600), 1)
    assert.equal(progressAt(-50, 600), 0)
  })

  it('treats a zero-length load as already complete', () => {
    assert.equal(progressAt(0, 0), 1)
  })
})

describe('formatSeconds', () => {
  it('shows one decimal place, like a stopwatch', () => {
    assert.equal(formatSeconds(600), '0.6s')
    assert.equal(formatSeconds(6400), '6.4s')
    assert.equal(formatSeconds(0), '0.0s')
  })

  it('rounds to the nearest tenth', () => {
    assert.equal(formatSeconds(149), '0.1s')
    assert.equal(formatSeconds(150), '0.2s')
  })

  it('never shows a negative time', () => {
    assert.equal(formatSeconds(-500), '0.0s')
  })
})
