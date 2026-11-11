// The fields a weapon, a piece of armor or a race writes as its corpus text's
// first block, "Category: Martial melee weapon", read as a stat block's
// sections. Their records hold no more than the corpus does, so the corpus is
// what this reads.
import { pathRoot } from '../../cites.ts'
import { size, type Line, type Section } from './section.ts'

// One field line: a label of letters and spaces, then its value.
const FIELD = /^([A-Z][A-Za-z ]*): (.+)$/

// The fields whose value is a comma list, set as bullets rather than one long
// value: a race's traits and subraces, a weapon's properties, a focus's forms.
const LISTS = new Set(['Traits', 'Subraces', 'Properties', 'Forms'])

// The roots whose entries open with a field block. Gear under equipment opens
// with prose instead, which fails FIELD on its first line.
const FIELD_ROOTS = new Set(['equipment', 'races'])

export type Fields = { sections: Section[]; rest: string }

// A body's first block as its field lines, label and value, and the text after
// it. `lines` is null when any line of the block is not a field: the block is
// prose, and `rest` is then the whole body.
export function splitFieldBlock(body: string): { lines: [string, string][] | null; rest: string } {
  const at = body.indexOf('\n\n')
  const block = at === -1 ? body : body.slice(0, at)
  const lines: [string, string][] = []
  for (const line of block.split('\n')) {
    const match = FIELD.exec(line)
    if (!match) return { lines: null, rest: body }
    lines.push([match[1], match[2]])
  }
  return { lines, rest: at === -1 ? '' : body.slice(at + 2) }
}

// The entry's fields and the text after them, or null for an entry with no
// field block, which renders as markdown.
export function corpusFields(path: string, body: string): Fields | null {
  if (!FIELD_ROOTS.has(pathRoot(path))) return null
  const { lines: fields, rest } = splitFieldBlock(body)
  if (fields === null) return null
  const lines: Line[] = []
  const lists: Section[] = []
  for (const [label, value] of fields) {
    // The corpus writes "none" for an empty list, a human's traits; no items,
    // so the section drops.
    if (LISTS.has(label)) lists.push({ kind: 'list', heading: label, items: value === 'none' ? [] : value.split(', ') })
    else lines.push({ label, value })
  }
  const sections: Section[] = [{ kind: 'rows', heading: 'Overview', lines }, ...lists]
  return { sections: sections.filter((s) => size(s) > 0), rest }
}
