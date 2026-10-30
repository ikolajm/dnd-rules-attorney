// Run with `node --test src/entry.test.ts` from web/.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { entryBody, entryTitle } from './entry.ts'

test('the title is the first line as the source writes it', () => {
  assert.equal(entryTitle('Fire Bolt\n\nLevel: cantrip'), 'Fire Bolt')
})

test('a title followed straight by a list is still the title', () => {
  // Strength's skills, as the corpus writes them, with no blank line after.
  assert.equal(entryTitle('Strength\n- Athletics'), 'Strength')
  assert.equal(entryBody('Strength\n- Athletics'), '- Athletics')
})

test('text with no line break has no title', () => {
  assert.equal(entryTitle('Grappled'), null)
})

test('the title line and the blank line after it are dropped', () => {
  assert.equal(entryBody('Blinded\n\n- A blinded creature cannot see.'), '- A blinded creature cannot see.')
})

test('table rows split by blank lines are joined, other blank lines kept', () => {
  // Control Weather's Precipitation table as the corpus writes it.
  const text = 'Wind\n\nFind a stage.\n\n| Stage | Condition |\n\n|---|---|\n\n| 1 | Clear |\n\nThen change it.'
  assert.equal(entryBody(text), 'Find a stage.\n\n| Stage | Condition |\n|---|---|\n| 1 | Clear |\n\nThen change it.')
})
