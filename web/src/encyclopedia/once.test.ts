// Run with `node --test src/encyclopedia/once.test.ts` from web/.
import assert from 'node:assert/strict'
import { test } from 'node:test'
import { once } from './once.ts'

// A load that counts its runs and fails on the runs listed.
function counted(failing: number[]) {
  let runs = 0
  const load = once(async () => {
    runs += 1
    if (failing.includes(runs)) throw new Error(`run ${runs} failed`)
    return `run ${runs}`
  })
  return { load, runs: () => runs }
}

test('a load that succeeds runs once and is kept', async () => {
  const { load, runs } = counted([])
  assert.equal(await load(), 'run 1')
  assert.equal(await load(), 'run 1')
  assert.equal(runs(), 1)
})

test('calls made while a load is running share it', async () => {
  const { load, runs } = counted([])
  const [first, second] = await Promise.all([load(), load()])
  assert.equal(first, second)
  assert.equal(runs(), 1)
})

test('a failed load is tried again on the next call', async () => {
  const { load, runs } = counted([1])
  await assert.rejects(load(), /run 1 failed/)
  assert.equal(await load(), 'run 2')
  assert.equal(runs(), 2)
})
