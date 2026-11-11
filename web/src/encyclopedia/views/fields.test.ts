// Run with `node --test src/encyclopedia/views/fields.test.ts` from web/.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { entryBody } from '../../entry.ts'
import { CORPUS, EQUIPMENT, RACES } from '../../test-data.ts'
import { equipmentRow, raceRow } from '../rows.ts'
import { corpusFields, type Fields } from './fields.ts'


function fields(path: string): Fields | null {
  const text = CORPUS.get(path)
  assert.ok(text, path)
  return corpusFields(path, entryBody(text))
}

// The fields back as the lines they were read from, in any order: the rows
// come first and the lists after them, whatever order the block had.
function lines(found: Fields): string[] {
  return found.sections.flatMap((s) =>
    s.kind === 'rows' ? s.lines.map((l) => `${l.label}: ${l.value}`) : [`${s.heading}: ${s.items.join(', ')}`],
  )
}

test("every weapon, armor and race with a row reads its fields, and they rebuild its block", () => {
  const paths = [
    ...EQUIPMENT.map(equipmentRow),
    ...RACES.map(raceRow),
  ].flatMap((row) => (row ? [row.path] : []))
  for (const path of paths) {
    const found = fields(path)
    assert.ok(found, path)
    const text = CORPUS.get(path) ?? ''
    const body = entryBody(text)
    const at = body.indexOf('\n\n')
    const block = at === -1 ? body : body.slice(0, at)
    // A list written "none" makes no section, so its line is set aside.
    const written = block.split('\n').filter((line) => !/^(Traits|Subraces|Properties|Forms): none$/.test(line))
    assert.deepEqual(lines(found).sort(), written.sort(), path)
  }
})

test("an entry's fields, lists and the text after them", () => {
  const longsword = fields('equipment > longsword')
  assert.ok(longsword)
  // Properties is a list, after the rows.
  assert.deepEqual(lines(longsword), [
    'Category: Martial melee weapon',
    'Damage: 1d8 slashing (1d10 two-handed)',
    'Properties: Versatile',
  ])
  assert.deepEqual(longsword.sections.find((s) => s.heading === 'Properties'), {
    kind: 'list',
    heading: 'Properties',
    items: ['Versatile'],
  })
  assert.equal(longsword.rest, '')
  const dwarf = fields('races > dwarf')
  assert.ok(dwarf)
  const traits = dwarf.sections.find((s) => s.heading === 'Traits')
  assert.equal(traits?.kind === 'list' ? traits.items.length : 0, 5)
  assert.deepEqual(dwarf.sections.find((s) => s.heading === 'Subraces'), {
    kind: 'list',
    heading: 'Subraces',
    items: ['Hill Dwarf'],
  })
  assert.ok(dwarf.rest.startsWith('***Speed.***'))
  // A human's traits are "none", so there is no Traits section.
  const human = fields('races > human')
  assert.ok(human)
  assert.equal(human.sections.find((s) => s.heading === 'Traits'), undefined)
  // Gear opens with prose, and a condition is not a root with fields.
  assert.equal(fields('equipment > acid-vial'), null)
  assert.equal(fields('conditions > blinded'), null)
})
