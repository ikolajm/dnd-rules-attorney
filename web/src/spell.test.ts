// Run with `node --test src/spell.test.ts` from web/.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { parseSpell } from './spell.ts'

// Bodies as the corpus writes them, the title line already dropped.
const FIRE_BOLT =
  'Level: cantrip\nSchool: Evocation\nCasting time: 1 action\nRange: 120 feet\nComponents: V, S\n' +
  'Duration: Instantaneous\nConcentration: no\nRitual: no\n\nYou hurl a mote of fire.'
const CONTROL_WEATHER =
  'Level: 8\nSchool: Transmutation\nCasting time: 10 minutes\nRange: Self\n' +
  'Components: V, S, M (Burning incense and bits of earth and wood mixed in water.)\n' +
  'Duration: Up to 8 hours\nConcentration: yes\nRitual: no\n\nYou take control of the weather.'
const ALARM =
  'Level: 1\nSchool: Abjuration\nCasting time: 1 minute\nRange: 30 feet\nComponents: V, S, M (A tiny bell.)\n' +
  'Duration: 8 hours\nConcentration: no\nRitual: yes\n\nYou set an alarm.\n\nAt Higher Levels. It lasts longer.'

test('a cantrip reads as one, with no material', () => {
  const spell = parseSpell(FIRE_BOLT)!
  assert.equal(spell.subtitle, 'Cantrip · Evocation')
  assert.deepEqual([spell.verbal, spell.somatic, spell.material], [true, true, null])
  assert.equal(spell.duration, 'Instantaneous')
  assert.equal(spell.body, 'You hurl a mote of fire.')
})

test('a levelled spell keeps its material sentence and folds concentration in', () => {
  const spell = parseSpell(CONTROL_WEATHER)!
  assert.equal(spell.subtitle, 'Level 8 · Transmutation')
  assert.equal(spell.material, 'Burning incense and bits of earth and wood mixed in water.')
  assert.equal(spell.duration, 'Concentration, up to 8 hours')
})

test('a ritual says so, and At Higher Levels is a bold lead-in', () => {
  const spell = parseSpell(ALARM)!
  assert.equal(spell.subtitle, 'Level 1 · Abjuration · Ritual')
  assert.equal(spell.body, 'You set an alarm.\n\n**At Higher Levels.** It lasts longer.')
})

test('stat lines not in the corpus form are left alone', () => {
  // A rule section, with no stat lines at all.
  assert.equal(parseSpell('When you want to grab a creature, make a grapple.'), null)
  // Eight lines, but one label not the corpus's, so the count alone passes it.
  assert.equal(parseSpell(FIRE_BOLT.replace('Range: 120 feet', 'Reach: 120 feet')), null)
})
