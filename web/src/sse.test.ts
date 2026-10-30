// Run with `node --test src/sse.test.ts` from web/. Node strips the types and
// runs the file as written.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { parser } from './sse.ts'

test('a line split across two chunks parses as one event', () => {
  const push = parser()
  assert.deepEqual(push('event: plan\ndata: {"sub_questions": ["What does gra'), [])
  assert.deepEqual(push('ppled do?"]}\n\n'), [
    { event: 'plan', data: '{"sub_questions": ["What does grappled do?"]}' },
  ])
})

test('the keepalive comment yields nothing', () => {
  assert.deepEqual(parser()(': ping\n\n'), [])
})

test('two events in one chunk yield both, in order', () => {
  const events = parser()('event: gate\ndata: {"about_rules": true}\n\nevent: plan\ndata: {"sub_questions": []}\n\n')
  assert.deepEqual(events, [
    { event: 'gate', data: '{"about_rules": true}' },
    { event: 'plan', data: '{"sub_questions": []}' },
  ])
})

test('an event the stream ends before finishing yields nothing', () => {
  // The data line is whole and only the blank line that ends the event is
  // missing, so this is the event's end being waited for, not a line's.
  assert.deepEqual(parser()('event: ruling\ndata: {"explanation": "Grappled only sets speed to 0."}\n'), [])
})
