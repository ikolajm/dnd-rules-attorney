// Run with `node --test src/encyclopedia/rows.test.ts` from web/.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { splitCorpus } from './corpus-text.ts'
import {
  challengeText,
  equipmentRow,
  magicItemRow,
  monsterRow,
  namedRow,
  raceRow,
  spellRow,
  type EquipmentRecord,
  type MagicItemRecord,
  type MonsterRecord,
  type NamedRecord,
  type RaceRecord,
  type Row,
  type SpellRecord,
} from './rows.ts'

// The real files, read rather than imported: Node imports JSON only with an
// import attribute, which the Vite build does not need.
const DATA = new URL('../../../data/srd-5.1/', import.meta.url)

function read<T>(name: string): T[] {
  return JSON.parse(readFileSync(new URL(name, DATA), 'utf8')) as T[]
}

const ITEMS = read<MagicItemRecord>('5e-SRD-Magic-Items.json')
const EQUIPMENT = read<EquipmentRecord>('5e-SRD-Equipment.json')
const MONSTERS = read<MonsterRecord>('5e-SRD-Monsters.json')

// The corpus by path, through the same split a record's view reads, so a row's
// path is checked against what that view will look up.
const CORPUS = splitCorpus(readFileSync(new URL('corpus.md', DATA), 'utf8'))

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
    ['spells', rowsOf(read<SpellRecord>('5e-SRD-Spells.json'), spellRow)],
    ['magic items', rowsOf(ITEMS, magicItemRow)],
    ['monsters', rowsOf(MONSTERS, monsterRow)],
    ['equipment', rowsOf(EQUIPMENT, equipmentRow)],
    ['races', rowsOf(read<RaceRecord>('5e-SRD-Races.json'), raceRow)],
    ['conditions', rowsOf(read<NamedRecord>('5e-SRD-Conditions.json'), (r) => namedRow('conditions', r))],
    [
      'weapon properties',
      rowsOf(read<NamedRecord>('5e-SRD-Weapon-Properties.json'), (r) => namedRow('weapon-properties', r)),
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
  assert.equal(magicItemRow(ITEMS.find((r) => r.variant)!), null)
  const parents = ITEMS.filter((r) => !r.variant).length
  assert.equal(rowsOf(ITEMS, magicItemRow).length, parents)
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
  assert.equal(magicItemRow(byIndex(ITEMS, 'cloak-of-protection'))!.fields.Attunement, 'yes')
  // "Wondrous item, uncommon"
  assert.equal(magicItemRow(byIndex(ITEMS, 'bag-of-holding'))!.fields.Attunement, 'no')
})

test('a challenge below 1 reads as a fraction', () => {
  assert.equal(challengeText(0.125), '1/8')
  assert.equal(challengeText(0.25), '1/4')
  assert.equal(challengeText(0.5), '1/2')
  assert.equal(challengeText(0), '0')
  assert.equal(challengeText(24), '24')
  assert.equal(monsterRow(byIndex(MONSTERS, 'skeleton')).fields.Challenge, '1/4')
})
