// What the encyclopedia loads in the browser: each kind's records and rows, the
// corpus by path and the supplement. Each file loads on first need and is kept
// from then on, so the ask screen carries none of it.
import { splitCorpus, type Supplement } from './corpus-text.ts'
import { once } from './once.ts'
import {
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

// One loader per file, its path written out: Vite bundles a dynamic import only
// when its argument is a literal, so a shared function taking the file's name
// would leave the file out of dist/. A JSON module's content is its default
// export. The typed import is what makes each cast a checked one: tsc refuses a
// record type the file's shape does not fit, which `fetch`'s `any` would take.
// Its cost is a slower full type check. The cast stays here, where tsc still
// knows the file's shape, and not in a helper taking `unknown`. H reads the
// records of the kinds it lays out; the rest are read only through KINDS.
export const spellRecords = once(() =>
  import('../../../data/srd-5.1/5e-SRD-Spells.json').then((m) => m.default as SpellRecord[]),
)
export const magicItemRecords = once(() =>
  import('../../../data/srd-5.1/5e-SRD-Magic-Items.json').then((m) => m.default as MagicItemRecord[]),
)
export const monsterRecords = once(() =>
  import('../../../data/srd-5.1/5e-SRD-Monsters.json').then((m) => m.default as MonsterRecord[]),
)
const equipmentRecords = once(() =>
  import('../../../data/srd-5.1/5e-SRD-Equipment.json').then((m) => m.default as EquipmentRecord[]),
)
const raceRecords = once(() =>
  import('../../../data/srd-5.1/5e-SRD-Races.json').then((m) => m.default as RaceRecord[]),
)
const conditionRecords = once(() =>
  import('../../../data/srd-5.1/5e-SRD-Conditions.json').then((m) => m.default as NamedRecord[]),
)
const propertyRecords = once(() =>
  import('../../../data/srd-5.1/5e-SRD-Weapon-Properties.json').then((m) => m.default as NamedRecord[]),
)

// A kind as the table's picker lists it.
export type Kind = { root: string; label: string; rows: () => Promise<Row[]> }

// A kind's rows, built once from its records, the records that make none dropped.
function rowsFrom<T>(records: () => Promise<T[]>, toRow: (record: T) => Row | null): () => Promise<Row[]> {
  return once(async () => (await records()).map(toRow).filter((row) => row !== null))
}

// In the order the picker shows them.
export const KINDS: Kind[] = [
  { root: 'spells', label: 'Spells', rows: rowsFrom(spellRecords, spellRow) },
  { root: 'magic-items', label: 'Magic items', rows: rowsFrom(magicItemRecords, magicItemRow) },
  { root: 'monsters', label: 'Monsters', rows: rowsFrom(monsterRecords, monsterRow) },
  { root: 'equipment', label: 'Weapons and armor', rows: rowsFrom(equipmentRecords, equipmentRow) },
  { root: 'races', label: 'Races', rows: rowsFrom(raceRecords, raceRow) },
  { root: 'conditions', label: 'Conditions', rows: rowsFrom(conditionRecords, (r) => namedRow('conditions', r)) },
  {
    root: 'weapon-properties',
    label: 'Weapon properties',
    rows: rowsFrom(propertyRecords, (r) => namedRow('weapon-properties', r)),
  },
]

// `?raw` imports a file's contents as a string; Vite's client types declare it.
export const corpus = once(() =>
  import('../../../data/srd-5.1/corpus.md?raw').then((m) => splitCorpus(m.default)),
)

export const supplement = once(() =>
  import('../../../data/srd-5.1/supplement.json').then((m) => m.default as Supplement),
)
