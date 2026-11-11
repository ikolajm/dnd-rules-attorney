// Run with `node --test src/encyclopedia/filter.test.ts` from web/.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { compareRows, compareValues, matches, NAME, options } from './filter.ts'
import {
  magicItemRow,
  monsterRow,
  spellRow,
  type Row,
} from './rows.ts'
import { MAGIC_ITEMS, MONSTERS, SPELLS } from '../shared/test-data.ts'

// Undead first and twice, so an unsorted or a repeated result shows; poison in
// two rows' lists; and an empty list, as armor's properties are.
const ROWS: Row[] = [
  { path: 'monsters > one', name: 'One', fields: { Type: 'undead', Immunities: ['poison', 'cold'] } },
  { path: 'monsters > two', name: 'Two', fields: { Type: 'beast', Immunities: ['poison'] } },
  { path: 'monsters > three', name: 'Three', fields: { Type: 'undead', Immunities: [] } },
]

test('options are distinct and sorted', () => {
  assert.deepEqual(options(ROWS, 'Type'), ['beast', 'undead'])
})

test('a list field contributes each member', () => {
  assert.deepEqual(options(ROWS, 'Immunities'), ['cold', 'poison'])
})

// `equal` to true rather than `ok`, which any truthy value passes.
test('the name search ignores case and outer spaces', () => {
  assert.equal(matches(ROWS[0], 'ONE', {}), true)
  assert.equal(matches(ROWS[2], ' three ', {}), true)
  assert.equal(matches(ROWS[1], 'one', {}), false)
})

test('an empty search with nothing chosen passes every row', () => {
  assert.equal(
    ROWS.every((row) => matches(row, '', {})),
    true,
  )
})

test('a list field passes when any member is chosen', () => {
  assert.equal(matches(ROWS[0], '', { Immunities: 'cold' }), true)
  assert.equal(matches(ROWS[1], '', { Immunities: 'cold' }), false)
})

// Two holds poison but is a beast; Three is undead but holds nothing.
test('every chosen field must pass', () => {
  const kept = ROWS.filter((row) => matches(row, '', { Type: 'undead', Immunities: 'poison' }))
  assert.deepEqual(
    kept.map((row) => row.name),
    ['One'],
  )
})

// A copy, since sort sorts in place. Each list below starts out of order.
const sortedAs = (field: string, values: string[]) => [...values].sort((a, b) => compareValues(field, a, b))

test('a challenge sorts by its rating, fractions first', () => {
  assert.deepEqual(sortedAs('Challenge', ['2', '1/2', '0', '1/8', '10', '1/4']), ['0', '1/8', '1/4', '1/2', '2', '10'])
})

test('a spell level sorts with cantrip as 0', () => {
  assert.deepEqual(sortedAs('Level', ['3', 'cantrip', '10', '1']), ['cantrip', '1', '3', '10'])
})

test('a size sorts from Tiny to Gargantuan', () => {
  assert.deepEqual(sortedAs('Size', ['Huge', 'Tiny', 'Medium', 'Gargantuan']), ['Tiny', 'Medium', 'Huge', 'Gargantuan'])
})

test('a rarity sorts from Common to Artifact, with Varies after', () => {
  assert.deepEqual(sortedAs('Rarity', ['Varies', 'Rare', 'Artifact', 'Common', 'Very Rare']), [
    'Common',
    'Rare',
    'Very Rare',
    'Artifact',
    'Varies',
  ])
})

// A default sort would put Zombie first.
test('a text field sorts ignoring case', () => {
  assert.deepEqual(sortedAs('Type', ['undead', 'Zombie', 'aberration']), ['aberration', 'undead', 'Zombie'])
})

// The two undead keep their order, since sort is stable.
test('rows sort by a field, or by name', () => {
  assert.deepEqual(
    [...ROWS].sort(compareRows('Type')).map((row) => row.name),
    ['Two', 'One', 'Three'],
  )
  assert.deepEqual(
    [...ROWS].sort(compareRows(NAME)).map((row) => row.name),
    ['One', 'Three', 'Two'],
  )
})

// Text order would give 0, 1/2, 1/4.
test("a field's options sort as its column does", () => {
  const rows: Row[] = ['1/2', '0', '1/4'].map((challenge) => ({
    path: `monsters > ${challenge}`,
    name: challenge,
    fields: { Challenge: challenge },
  }))
  assert.deepEqual(options(rows, 'Challenge'), ['0', '1/4', '1/2'])
})

// rank matches field labels as strings that rows.ts writes as keys. The tests
// above type the labels in, so only rows built by the real row functions show a
// label the two files disagree on: that column falls back to text order.
test("the real rows' ordered fields sort in their own order", () => {
  const monsters = MONSTERS.map(monsterRow)
  const spells = SPELLS.map(spellRow)
  const items = MAGIC_ITEMS.map(magicItemRow).filter((row) => row !== null)
  assert.deepEqual(options(monsters, 'Challenge').slice(0, 6), ['0', '1/8', '1/4', '1/2', '1', '2'])
  assert.deepEqual(options(monsters, 'Size'), ['Tiny', 'Small', 'Medium', 'Large', 'Huge', 'Gargantuan'])
  assert.deepEqual(options(spells, 'Level').slice(0, 3), ['cantrip', '1', '2'])
  assert.deepEqual(options(items, 'Rarity'), [
    'Common',
    'Uncommon',
    'Rare',
    'Very Rare',
    'Legendary',
    'Artifact',
    'Varies',
  ])
})
