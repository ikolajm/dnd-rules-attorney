import type { Spell } from './spell.ts'

type Props = {
  spell: Spell
}

const yesNo = (value: boolean) => (value ? 'Yes' : 'No')

// A spell's stat lines as label and value rows, above its description. The
// components are rows like the rest, where the corpus's Components line sat:
// verbal and somatic as Yes or No, and the material sentence when the spell has
// one. The look is provisional until the design sweep.
export function SpellStats({ spell }: Props) {
  return (
    <div className="spell-stats">
      <p className="eyebrow text-label-md">{spell.subtitle}</p>
      <dl className="spell-stats__rows text-body-md">
        <dt>Casting Time</dt>
        <dd>{spell.castingTime}</dd>
        <dt>Range</dt>
        <dd>{spell.range}</dd>
        <dt>Verbal</dt>
        <dd>{yesNo(spell.verbal)}</dd>
        <dt>Somatic</dt>
        <dd>{yesNo(spell.somatic)}</dd>
        <dt>Material</dt>
        <dd>{spell.material ?? 'No'}</dd>
        <dt>Duration</dt>
        <dd>{spell.duration}</dd>
      </dl>
    </div>
  )
}
