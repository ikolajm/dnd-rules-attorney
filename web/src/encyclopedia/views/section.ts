// What every stat block is built from: headed sections of rows or of list
// items, shared by the monster's view and the magic item's.

// One row: "Armor Class", "19 (natural armor)".
export type Line = { label: string; value: string }

// A headed part of the block: rows of label and value, "Movement" and a row
// per speed, or a bulleted list, "Damage Resistances" and an entry each, whose
// entries are sentences too long to sit as a value. `kind` tells them apart.
export type Section =
  | { kind: 'rows'; heading: string; lines: Line[] }
  | { kind: 'list'; heading: string; items: string[] }

// A section's entries, rows or items. Every kind returns, so a third added to
// Section fails to compile here until it is counted.
export function size(section: Section): number {
  switch (section.kind) {
    case 'rows':
      return section.lines.length
    case 'list':
      return section.items.length
  }
}

export function capitalized(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}
