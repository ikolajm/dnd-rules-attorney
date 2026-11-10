// The filter and sort over a kind's rows, which the encyclopedia's table reads.
import { FRACTIONS, type Row } from './rows.ts'

// A challenge's text back to the rating it was written from, '1/8' to 0.125.
const CHALLENGES = new Map([...FRACTIONS].map(([rating, text]) => [text, rating]))

const SIZES = ['Tiny', 'Small', 'Medium', 'Large', 'Huge', 'Gargantuan']
// The source's `Varies` is not a rarity, so it sorts after the order.
const RARITIES = ['Common', 'Uncommon', 'Rare', 'Very Rare', 'Legendary', 'Artifact']

// A value's place in a fixed order, and a value outside it after the last.
// indexOf's -1 would put it first.
function position(order: string[], value: string): number {
  const at = order.indexOf(value)
  return at === -1 ? order.length : at
}

// The number an ordered field sorts by, or null for a field that sorts as text.
function rank(field: string, value: string): number | null {
  switch (field) {
    case 'Challenge':
      return CHALLENGES.get(value) ?? Number(value)
    case 'Level':
      return value === 'cantrip' ? 0 : Number(value)
    case 'Size':
      return position(SIZES, value)
    case 'Rarity':
      return position(RARITIES, value)
    default:
      return null
  }
}

// Two values of one field, for sort: negative when a comes first. An ordered
// field compares by rank, the nulls checked outright since a cantrip ranks 0;
// text, and two values tied on rank, by localeCompare, since sort without a
// comparator orders by UTF-16 code unit, Zombie before aberration.
export function compareValues(field: string, a: string, b: string): number {
  const ra = rank(field, a)
  const rb = rank(field, b)
  if (ra !== null && rb !== null && ra !== rb) return ra - rb
  return a.localeCompare(b)
}

// A field's value as a list, whether the row writes it as a string or a list:
// 'undead' as ['undead'], and an empty list as none.
export function members(row: Row, field: string): string[] {
  return [row.fields[field]].flat()
}

// The values one field takes across the rows, each once and in order, for that
// field's filter. A list field contributes each member, and an empty list none.
export function options(rows: Row[], field: string): string[] {
  const values = new Set<string>()
  for (const row of rows) {
    for (const value of members(row, field)) values.add(value)
  }
  // In the column's own order, so a challenge filter reads 0 to 30.
  return [...values].sort((a, b) => compareValues(field, a, b))
}

// Whether a row stays in the table: its name holds the search, ignoring case
// and outer spaces, and it holds the chosen value of every chosen field, a
// list field on any member. A field with nothing chosen has no key in
// `chosen`, so an empty one passes every row.
export function matches(row: Row, search: string, chosen: Record<string, string>): boolean {
  const needle = search.trim().toLowerCase()
  if (!row.name.toLowerCase().includes(needle)) return false
  return Object.entries(chosen).every(([field, value]) => members(row, field).includes(value))
}

// The name column's key. The name sits beside the fields, not in them, and no
// kind has a field of this label.
export const NAME = 'Name'

// A comparator over rows by one field, ascending, for rows.sort. A list field
// sorts by its first member, an empty one as '' and so first. The table
// reverses the sorted rows for descending.
export function compareRows(field: string): (a: Row, b: Row) => number {
  const key = (row: Row): string => (field === NAME ? row.name : (members(row, field)[0] ?? ''))
  return (a, b) => compareValues(field, key(a), key(b))
}
