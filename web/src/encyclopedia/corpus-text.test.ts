// Run with `node --test src/encyclopedia/corpus-text.test.ts` from web/.
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { test } from 'node:test'
import { additions, splitCorpus, type Supplement } from './corpus-text.ts'

const MARKDOWN = readFileSync(new URL('../../../data/srd-5.1/corpus.md', import.meta.url), 'utf8')
const CORPUS = splitCorpus(MARKDOWN)
const SUPPLEMENT = JSON.parse(
  readFileSync(new URL('../../../data/srd-5.1/supplement.json', import.meta.url), 'utf8'),
) as Supplement

// Catches a dropped `.slice(1)` or `m` flag. It counts with the pattern the
// split cuts on, so a text holding a `## ` line would move both alike.
test('one entry per ## line', () => {
  assert.equal(CORPUS.size, MARKDOWN.match(/^## /gm)!.length)
})

// The split is safe only while no text holds a `## ` line. One that did would
// split off a key that is its heading and the lines under it, not a path.
test('every key is a path', () => {
  const strays = [...CORPUS.keys()].filter((key) => !/^[a-z0-9-]+( > [a-z0-9-]+)*$/.test(key))
  assert.deepEqual(strays, [])
})

// A rule section's root, a nested header, a spell, a monster and an entry the
// supplement makes.
test('each text opens with its title line', () => {
  const titles = [
    ['the-order-of-combat', 'The Order of Combat'],
    ['making-an-attack > melee-attacks > grappling', 'Grappling'],
    ['spells > fireball', 'Fireball'],
    ['monsters > skeleton', 'Skeleton'],
    ['inspiration', 'Inspiration'],
  ]
  for (const [path, title] of titles) {
    assert.ok(CORPUS.get(path)?.startsWith(`${title}\n`), path)
  }
})

// The last block has only the file's final newline after it.
test('the last entry ends where the file does', () => {
  assert.ok(CORPUS.get('legendary-creatures > legendary-actions')?.endsWith('its first turn in the combat.'))
})

test('an insertion reads with the text it follows', () => {
  assert.deepEqual(additions(SUPPLEMENT, 'spells > shield'), [
    {
      text: 'Casting time: 1 reaction, which you take when you are hit by an attack or targeted by the magic missile spell',
      pages: [179],
    },
  ])
})

test('an append reads as its paragraphs', () => {
  assert.deepEqual(additions(SUPPLEMENT, 'races > dwarf'), [
    {
      text: '***Speed.*** Your base walking speed is 25 feet. Your speed is not reduced by wearing heavy armor.',
      pages: [3],
    },
  ])
})

// Inspiration is an entry a `new` passage makes.
test('an entry the supplement leaves alone or makes has no additions', () => {
  assert.deepEqual(additions(SUPPLEMENT, 'spells > fireball'), [])
  assert.deepEqual(additions(SUPPLEMENT, 'inspiration'), [])
})

// Against the text the Python build wrote, which applied every passage.
test("every addition is in its entry's corpus text", () => {
  for (const path of new Set(SUPPLEMENT.passages.map((passage) => passage.path))) {
    for (const addition of additions(SUPPLEMENT, path)) {
      assert.ok(CORPUS.get(path)?.includes(addition.text), path)
    }
  }
})
