// A magic item's view: its sections, then its description as markdown, whose
// tables render as the panel's do.
import { Prose } from '../../Prose.tsx'
import type { MagicItem } from './magic-item.ts'
import { Sections } from './StatBlock.tsx'

export function MagicItemStats({ item }: { item: MagicItem }) {
  return (
    <div className="stat-block">
      <Sections sections={item.sections} />
      <h3 className="text-title-sm">Description</h3>
      <Prose>{item.description}</Prose>
    </div>
  )
}
