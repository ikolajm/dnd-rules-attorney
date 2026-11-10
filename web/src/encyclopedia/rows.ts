// Each kind's source record from data/srd-5.1/, holding only the keys a row
// reads, and the Row every kind maps into, so one table and one filter serve all.

export type Field = string | string[]

export type Row = {
  // The corpus path, `spells > fireball`, which is how a cite names the record.
  path: string
  name: string
  // One column per key, in insertion order. A key that looks like an integer
  // would jump to the front, so labels are words.
  fields: Record<string, Field>
}

// A linked record as the files write it, a school, a class or a property. Its
// `url` is never read.
type Ref = { index: string; name: string }

// Every record's own index and name.
type Base = Ref

export type SpellRecord = Base & {
  // 0 for a cantrip.
  level: number
  school: Ref
  concentration: boolean
  ritual: boolean
  classes: Ref[]
}

export type MagicItemRecord = Base & {
  variant: boolean
  equipment_category: Ref
  rarity: { name: string }
  // The first paragraph is the line holding the attunement clause.
  desc: string[]
}

export type MonsterRecord = Base & {
  type: string
  size: string
  // 0.125, 0.25 and 0.5 below 1.
  challenge_rating: number
  damage_immunities: string[]
  condition_immunities: Ref[]
}

// Weapons and armor write the keys they do not use as null; the gear, tools
// and mounts in the same file may leave them out.
export type EquipmentRecord = Base & {
  equipment_category: Ref
  category_range?: string | null
  armor_category?: string | null
  properties?: Ref[] | null
}

export type RaceRecord = Base & {
  size: string
  speed: number
}

// Conditions and weapon properties, whose rows carry no fields.
export type NamedRecord = Base

// The corpus's own words for a boolean field.
function yesNo(value: boolean): string {
  return value ? 'yes' : 'no'
}

// A magic item's attunement clause, as item_fields in
// src/rules_attorney/corpus.py matches it. The corpus build refuses a first
// line with two, so only whether one is there is read. No `g` flag: with it,
// `test` keeps its place between calls.
const ATTUNEMENT = /\(requires attunement[^)]*\)/

// A Map keeps its keys numbers, where an object would turn them into strings.
const FRACTIONS = new Map([
  [0.125, '1/8'],
  [0.25, '1/4'],
  [0.5, '1/2'],
])

// A challenge rating as a stat block writes it: 1/8, 1/4 and 1/2 below 1, and
// any other rating as its number.
export function challengeText(rating: number): string {
  return FRACTIONS.get(rating) ?? String(rating)
}

// A record's row under its root, the one place the path is built. Conditions
// and weapon properties call it with no fields.
export function namedRow(root: string, record: NamedRecord, fields: Row['fields'] = {}): Row {
  return { path: `${root} > ${record.index}`, name: record.name, fields }
}

export function spellRow(record: SpellRecord): Row {
  return namedRow('spells', record, {
    Level: record.level === 0 ? 'cantrip' : String(record.level),
    School: record.school.name,
    Concentration: yesNo(record.concentration),
    Ritual: yesNo(record.ritual),
    Classes: record.classes.map((c) => c.name),
  })
}

// A variant makes no row: its parent holds the SRD text, and the corpus
// leaves variants out.
export function magicItemRow(record: MagicItemRecord): Row | null {
  if (record.variant) return null
  return namedRow('magic-items', record, {
    Category: record.equipment_category.name,
    Rarity: record.rarity.name,
    Attunement: yesNo(ATTUNEMENT.test(record.desc[0])),
  })
}

export function monsterRow(record: MonsterRecord): Row {
  return namedRow('monsters', record, {
    Type: record.type,
    Size: record.size,
    Challenge: challengeText(record.challenge_rating),
    'Damage immunities': record.damage_immunities,
    'Condition immunities': record.condition_immunities.map((c) => c.name),
  })
}

// Only weapons and armor: the gear in the corpus is chosen by GEAR_WITH_RULES
// in the Python build, and the foci are merged there. Armor reads "Heavy Armor"
// and the shield "Shield", as armor_lines writes them, so armor's category is
// not a bare "Heavy" beside the weapons'.
export function equipmentRow(record: EquipmentRecord): Row | null {
  const kind = record.equipment_category.index
  if (kind !== 'weapon' && kind !== 'armor') return null
  // A weapon fills category_range and armor armor_category; the type allows
  // null for the gear. A record missing its own is refused, not written blank.
  const named = kind === 'weapon' ? record.category_range : record.armor_category
  if (!named) throw new Error(`${record.index} has no ${kind} category`)
  return namedRow('equipment', record, {
    Category: kind === 'weapon' || named === 'Shield' ? named : `${named} Armor`,
    Properties: (record.properties ?? []).map((p) => p.name),
  })
}

export function raceRow(record: RaceRecord): Row {
  return namedRow('races', record, {
    Size: record.size,
    Speed: `${record.speed} feet`,
  })
}
