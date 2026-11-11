// Run with `node --test src/encyclopedia/views/monster.test.ts` from web/.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { entryBody } from '../../shared/entry.ts'
import { monsterFromRecord, type Monster, type Trait } from './monster.ts'
import type { Line, Section } from './section.ts'
import { CORPUS, MONSTERS } from '../../shared/test-data.ts'
import type { MonsterRecord } from '../rows.ts'

function byIndex(index: string): Monster {
  const record = MONSTERS.find((m) => m.index === index)
  assert.ok(record, index)
  return monsterFromRecord(record)
}

function section(monster: Monster, heading: string): Section | undefined {
  return monster.sections.find((s) => s.heading === heading)
}

// A section's rows, [] when it was dropped or is a list.
function lines(monster: Monster, heading: string): Line[] {
  const found = section(monster, heading)
  return found?.kind === 'rows' ? found.lines : []
}

// A list section's items, [] when it was dropped or is rows.
function items(monster: Monster, heading: string): string[] {
  const found = section(monster, heading)
  return found?.kind === 'list' ? found.items : []
}

function row(monster: Monster, heading: string, label: string): string | undefined {
  return lines(monster, heading).find((l) => l.label === label)?.value
}

// A damage section's items back as the record's entries, each first letter
// lowercased again.
function level(monster: Monster, heading: string): string[] {
  return items(monster, heading).map((entry) => entry.charAt(0).toLowerCase() + entry.slice(1))
}

// The corpus writes `none` for an empty list.
const joined = (list: string[], separator: string) => list.join(separator) || 'none'

// An ability as the corpus writes it, its usage back in its name and its options
// back on lines of their own.
const text = (t: Trait): string =>
  [`${t.name}${t.usage ? ` (${t.usage})` : ''}. ${t.text}`, ...t.options.map(text)].join('\n')

// Text as its non-blank lines. The corpus breaks some abilities with blank
// lines and the view's options rejoin them with single ones, so both sides are
// compared line by line.
const textLines = (text: string) => text.split(/\n+/).filter((l) => l !== '')

// The view's abilities as the corpus writes them, its group headings among
// them, as lines.
function paragraphs(monster: Monster): string[] {
  return [...monster.traits.map(text), ...monster.groups.flatMap((g) => [g.heading, ...g.traits.map(text)])].flatMap(
    textLines,
  )
}

// The corpus is the model's text, so each line it writes, rebuilt from the
// view's rows, reads the same.
test('every monster reads as its corpus text does, on the fields both write', () => {
  for (const record of MONSTERS) {
    const path = `monsters > ${record.index}`
    const entry = CORPUS.get(path)
    assert.ok(entry, path)
    // The stat lines, then the ability paragraphs.
    const [head, ...rest] = entryBody(entry).split('\n\n')
    const corpus = new Map(
      head.split('\n').map((line): [string, string] => {
        const at = line.indexOf(': ')
        return [line.slice(0, at).toLowerCase(), line.slice(at + 2)]
      }),
    )
    const monster = monsterFromRecord(record)
    // The corpus's value for a label, and the message naming it.
    const field = (label: string) => [corpus.get(label), `${path}: ${label}`] as const

    assert.equal(row(monster, 'Overview', 'Size'), ...field('size'))
    const type = corpus.get('type') ?? ''
    assert.ok(row(monster, 'Overview', 'Type')?.startsWith(type.charAt(0).toUpperCase() + type.slice(1)), path)
    assert.equal(row(monster, 'Combat', 'Hit Points'), ...field('hit points'))
    // Walk's distance stands alone; every other mode is named.
    const speed = lines(monster, 'Movement').map((l) => (l.label === 'Walk' ? l.value : `${l.label.toLowerCase()} ${l.value}`))
    assert.equal(speed.join(', '), ...field('speed'))
    assert.equal(
      lines(monster, 'Abilities')
        .map((l) => `${l.label.slice(0, 3)} ${l.value.split(' ')[0]}`)
        .join(', '),
      ...field('abilities'),
    )
    assert.equal(joined(level(monster, 'Damage Vulnerabilities'), '; '), ...field('damage vulnerabilities'))
    assert.equal(joined(level(monster, 'Damage Resistances'), '; '), ...field('damage resistances'))
    assert.equal(joined(level(monster, 'Damage Immunities'), '; '), ...field('damage immunities'))
    assert.equal(joined(items(monster, 'Condition Immunities'), ', '), ...field('condition immunities'))
    const senses = lines(monster, 'Senses').map((l) => (l.label === 'Passive Perception' ? `passive Perception ${l.value}` : `${l.label.toLowerCase()} ${l.value}`))
    assert.equal(senses.join(', '), ...field('senses'))
    assert.equal(monster.languages === '—' ? 'none' : monster.languages, ...field('languages'))
    assert.equal(row(monster, 'Challenge', 'Challenge Rating'), ...field('challenge'))
    // Dropping what the corpus leaves out, the attacks, Multiattack and an
    // emptied group's heading, leaves its own lines in its order.
    const corpusLines = rest.flatMap(textLines)
    assert.deepEqual(
      paragraphs(monster).filter((p) => corpusLines.includes(p)),
      corpusLines,
      path,
    )
  }
})

