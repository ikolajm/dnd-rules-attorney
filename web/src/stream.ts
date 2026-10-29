import type { ErrorReason, Fixture, StreamEvent } from './types.ts'

// The seam the live stream replaces: a question in, the endpoint's events out,
// ended early by the signal. Until the endpoint exists, a fixture is replayed
// at the timings level 3 measured on dev.

// Plan and ruling are dev medians from the level 3 run. The gate is not written
// and retrieval was not timed on its own, so those two are guesses.
const DELAY = { gate: 400, plan: 500, entries: 300, ruling: 2500 }

// How long the timeout scenario waits before failing, standing in for the
// server's limit, which is the endpoint's to set.
const TIMEOUT_DEMO = 8000

// Dev only. Each failure the screen has to show, on any fixture. None of them
// is a recorded run: the refusal and the errors are synthesised here.
export const SCENARIOS = ['ruled', 'refused', 'unreachable', 'plan-unparsed', 'ruling-unparsed', 'timeout'] as const
export type Scenario = (typeof SCENARIOS)[number]

function wait(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) return reject(signal.reason)
    const timer = setTimeout(resolve, ms)
    signal.addEventListener(
      'abort',
      () => {
        clearTimeout(timer)
        reject(signal.reason)
      },
      { once: true },
    )
  })
}

function error(reason: ErrorReason): StreamEvent {
  return { event: 'error', data: { reason } }
}

export async function* replay(fixture: Fixture, scenario: Scenario, signal: AbortSignal): AsyncGenerator<StreamEvent> {
  const recorded = new Map(fixture.events.map((e) => [e.event, e]))
  const take = (name: StreamEvent['event']) => recorded.get(name)!

  if (scenario === 'unreachable') {
    await wait(DELAY.gate, signal)
    yield error('unreachable')
    return
  }

  await wait(DELAY.gate, signal)
  if (scenario === 'refused') {
    yield { event: 'gate', data: { allowed: false } }
    return
  }
  yield take('gate')

  await wait(DELAY.plan, signal)
  if (scenario === 'plan-unparsed') {
    yield error('plan-unparsed')
    return
  }
  yield take('plan')

  await wait(DELAY.entries, signal)
  yield take('entries')

  if (scenario === 'timeout') {
    await wait(TIMEOUT_DEMO, signal)
    yield error('timeout')
    return
  }
  await wait(DELAY.ruling, signal)
  yield scenario === 'ruling-unparsed' ? error('ruling-unparsed') : take('ruling')
}
