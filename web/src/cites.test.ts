// Run with `node --test src/cites.test.ts` from web/.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { entryLabel, entryLabels, linkExplanation } from './cites.ts'

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

// The three Spellcasting Ability entries a question about spellcasters drew, as
// the corpus writes them.
const ABILITY = (parent: string) => ({
  path: `using-each-ability > ${parent} > spellcasting-ability`,
  text: 'Spellcasting Ability\n\nYour modifier for this ability.',
})
const SPELLCASTERS = [ABILITY('intelligence'), ABILITY('wisdom'), ABILITY('charisma'), GRAPPLED]

test('entries that share a title each take their parent section', () => {
  const labels = entryLabels(SPELLCASTERS)
  assert.equal(labels.get('using-each-ability > intelligence > spellcasting-ability'), 'Spellcasting Ability (Intelligence)')
  assert.equal(labels.get('using-each-ability > wisdom > spellcasting-ability'), 'Spellcasting Ability (Wisdom)')
  // A title no other entry shares stands alone.
  assert.equal(labels.get('conditions > grappled'), 'Grappled')
})

test('an explanation link reads as the run names the entry', () => {
  const parts = linkExplanation("Under 'using-each-ability > wisdom > spellcasting-ability', clerics cast.", SPELLCASTERS)
  assert.equal(parts[1].text, 'Spellcasting Ability (Wisdom)')
})
