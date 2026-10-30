import type { ErrorReason, Fixture, StreamEvent } from './types.ts'

// The dev source beside the live one: a fixture replayed at the timings level 3
// measured, in the shape `live` has, so the design sweep can bring up every
// state without Ollama running.

// Plan and ruling are dev medians from the level 3 run, and the gate is the
// gate check's fifth of a second. Retrieval was not timed on its own, so its
// delay is a guess.
const DELAY = { gate: 200, plan: 500, entries: 300, ruling: 2500 }

// How long the timeout scenario waits before failing. The server's limit is 30
// seconds; this is shorter so the state can be looked at without the wait.
const TIMEOUT_DEMO = 8000

// Dev only. Each failure the screen has to show, on any fixture. None of them
// is a recorded run: the refusal and the errors are synthesised here.
export const SCENARIOS = ['ruled', 'refused', 'unreachable', 'ruling-unparsed', 'timeout'] as const
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
    yield { event: 'gate', data: { about_rules: false } }
    return
  }
  yield take('gate')

  await wait(DELAY.plan, signal)
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
