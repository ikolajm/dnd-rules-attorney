// Run with `node --test src/encyclopedia/rows.test.ts` from web/.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import {
  challengeText,
  equipmentRow,
  magicItemRow,
  monsterRow,
  namedRow,
  raceRow,
  spellRow,
  type Row,
} from './rows.ts'
import { CONDITIONS, CORPUS, EQUIPMENT, MAGIC_ITEMS, MONSTERS, PROPERTIES, RACES, SPELLS } from '../shared/test-data.ts'

// Each kind's rows, the records that make none dropped.
function rowsOf<T>(records: T[], toRow: (record: T) => Row | null): Row[] {
  return records.map(toRow).filter((row) => row !== null)
}

function byIndex<T extends { index: string }>(records: T[], index: string): T {
  const record = records.find((r) => r.index === index)
  assert.ok(record, `no record ${index}`)
  return record
}

test("every row's path is a corpus path", () => {
  const kinds: [string, Row[]][] = [
    ['spells', rowsOf(SPELLS, spellRow)],
    ['magic items', rowsOf(MAGIC_ITEMS, magicItemRow)],
    ['monsters', rowsOf(MONSTERS, monsterRow)],
    ['equipment', rowsOf(EQUIPMENT, equipmentRow)],
    ['races', rowsOf(RACES, raceRow)],
    ['conditions', rowsOf(CONDITIONS, (r) => namedRow('conditions', r))],
    [
      'weapon properties',
      rowsOf(PROPERTIES, (r) => namedRow('weapon-properties', r)),
    ],
  ]
  for (const [kind, rows] of kinds) {
    assert.ok(rows.length > 0, `${kind} made no rows`)
    const missing = rows.filter((row) => !CORPUS.has(row.path)).map((row) => row.path)
    assert.deepEqual(missing, [], `${kind} paths not in the corpus`)
    // `read` casts the parsed file unchecked, so a key a record type names
    // that the file does not have arrives as undefined. This is where it shows.
    const unread = rows.filter((row) => Object.values(row.fields).flat().some((value) => value === undefined))
    assert.deepEqual(unread.map((row) => row.path), [], `${kind} rows with a field never read`)
  }
})

test('a magic item variant makes no row, and every other item one', () => {
  assert.equal(magicItemRow(MAGIC_ITEMS.find((r) => r.variant)!), null)
  const parents = MAGIC_ITEMS.filter((r) => !r.variant).length
  assert.equal(rowsOf(MAGIC_ITEMS, magicItemRow).length, parents)
})

test('only weapons and armor make an equipment row', () => {
  assert.equal(equipmentRow(byIndex(EQUIPMENT, 'abacus')), null)
  const kept = EQUIPMENT.filter((r) => ['weapon', 'armor'].includes(r.equipment_category.index)).length
  assert.equal(rowsOf(EQUIPMENT, equipmentRow).length, kept)
})

test('every weapon and armor row has a category, armor named as armor', () => {
  for (const row of rowsOf(EQUIPMENT, equipmentRow)) {
    assert.ok(row.fields.Category, `${row.path} has no category`)
  }
  assert.equal(equipmentRow(byIndex(EQUIPMENT, 'chain-mail'))!.fields.Category, 'Heavy Armor')
  assert.equal(equipmentRow(byIndex(EQUIPMENT, 'shield'))!.fields.Category, 'Shield')
  assert.equal(equipmentRow(byIndex(EQUIPMENT, 'longsword'))!.fields.Category, 'Martial Melee')
})

test('a weapon or armor with no category is refused', () => {
  const longsword = byIndex(EQUIPMENT, 'longsword')
  assert.throws(() => equipmentRow({ ...longsword, category_range: null }), /longsword has no weapon category/)
  const chainMail = byIndex(EQUIPMENT, 'chain-mail')
  assert.throws(() => equipmentRow({ ...chainMail, armor_category: null }), /chain-mail has no armor category/)
})

test('attunement is read from the clause in the first line', () => {
  // "Wondrous item, uncommon (requires attunement)"
  assert.equal(magicItemRow(byIndex(MAGIC_ITEMS, 'cloak-of-protection'))!.fields.Attunement, 'yes')
  // "Wondrous item, uncommon"
  assert.equal(magicItemRow(byIndex(MAGIC_ITEMS, 'bag-of-holding'))!.fields.Attunement, 'no')
})

test('a challenge below 1 reads as a fraction', () => {
  assert.equal(challengeText(0.125), '1/8')
  assert.equal(challengeText(0.25), '1/4')
  assert.equal(challengeText(0.5), '1/2')
  assert.equal(challengeText(0), '0')
  assert.equal(challengeText(24), '24')
  assert.equal(monsterRow(byIndex(MONSTERS, 'skeleton')).fields.Challenge, '1/4')
})
