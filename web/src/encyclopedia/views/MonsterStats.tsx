// A monster's stat block as headed sections of rows or lists, then its abilities.
import { Badge } from '../../components/loom/badge.tsx'
import { Prose } from '../../Prose.tsx'
import type { Monster, Trait } from './monster.ts'
import { Sections } from './StatBlock.tsx'

// An ability as a title line, its usage a badge beside the name, then its
// text. The text is markdown: the spellcasting lists are bullets. Its options,
// each breath of a Breath Weapons, sit indented inside it. The name is an h4
// under its group's h3, an option's an h5, so a screen reader can step through
// them.
function TraitText({ trait }: { trait: Trait }) {
  return (
    <li>
      <div className="monster-stats__title">
        <h4 className="text-label-lg">{trait.name}</h4>
        {trait.usage && (
          <Badge size="sm" color="neutral" intensity="soft">
            {trait.usage}
          </Badge>
        )}
      </div>
      <Prose>{trait.text}</Prose>
      {trait.options.length > 0 && (
        <ul className="monster-stats__options">
          {trait.options.map((o) => (
            <li key={o.name}>
              <h5 className="text-label-md">{o.name}</h5>
              <Prose>{o.text}</Prose>
            </li>
          ))}
        </ul>
      )}
    </li>
  )
}

// A heading over its abilities. Names are unique within a monster's list.
function Abilities({ heading, traits }: { heading: string; traits: Trait[] }) {
  return (
    <>
      <h3 className="text-title-sm">{heading}</h3>
      <ul className="monster-stats__traits">
        {traits.map((t) => (
          <TraitText key={t.name} trait={t} />
        ))}
      </ul>
    </>
  )
}

// The panel's title is the h2, so every heading here is an h3, the level Prose
// gives a corpus heading. Languages is a line of text, not rows: its entries
// do not split into label and value.
export function MonsterStats({ monster }: { monster: Monster }) {
  return (
    <div className="stat-block monster-stats">
      <Sections sections={monster.sections} />
      <h3 className="text-title-sm">Languages</h3>
      <p className="text-body-md">{monster.languages}</p>
      {monster.traits.length > 0 && <Abilities heading="Traits" traits={monster.traits} />}
      {monster.groups.map((g) => (
        <Abilities key={g.heading} heading={g.heading} traits={g.traits} />
      ))}
    </div>
  )
}
