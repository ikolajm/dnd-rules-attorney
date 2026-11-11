// Run with `node --test src/encyclopedia/views/magic-item.test.ts` from web/.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { entryBody } from '../../entry.ts'
import { CORPUS, MAGIC_ITEMS as RECORDS } from '../../test-data.ts'
import { magicItemFromRecord, type MagicItem } from './magic-item.ts'

const BY_INDEX = new Map(RECORDS.map((r) => [r.index, r] as const))

function byIndex(index: string): MagicItem {
  const record = BY_INDEX.get(index)
  assert.ok(record, index)
  return magicItemFromRecord(record, BY_INDEX)
}

// A section's rows as [label, value] pairs, [] when it was dropped.
function pairs(item: MagicItem, heading: string): [string, string][] {
  const found = item.sections.find((s) => s.heading === heading)
  return found?.kind === 'rows' ? found.lines.map((l): [string, string] => [l.label, l.value]) : []
}

function row(item: MagicItem, label: string): string | undefined {
  return pairs(item, 'Overview').find(([l]) => l === label)?.[1]
}

// The corpus is the model's text, so each line it writes, rebuilt from the
// view's rows, reads the same.
test('every magic item reads as its corpus text does', () => {
  // A variant makes no row and no corpus entry.
  for (const record of RECORDS.filter((r) => !r.variant)) {
    const path = `magic-items > ${record.index}`
    const entry = CORPUS.get(path)
    assert.ok(entry, path)
    // The field lines, then the description.
    const body = entryBody(entry)
    const at = body.indexOf('\n\n')
    const [head, description] = at === -1 ? [body, ''] : [body.slice(0, at), body.slice(at + 2)]
    const corpus = new Map(
      head.split('\n').map((line): [string, string] => {
        const colon = line.indexOf(': ')
        return [line.slice(0, colon), line.slice(colon + 2)]
      }),
    )
    const item = magicItemFromRecord(record, BY_INDEX)
    const lower = (text = '') => text.charAt(0).toLowerCase() + text.slice(1)

    assert.equal(row(item, 'Type'), corpus.get('Type'), `${path}: type`)
    assert.equal(lower(row(item, 'Rarity')), corpus.get('Rarity'), `${path}: rarity`)
    const attunement = row(item, 'Attunement')
    assert.equal(
      attunement === 'None' ? 'none' : attunement?.replace('Required', 'requires attunement'),
      corpus.get('Attunement'),
      `${path}: attunement`,
    )
    // The corpus leaves out a variant named as its item is.
    const variants = pairs(item, 'Variants')
      .map(([name]) => name)
      .filter((name) => name !== record.name)
    assert.equal(variants.join('; ') || undefined, corpus.get('Variants'), `${path}: variants`)
    assert.equal(item.description, description, `${path}: description`)
  }
})

test("an item's rows", () => {
  // The commas inside the parentheses are not the split.
  const adamantine = byIndex('adamantine-armor')
  assert.equal(row(adamantine, 'Type'), 'Armor (medium or heavy, but not hide)')
  assert.equal(row(adamantine, 'Attunement'), 'None')
  assert.deepEqual(pairs(adamantine, 'Variants'), [])
  assert.equal(row(byIndex('amulet-of-health'), 'Attunement'), 'Required')
  assert.equal(row(byIndex('ring-of-shooting-stars'), 'Attunement'), 'Required outdoors at night')
  assert.deepEqual(pairs(byIndex('ammunition'), 'Variants'), [
    ['Ammunition, +1', 'Uncommon'],
    ['Ammunition, +2', 'Rare'],
    ['Ammunition, +3', 'Very rare'],
  ])
  // The variant named as its item is kept: its rarity tells the potions apart.
  assert.deepEqual(pairs(byIndex('potion-of-healing'), 'Variants')[0], ['Potion of Healing', 'Common'])
  // A table's rows are closed up, with no blank line between them.
  assert.match(byIndex('apparatus-of-the-crab').description, /\|\n\|/)
  assert.doesNotMatch(byIndex('apparatus-of-the-crab').description, /\|\n\n\|/)
})

// Every variant's first line splits as an item's does, so none throws or
// leaves its rarity empty.
test("every variant's rarity reads from its first line", () => {
  for (const record of RECORDS.filter((r) => r.variants.length > 0)) {
    for (const [name, rarity] of pairs(magicItemFromRecord(record, BY_INDEX), 'Variants')) {
      assert.notEqual(rarity, '', `${record.index}: ${name}`)
    }
  }
})
