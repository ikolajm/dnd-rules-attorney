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

// Each file's address, which Vite writes for `?url`: the file served as it is
// in dev, and copied into dist/ under a hashed name in a build. An import's path
// must be a literal for Vite to find the file, so each is written out.
import conditionsUrl from '../../../data/srd-5.1/5e-SRD-Conditions.json?url'
import equipmentUrl from '../../../data/srd-5.1/5e-SRD-Equipment.json?url'
import magicItemsUrl from '../../../data/srd-5.1/5e-SRD-Magic-Items.json?url'
import monstersUrl from '../../../data/srd-5.1/5e-SRD-Monsters.json?url'
import racesUrl from '../../../data/srd-5.1/5e-SRD-Races.json?url'
import spellsUrl from '../../../data/srd-5.1/5e-SRD-Spells.json?url'
import propertiesUrl from '../../../data/srd-5.1/5e-SRD-Weapon-Properties.json?url'
import corpusUrl from '../../../data/srd-5.1/corpus.md?url'
import supplementUrl from '../../../data/srd-5.1/supplement.json?url'

// A file's response, refused unless it succeeded: fetch rejects only when the
// network fails, and resolves on a 404 or a 500. Fetched rather than imported,
// since a browser keeps a failed import() of a URL for the page's life, so a
// retry would reject again without asking the network.
async function fetched(url: string): Promise<Response> {
  const response = await fetch(url)
  if (!response.ok) throw new Error(`${url} answered ${response.status}`)
  return response
}

// A JSON file's contents as T. json() returns `any`, so T is only as true as
// the type the caller names. No runtime schema checks it: each loader names
// the type of the very file the URL serves, copied into the build under a
// hashed name, so no outside source can drift from what tsc read.
async function json<T>(url: string): Promise<T> {
  return (await fetched(url)).json() as Promise<T>
}

// One loader per file. Each names its file's own type, `typeof import(...)`, a
// type-only import that ships nothing, so the cast to a record type stays a
// checked one: tsc refuses a record type the file's shape does not fit, which
// json()'s `any` alone would take. Its cost is a slower full type check. The
// record view reads the exported loaders' records for its stat blocks; the rest
// are read only through KINDS.
export const spellRecords = once(() =>
  json<typeof import('../../../data/srd-5.1/5e-SRD-Spells.json')>(spellsUrl).then((r) => r as SpellRecord[]),
)
export const magicItemRecords = once(() =>
  json<typeof import('../../../data/srd-5.1/5e-SRD-Magic-Items.json')>(magicItemsUrl).then(
    (r) => r as MagicItemRecord[],
  ),
)
export const monsterRecords = once(() =>
  json<typeof import('../../../data/srd-5.1/5e-SRD-Monsters.json')>(monstersUrl).then((r) => r as MonsterRecord[]),
)
const equipmentRecords = once(() =>
  json<typeof import('../../../data/srd-5.1/5e-SRD-Equipment.json')>(equipmentUrl).then(
    (r) => r as EquipmentRecord[],
  ),
)
const raceRecords = once(() =>
  json<typeof import('../../../data/srd-5.1/5e-SRD-Races.json')>(racesUrl).then((r) => r as RaceRecord[]),
)
const conditionRecords = once(() =>
  json<typeof import('../../../data/srd-5.1/5e-SRD-Conditions.json')>(conditionsUrl).then((r) => r as NamedRecord[]),
)
const propertyRecords = once(() =>
  json<typeof import('../../../data/srd-5.1/5e-SRD-Weapon-Properties.json')>(propertiesUrl).then(
    (r) => r as NamedRecord[],
  ),
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

export const corpus = once(async () => splitCorpus(await (await fetched(corpusUrl)).text()))

export const supplement = once(() =>
  json<typeof import('../../../data/srd-5.1/supplement.json')>(supplementUrl).then((s) => s as Supplement),
)
