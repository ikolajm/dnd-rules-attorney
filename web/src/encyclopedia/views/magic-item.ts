// A magic item's view from its record: the type, rarity and attunement its
// first line holds, its variants with their rarities, and its description.
import { joinTableRows } from '../../shared/entry.ts'
import { ATTUNEMENT, type MagicItemRecord } from '../rows.ts'
import { capitalized, size, type Section } from './section.ts'

export type MagicItem = { sections: Section[]; description: string }

// An item's first line, "Armor (medium or heavy, but not hide), uncommon", is
// its fields: the type before the first comma outside parentheses, then the
// rarity, then any attunement clause. A port of item_fields in
// src/rules_attorney/corpus.py, so the view reads the line as the corpus does.
// It throws on a line with no such comma, as the corpus build does; every item
// and variant in the data has one.
function firstLine(line: string): { type: string; rarity: string; attunement: string | null } {
  // How many parentheses are open at each character, so the commas inside
  // "(medium or heavy, but not hide)" are passed over.
  let depth = 0
  for (let i = 0; i < line.length; i++) {
    const char = line[i]
    if (char === '(') depth++
    else if (char === ')') depth--
    else if (char === ',' && depth === 0) {
      const rest = line.slice(i + 1)
      return {
        type: line.slice(0, i),
        rarity: rest.replace(ATTUNEMENT, '').trim(),
        attunement: ATTUNEMENT.exec(rest)?.[1] ?? null,
      }
    }
  }
  throw new Error(`no comma outside parentheses: ${line}`)
}

// The clause as a value: "None", "Required", "Required by a spellcaster".
function attunementText(clause: string | null): string {
  return clause === null ? 'None' : clause.replace('requires attunement', 'Required')
}

// `byIndex` holds every record in the file, the variants among them, which make
// no row of their own.
export function magicItemFromRecord(record: MagicItemRecord, byIndex: Map<string, MagicItemRecord>): MagicItem {
  const { type, rarity, attunement } = firstLine(record.desc[0])
  // Each variant's rarity from its own first line, so it reads as the item's
  // does. Potion of Healing lists itself among its variants, which the corpus
  // leaves out; here its row is the one that tells the four potions apart.
  const variants = record.variants.flatMap((ref) => {
    const variant = byIndex.get(ref.index)
    return variant ? [{ label: variant.name, value: capitalized(firstLine(variant.desc[0]).rarity) }] : []
  })
  const sections: Section[] = [
    {
      kind: 'rows',
      heading: 'Overview',
      lines: [
        { label: 'Type', value: type },
        { label: 'Rarity', value: capitalized(rarity) },
        { label: 'Attunement', value: attunementText(attunement) },
      ],
    },
    { kind: 'rows', heading: 'Variants', lines: variants },
  ]
  return {
    sections: sections.filter((s) => size(s) > 0),
    // The rest of the description, its tables closed up as a spell's are.
    description: joinTableRows(record.desc.slice(1).join('\n\n')),
  }
}
