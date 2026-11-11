// Run with `node --test src/encyclopedia/views/roots.test.ts` from web/.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { SUPPLEMENT } from '../../test-data.ts'
import { hasView } from './roots.ts'

// A record's view is built from the record, not the corpus text the supplement
// was added to, so a passage adding to it would go unshown. The one kind it
// takes is a reaction spell's casting time, which spellFromRecord folds in.
test("every passage adding to a record's view is one the view takes", () => {
  for (const passage of SUPPLEMENT.passages) {
    if (passage.op === 'new' || !hasView(passage.path)) continue
    assert.ok(passage.op === 'insert' && passage.after.startsWith('Casting time: '), passage.path)
  }
})
