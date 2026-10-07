import { test } from 'node:test'
import assert from 'node:assert/strict'
import { FOUNDING, foundingLeft } from './site.ts'

test('founding places left: the real count, never below zero', () => {
  assert.equal(foundingLeft({ places: 3, taken: 0 }), 3)
  assert.equal(foundingLeft({ places: 3, taken: 2 }), 1)
  assert.equal(foundingLeft({ places: 3, taken: 5 }), 0)
  assert.ok(foundingLeft() <= FOUNDING.places)
})