// The cast in load.ts checks a union only loosely, so these hold each shape.
test('each armor class shape reads as its source', () => {
  for (const [index, expected] of [
    ['adult-red-dragon', '19 (natural armor)'],
    ['acolyte', '10'],
    ['goblin', '15 (leather armor, shield)'],
    ['skeleton', '13 (armor scraps)'],
    ['archmage', '12, 15 (with mage armor)'],
    ['ankheg', '14 (natural armor), 11 (while prone)'],
  ]) {
    assert.equal(row(byIndex(index), 'Combat', 'Armor Class'), expected, index)
  }
})

test("a stat block's rows, and the sections it drops", () => {
  const dragon = byIndex('adult-red-dragon')
  assert.deepEqual(
    lines(dragon, 'Saving Throws').map((l) => `${l.label} ${l.value}`),
    ['Dexterity +6', 'Constitution +13', 'Wisdom +7', 'Charisma +11'],
  )
  assert.equal(row(dragon, 'Skills', 'Perception'), '+13')
  assert.equal(row(dragon, 'Challenge', 'Experience'), '18,000 XP')
  assert.equal(row(dragon, 'Challenge', 'Proficiency Bonus'), '+6')
  assert.equal(row(dragon, 'Abilities', 'Strength'), '27 (+8)')
  assert.deepEqual(items(dragon, 'Damage Immunities'), ['Fire'])
  // An empty list is dropped as an empty set of rows is.
  assert.equal(section(dragon, 'Damage Resistances'), undefined)
  assert.equal(dragon.groups[0].traits[0].name, 'Multiattack')
  // Str 3. The minus is U+2212, as monster.ts writes it.
  assert.equal(row(byIndex('awakened-shrub'), 'Abilities', 'Strength'), '3 (−4)')
  const ankheg = byIndex('ankheg')
  assert.equal(
    ankheg.sections.some((s) => s.heading === 'Saving Throws'),
    false,
  )
  assert.equal(ankheg.languages, '—')
  assert.equal(row(byIndex('acolyte'), 'Challenge', 'Challenge Rating'), '1/4')
  // A bullet per entry, a type or one with a condition, in the record's order.
  const air = byIndex('air-elemental')
  assert.deepEqual(items(air, 'Damage Resistances'), [
    'Lightning',
    'Thunder',
    'Bludgeoning, piercing, and slashing from nonmagical weapons',
  ])
  assert.deepEqual(items(byIndex('werewolf-human'), 'Damage Immunities'), [
    "Bludgeoning, piercing, and slashing from nonmagical weapons that aren't silvered",
  ])
  // Condition immunities are a list of their own.
  assert.deepEqual(items(byIndex('adult-green-dragon'), 'Condition Immunities'), ['Poisoned'])
  assert.equal(row(air, 'Movement', 'Fly'), '90 ft. (hover)')
  assert.equal(row(air, 'Movement', 'Walk'), undefined)
})

test("an ability's named options list apart from its lead-in", () => {
  const silver = byIndex('adult-silver-dragon')
  const breath = silver.groups[0].traits.find((t) => t.name === 'Breath Weapons')
  assert.ok(breath)
  assert.equal(breath.text, 'The dragon uses one of the following breath weapons.')
  assert.deepEqual(
    breath.options.map((o) => o.name),
    ['Cold Breath', 'Paralyzing Breath'],
  )
  const vampire = byIndex('vampire-vampire').traits.find((t) => t.name === 'Vampire Weaknesses')
  assert.deepEqual(
    vampire?.options.map((o) => o.name),
    ['Forbiddance', 'Harmed by Running Water', 'Stake to the Heart', 'Sunlight Hypersensitivity'],
  )
  // A usage stays apart from the name.
  const fire = byIndex('adult-red-dragon').groups[0].traits.find((t) => t.name === 'Fire Breath')
  assert.equal(fire?.usage, 'Recharge 5-6')
  // The dragons' 20, the androsphinx's Roar and the four vampires'.
  const optioned = MONSTERS.map(monsterFromRecord).flatMap((m) =>
    [...m.traits, ...m.groups.flatMap((g) => g.traits)].filter((t) => t.options.length > 0),
  )
  assert.equal(optioned.length, 25)
})

// No option in the data runs past its own line, but one that did would lose
// its second line unless it joins the option above. A copied vampire with a
// line added after Forbiddance stands in for it.
test("an unnamed line after an option stays that option's", () => {
  const record = MONSTERS.find((m) => m.index === 'vampire-vampire')
  assert.ok(record)
  const extra = 'An added line with no name.'
  const copy: MonsterRecord = {
    ...record,
    special_abilities: (record.special_abilities ?? []).map((a) =>
      a.name === 'Vampire Weaknesses' ? { ...a, desc: a.desc.replace(/(Forbiddance\. [^\n]*)/, `$1\n${extra}`) } : a,
    ),
  }
  const weaknesses = monsterFromRecord(copy).traits.find((t) => t.name === 'Vampire Weaknesses')
  assert.ok(weaknesses?.options[0].text.endsWith(`\n${extra}`))
})
