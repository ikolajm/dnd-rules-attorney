// A monster's full stat block from its record: the fields the corpus keeps,
// beside the armor class, saves, skills, alignment, XP, Multiattack and attacks
// it leaves out.
import { challengeText, type Ability, type ArmorClass, type MonsterRecord, type Usage } from '../rows.ts'
import { capitalized, size, type Line, type Section } from './section.ts'

// An ability, its usage kept apart from its name, "Fire Breath" and "Recharge
// 5-6", so the view can set it beside the name. `options` holds the named
// choices its text lists after a lead-in, each breath of a Breath Weapons; most
// abilities have none.
export type Trait = { name: string; usage?: string; text: string; options: Trait[] }

// Actions, Reactions or Legendary Actions.
export type Group = { heading: string; traits: Trait[] }

// The sections in block order, the languages, then the traits and each group.
export type Monster = {
  sections: Section[]
  languages: string
  traits: Trait[]
  groups: Group[]
}

// `as const` keeps each key a literal, so `record[key]` types as a number.
const SCORES = [
  ['Strength', 'strength'],
  ['Dexterity', 'dexterity'],
  ['Constitution', 'constitution'],
  ['Intelligence', 'intelligence'],
  ['Wisdom', 'wisdom'],
  ['Charisma', 'charisma'],
] as const

// Each damage section's heading beside the record's list for it, in the
// corpus's order.
const LEVELS = [
  ['Damage Vulnerabilities', 'damage_vulnerabilities'],
  ['Damage Resistances', 'damage_resistances'],
  ['Damage Immunities', 'damage_immunities'],
] as const

// A line that opens with a short name and a period, "Cold Breath. The dragon
// exhales…": up to five words, each capitalized or a small joining word, as in
// "Harmed by Running Water". A sentence fails it at its first lowercase word.
const OPTION = /^((?:[A-Z][A-Za-z']*|by|to|the|of|and)(?: (?:[A-Z][A-Za-z']*|by|to|the|of|and)){0,4})\. /

// "+8" or "−4". The minus is U+2212, as the printed SRD writes it, which a
// screen reader reads as minus where a hyphen may read as dash.
function signed(n: number): string {
  return n < 0 ? `−${-n}` : `+${n}`
}

// corpus.py's usage_text. Every member returns, so a fourth added to Usage
// fails to compile here until it is handled.
function usageText(usage: Usage): string {
  switch (usage.type) {
    case 'per day':
      return `${usage.times}/Day`
    case 'recharge on roll':
      return usage.min_value === 6 ? 'Recharge 6' : `Recharge ${usage.min_value}-6`
    case 'recharge after rest':
      return `Recharges after a ${usage.rest_types.map(capitalized).join(' or ')} Rest`
  }
}

// The text up to its first named line after the first, then an option per
// named line, as a metallic dragon's Breath Weapons. A line with no name joins
// the option above it rather than being lost.
function trait(ability: Ability): Trait {
  const name = ability.name
  const usage = ability.usage ? usageText(ability.usage) : undefined
  const lines = ability.desc.split('\n')
  const first = lines.findIndex((line, i) => i > 0 && OPTION.test(line))
  if (first === -1) return { name, usage, text: ability.desc, options: [] }
  const options: Trait[] = []
  for (const line of lines.slice(first)) {
    const match = OPTION.exec(line)
    if (match) options.push({ name: match[1], text: line.slice(match[0].length), options: [] })
    else options[options.length - 1].text += `\n${line}`
  }
  return { name, usage, text: lines.slice(0, first).join('\n'), options }
}

// One form for every entry, the value and then its source in parentheses,
// joined with commas when there are two: "12, 15 (with mage armor)".
function armorText(entry: ArmorClass): string {
  switch (entry.type) {
    case 'natural':
      return `${entry.value} (natural armor)`
    case 'dex':
      return String(entry.value)
    case 'armor':
      return `${entry.value} (${entry.desc ?? (entry.armor ?? []).map((a) => a.name.toLowerCase()).join(', ')})`
    case 'spell':
      return `${entry.value} (with ${entry.spell.name.toLowerCase()})`
    case 'condition':
      return `${entry.value} (while ${entry.condition.name.toLowerCase()})`
  }
}

