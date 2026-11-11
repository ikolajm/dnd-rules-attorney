// The entries a race's or a weapon's list items open to in place: a race's
// traits and subraces, a weapon's properties. Matched by title and by field
// line rather than built as paths: corpus.py sets a trait's path by how widely
// its text is shared, `racial-traits > darkvision` for one several races hold,
// `racial-traits > dwarf > stonecunning` for one only the dwarf does, and that
// rule stays in Python alone.
import { pathLeaf } from '../../cites.ts'
import { entryBody, entryTitle } from '../../entry.ts'
import type { Entry } from '../../types.ts'
import { splitFieldBlock } from './fields.ts'
import type { Section } from './section.ts'

// The first entry in scope with this title.
function titled(texts: Map<string, string>, name: string, inScope: (path: string) => boolean): Entry | undefined {
  for (const [path, text] of texts) {
    if (inScope(path) && entryTitle(text) === name) return { path, text }
  }
  return undefined
}

// Each name's entry: the one under the race's own path first, then a shared
// one, directly under `racial-traits`. A name with neither is left out, and
// its view shows it as a plain item.
export function traitEntries(racePath: string, names: string[], texts: Map<string, string>): Map<string, Entry> {
  const race = pathLeaf(racePath)
  const found = new Map<string, Entry>()
  for (const name of names) {
    const entry =
      titled(texts, name, (p) => p.startsWith(`racial-traits > ${race} > `)) ??
      titled(texts, name, (p) => p.startsWith('racial-traits > ') && p.split(' > ').length === 2)
    if (entry) found.set(name, entry)
  }
  return found
}

// A subrace's traits. The data holds no subrace entry of its own; each of its
// traits names it in a field line, "Subrace: Hill Dwarf".
export function subraceEntries(racePath: string, name: string, texts: Map<string, string>): Entry[] {
  const prefix = `racial-traits > ${pathLeaf(racePath)} > `
  const found: Entry[] = []
  for (const [path, text] of texts) {
    if (!path.startsWith(prefix)) continue
    const { lines } = splitFieldBlock(entryBody(text))
    if (lines?.some(([label, value]) => label === 'Subrace' && value === name)) found.push({ path, text })
  }
  return found
}

// A weapon property's entry, titled as the weapon's Properties line names it.
export function propertyEntry(name: string, texts: Map<string, string>): Entry | undefined {
  return titled(texts, name, (p) => p.startsWith('weapon-properties > '))
}

// The headings whose items open in place.
export const PULLOUT_HEADINGS = new Set(['Traits', 'Subraces', 'Properties'])

// By heading, then by item: the entries each opens to. A trait or a property
// opens to one, a subrace to its traits. An item with none is left out.
export type Pullouts = Map<string, Map<string, Entry[]>>

export function pullouts(path: string, sections: Section[], texts: Map<string, string>): Pullouts {
  const found: Pullouts = new Map()
  for (const section of sections) {
    if (section.kind !== 'list') continue
    const items = new Map<string, Entry[]>()
    if (section.heading === 'Traits') {
      for (const [name, entry] of traitEntries(path, section.items, texts)) items.set(name, [entry])
    } else if (section.heading === 'Subraces') {
      for (const name of section.items) {
        const entries = subraceEntries(path, name, texts)
        if (entries.length > 0) items.set(name, entries)
      }
    } else if (section.heading === 'Properties') {
      for (const name of section.items) {
        const entry = propertyEntry(name, texts)
        if (entry) items.set(name, [entry])
      }
    }
    if (items.size > 0) found.set(section.heading, items)
  }
  return found
}

// The field lines the view around a pull-out already says: the race it sits
// under, or every race that shares it.
const SAID = new Set(['Race', 'Races', 'Subrace'])

// An entry's text as it reads opened in place: its body without the field
// lines its view already says. Draconic Ancestry's Options, the table its text
// refers to, become a bulleted list, one per dragon.
export function pulloutText(entry: Entry): string {
  const { lines, rest } = splitFieldBlock(entryBody(entry.text))
  if (lines === null) return rest
  const kept = lines
    .filter(([label]) => !SAID.has(label))
    .map(([label, value]) =>
      label === 'Options' ? value.split('; ').map((option) => `- ${option}`).join('\n') : `${label}: ${value}`,
    )
  return [...(kept.length > 0 ? [kept.join('\n')] : []), ...(rest ? [rest] : [])].join('\n\n')
}
