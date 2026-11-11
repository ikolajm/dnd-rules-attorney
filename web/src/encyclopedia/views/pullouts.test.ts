// Run with `node --test src/encyclopedia/views/pullouts.test.ts` from web/.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { entryBody } from '../../entry.ts'
import { CORPUS, EQUIPMENT } from '../../test-data.ts'
import { equipmentRow } from '../rows.ts'
import { corpusFields } from './fields.ts'
import { propertyEntry, pulloutText, subraceEntries, traitEntries } from './pullouts.ts'

// An entry's list items under a heading, as its view lists them.
function items(path: string, heading: string): string[] {
  const fields = corpusFields(path, entryBody(CORPUS.get(path) ?? ''))
  const section = fields?.sections.find((s) => s.heading === heading)
  return section?.kind === 'list' ? section.items : []
}
const traits = (path: string) => items(path, 'Traits')

test("every race's traits find their entries", () => {
  const races = [...CORPUS.keys()].filter((path) => path.startsWith('races > '))
  assert.equal(races.length, 9)
  for (const race of races) {
    const names = traits(race)
    assert.deepEqual([...traitEntries(race, names, CORPUS).keys()], names, race)
  }
  // A trait several races hold is shared; one only the dwarf holds is its own.
  const dwarf = traitEntries('races > dwarf', traits('races > dwarf'), CORPUS)
  assert.equal(dwarf.get('Darkvision')?.path, 'racial-traits > darkvision')
  assert.equal(dwarf.get('Dwarven Resilience')?.path, 'racial-traits > dwarf > dwarven-resilience')
})

// No trait in the data has both, so a map built here holds the case.
test("a race's own trait is chosen over a shared one of the same title", () => {
  const texts = new Map([
    ['racial-traits > keen-senses', 'Keen Senses\n\nShared.'],
    ['racial-traits > elf > keen-senses', 'Keen Senses\n\nThe elf’s own.'],
    ['racial-traits > dwarf > keen-senses', 'Keen Senses\n\nAnother race’s.'],
  ])
  assert.equal(traitEntries('races > elf', ['Keen Senses'], texts).get('Keen Senses')?.path, 'racial-traits > elf > keen-senses')
  // A race without its own falls back to the shared one, not another race's.
  assert.equal(traitEntries('races > gnome', ['Keen Senses'], texts).get('Keen Senses')?.path, 'racial-traits > keen-senses')
})

// A subrace has no entry; its traits name it in a field line.
test("a subrace opens to the traits that name it", () => {
  assert.deepEqual(
    subraceEntries('races > dwarf', 'Hill Dwarf', CORPUS).map((e) => e.path),
    ['racial-traits > dwarf > hill-dwarf > dwarven-toughness'],
  )
  assert.equal(subraceEntries('races > elf', 'High Elf', CORPUS).length, 3)
})

test("every weapon's properties find their entries", () => {
  for (const row of EQUIPMENT.map(equipmentRow)) {
    if (!row) continue
    for (const name of items(row.path, 'Properties')) assert.ok(propertyEntry(name, CORPUS), `${row.path}: ${name}`)
  }
  assert.equal(propertyEntry('Two-Handed', CORPUS)?.path, 'weapon-properties > two-handed')
})

test('an entry opened in place leaves out the fields its view says', () => {
  const text = (path: string) => pulloutText({ path, text: CORPUS.get(path) ?? '' })
  const resilience = text('racial-traits > dwarf > dwarven-resilience')
  assert.ok(resilience.startsWith('You have advantage'), resilience)
  assert.ok(!resilience.includes('Race:'))
  // The table Draconic Ancestry's text refers to, a bullet per dragon.
  assert.ok(text('racial-traits > dragonborn > draconic-ancestry').includes('- Black: acid, 30 ft. line, Dex save\n'))
})
