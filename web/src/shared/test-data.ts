// The SRD's files as the tests read them, from disk, in one place. Node
// imports JSON only with an import attribute, which the Vite build does not
// need, so the files are read rather than imported.
//
// Each cast goes through the file's own type first, `typeof import(...)`, a
// type-only import that ships nothing, as load.ts does for the browser: tsc
// then refuses a record type the file's shape does not fit, where a cast from
// JSON.parse's `any` alone would take any type at all.
import { readFileSync } from 'node:fs'
import { splitCorpus, type Supplement } from '../encyclopedia/corpus-text.ts'
import type {
  EquipmentRecord,
  MagicItemRecord,
  MonsterRecord,
  NamedRecord,
  RaceRecord,
  SpellRecord,
} from '../encyclopedia/rows.ts'

const DATA = new URL('../../../data/srd-5.1/', import.meta.url)

function read(name: string): unknown {
  return JSON.parse(readFileSync(new URL(name, DATA), 'utf8'))
}

export const SPELLS = read('5e-SRD-Spells.json') as typeof import('../../../data/srd-5.1/5e-SRD-Spells.json', {
  with: { type: 'json' },
}) as SpellRecord[]
export const MAGIC_ITEMS = read('5e-SRD-Magic-Items.json') as typeof import('../../../data/srd-5.1/5e-SRD-Magic-Items.json', {
  with: { type: 'json' },
}) as MagicItemRecord[]
export const MONSTERS = read('5e-SRD-Monsters.json') as typeof import('../../../data/srd-5.1/5e-SRD-Monsters.json', {
  with: { type: 'json' },
}) as MonsterRecord[]
export const EQUIPMENT = read('5e-SRD-Equipment.json') as typeof import('../../../data/srd-5.1/5e-SRD-Equipment.json', {
  with: { type: 'json' },
}) as EquipmentRecord[]
export const RACES = read('5e-SRD-Races.json') as typeof import('../../../data/srd-5.1/5e-SRD-Races.json', {
  with: { type: 'json' },
}) as RaceRecord[]
export const CONDITIONS = read('5e-SRD-Conditions.json') as typeof import('../../../data/srd-5.1/5e-SRD-Conditions.json', {
  with: { type: 'json' },
}) as NamedRecord[]
export const PROPERTIES = read('5e-SRD-Weapon-Properties.json') as typeof import(
  '../../../data/srd-5.1/5e-SRD-Weapon-Properties.json',
  { with: { type: 'json' } }
) as NamedRecord[]
export const SUPPLEMENT = read('supplement.json') as typeof import('../../../data/srd-5.1/supplement.json', {
  with: { type: 'json' },
}) as Supplement

// The corpus as written, and split by path through the split a view reads.
export const CORPUS_TEXT = readFileSync(new URL('corpus.md', DATA), 'utf8')
export const CORPUS = splitCorpus(CORPUS_TEXT)
