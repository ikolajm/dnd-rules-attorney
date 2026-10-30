// Run with `node --test src/cites.test.ts` from web/.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { entryLabel, linkExplanation } from './cites.ts'

// Entries as the corpus writes them, each opening with its own title line.
const GRAPPLED = { path: 'conditions > grappled', text: 'Grappled\n\n- A grappled creature’s speed becomes 0.' }
const MELEE = { path: 'making-an-attack > melee-attacks', text: 'Melee Attacks\n\nUsed in hand-to-hand combat.' }
const ENTRIES = [GRAPPLED, MELEE]

test('a quoted path with its marker links as the title, neither left as text', () => {
  // The shape a live reply wrote, and the `##` it showed inside the link.
  const parts = linkExplanation("The rule on '## conditions > grappled' sets speed to 0.", ENTRIES)
  assert.deepEqual(parts, [
    { text: 'The rule on ' },
    { text: 'Grappled', entry: GRAPPLED },
    { text: ' sets speed to 0.' },
  ])
})

test('a bare path links as the title', () => {
  const parts = linkExplanation('Under making-an-attack > melee-attacks, a reach of 5 feet.', ENTRIES)
  assert.deepEqual(parts[1], { text: 'Melee Attacks', entry: MELEE })
})

test('parentheses around a path stay in the text', () => {
  const parts = linkExplanation('Its speed is 0 (conditions > grappled).', ENTRIES)
  assert.deepEqual(parts, [
    { text: 'Its speed is 0 (' },
    { text: 'Grappled', entry: GRAPPLED },
    { text: ').' },
  ])
})

test('an entry is named by its own title, cased as the source writes it', () => {
  // The slug alone gives "Melee attacks".
  assert.equal(entryLabel(MELEE), 'Melee Attacks')
})
