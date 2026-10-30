// Run with `node --test src/cites.test.ts` from web/.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { linkExplanation } from './cites.ts'

const GRAPPLED = { path: 'conditions > grappled', text: 'Grappled' }
const MELEE = { path: 'making-an-attack > melee-attacks', text: 'Melee Attacks' }
const ENTRIES = [GRAPPLED, MELEE]

test('a quoted path with its marker links as the title, neither left as text', () => {
  // The shape a live reply wrote, and the `##` it showed inside the link.
  const parts = linkExplanation("The rule on '## conditions > grappled' sets speed to 0.", ENTRIES)
  assert.deepEqual(parts, [
    { text: 'The rule on ' },
    { text: 'Conditions › Grappled', entry: GRAPPLED },
    { text: ' sets speed to 0.' },
  ])
})

test('a bare path links as the title', () => {
  const parts = linkExplanation('Under making-an-attack > melee-attacks, a reach of 5 feet.', ENTRIES)
  assert.deepEqual(parts[1], { text: 'Making an attack › Melee attacks', entry: MELEE })
})

test('parentheses around a path stay in the text', () => {
  const parts = linkExplanation('Its speed is 0 (conditions > grappled).', ENTRIES)
  assert.deepEqual(parts, [
    { text: 'Its speed is 0 (' },
    { text: 'Conditions › Grappled', entry: GRAPPLED },
    { text: ').' },
  ])
})
