// The loading of a path's view, built from its record: a spell's, a monster's
// or a magic item's. Apart from RecordView.tsx so that file exports only its
// component, which Vite's fast refresh needs to swap it in place.
import { pathLeaf } from '../../shared/cites.ts'
import { spellFromRecord, type Spell } from './spell.ts'
import { magicItemRecords, monsterRecords, spellRecords, supplement } from '../load.ts'
import { magicItemFromRecord, type MagicItem } from './magic-item.ts'
import { monsterFromRecord, type Monster } from './monster.ts'
import { rootOf } from './roots.ts'

export type View =
  | { kind: 'spell'; spell: Spell }
  | { kind: 'monster'; monster: Monster }
  | { kind: 'magic-item'; item: MagicItem }

// The view for a path, null when its root has none or no record has its
// index. From the table the records are already loaded, its rows coming from
// the same `once`, so this resolves at once. Every root returns, so one added
// to ROOTS fails to compile here until it is handled.
export async function loadView(path: string): Promise<View | null> {
  const root = rootOf(path)
  if (root === null) return null
  // "monsters > aboleth" to "aboleth".
  const index = pathLeaf(path)
  switch (root) {
    case 'spells': {
      // Both files at once, rather than one after the other: a spell's casting
      // time may take the supplement's insert.
      const [records, passages] = await Promise.all([spellRecords(), supplement()])
      const record = records.find((r) => r.index === index)
      return record ? { kind: 'spell', spell: spellFromRecord(record, passages) } : null
    }
    case 'monsters': {
      const record = (await monsterRecords()).find((r) => r.index === index)
      return record ? { kind: 'monster', monster: monsterFromRecord(record) } : null
    }
    case 'magic-items': {
      // Every record by index, so the item's variants are found by theirs.
      const byIndex = new Map((await magicItemRecords()).map((r) => [r.index, r] as const))
      const record = byIndex.get(index)
      return record ? { kind: 'magic-item', item: magicItemFromRecord(record, byIndex) } : null
    }
  }
}
