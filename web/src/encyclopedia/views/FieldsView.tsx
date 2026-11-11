// A weapon's, a piece of armor's or a race's fields as a stat block, then the
// text after them, which a weapon's entry often has none of.
import { Prose } from '../../shared/Prose.tsx'
import type { Fields } from './fields.ts'
import { Sections, type Expand } from './StatBlock.tsx'

// `expand` gives what a race's traits and subraces and a weapon's properties
// open to in place.
export function FieldsView({ fields, expand }: { fields: Fields; expand?: Expand }) {
  return (
    <div className="stat-block">
      <Sections sections={fields.sections} expand={expand} />
      {fields.rest !== '' && (
        <>
          <h3 className="text-title-sm">Description</h3>
          <Prose>{fields.rest}</Prose>
        </>
      )}
    </div>
  )
}