// The saves or the skills, a row each. A save's "DEX" is named by the score
// whose key starts with it; a skill keeps its name.
function proficiencies(record: MonsterRecord, prefix: string): Line[] {
  return record.proficiencies
    .filter((p) => p.proficiency.name.startsWith(prefix))
    .map((p) => {
      const name = p.proficiency.name.slice(prefix.length)
      const score = SCORES.find(([, key]) => key.slice(0, 3).toUpperCase() === name)
      return { label: prefix === 'Saving Throw: ' && score ? score[0] : name, value: signed(p.value) }
    })
}

export function monsterFromRecord(record: MonsterRecord): Monster {
  // `hover` is a note on fly, not a mode.
  const speeds = Object.entries(record.speed)
    .filter(([mode]) => mode !== 'hover')
    .map(([mode, value]) => ({
      label: capitalized(mode),
      value: `${value}${mode === 'fly' && record.speed.hover ? ' (hover)' : ''}`,
    }))
  const senses = Object.entries(record.senses).map(([sense, value]) => ({
    label: sense === 'passive_perception' ? 'Passive Perception' : capitalized(sense),
    value: String(value),
  }))
  const groups: [string, Ability[] | undefined][] = [
    ['Actions', record.actions],
    ['Reactions', record.reactions],
    ['Legendary Actions', record.legendary_actions],
  ]

  const sections: Section[] = [
    {
      kind: 'rows',
      heading: 'Overview',
      lines: [
        { label: 'Size', value: record.size },
        { label: 'Type', value: `${capitalized(record.type)}${record.subtype ? ` (${record.subtype})` : ''}` },
        { label: 'Alignment', value: capitalized(record.alignment) },
      ],
    },
    {
      kind: 'rows',
      heading: 'Combat',
      lines: [
        { label: 'Armor Class', value: record.armor_class.map(armorText).join(', ') },
        // "19d12+133" as the corpus writes it, "19d12 + 133".
        { label: 'Hit Points', value: `${record.hit_points} (${record.hit_points_roll.replace(/([+-])/g, ' $1 ')})` },
      ],
    },
    { kind: 'rows', heading: 'Movement', lines: speeds },
    {
      kind: 'rows',
      heading: 'Challenge',
      lines: [
        { label: 'Challenge Rating', value: challengeText(record.challenge_rating) },
        { label: 'Experience', value: `${record.xp.toLocaleString('en-US')} XP` },
        { label: 'Proficiency Bonus', value: signed(record.proficiency_bonus) },
      ],
    },
    {
      kind: 'rows',
      heading: 'Abilities',
      lines: SCORES.map(([label, key]) => ({
        label,
        value: `${record[key]} (${signed(Math.floor((record[key] - 10) / 2))})`,
      })),
    },
    { kind: 'rows', heading: 'Saving Throws', lines: proficiencies(record, 'Saving Throw: ') },
    { kind: 'rows', heading: 'Skills', lines: proficiencies(record, 'Skill: ') },
    ...LEVELS.map(([heading, key]): Section => ({ kind: 'list', heading, items: record[key].map(capitalized) })),
    {
      kind: 'list',
      heading: 'Condition Immunities',
      items: record.condition_immunities.map((c) => c.name),
    },
    { kind: 'rows', heading: 'Senses', lines: senses },
  ]

  return {
    sections: sections.filter((s) => size(s) > 0),
    // `||`: `??` replaces only null and undefined, and '' is neither.
    languages: record.languages || '—',
    traits: (record.special_abilities ?? []).map(trait),
    // Length, not presence: a monster's actions can be an empty list.
    groups: groups.flatMap(([heading, list]) => (list?.length ? [{ heading, traits: list.map(trait) }] : [])),
  }
}
