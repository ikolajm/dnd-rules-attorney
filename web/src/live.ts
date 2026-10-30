import { parser } from './sse.ts'
import type { StreamEvent } from './types.ts'

// The stream: a question in, the endpoint's events out, ended early by the
// signal.

const SERVER_DOWN: StreamEvent = { event: 'error', data: { reason: 'server-unreachable' } }

// Whether an event is one a run ends on.
function ends(e: StreamEvent): boolean {
  return e.event === 'ruling' || e.event === 'error' || (e.event === 'gate' && !e.data.about_rules)
}

export async function* live(question: string, signal: AbortSignal): AsyncGenerator<StreamEvent> {
  let response: Response
  try {
    response = await fetch('/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
      signal,
    })
  } catch (err) {
    // A stop aborts the fetch, and the screen handles that; anything else is a
    // server that could not be reached.
    if (signal.aborted) throw err
    yield SERVER_DOWN
    return
  }
  if (!response.ok || !response.body) {
    yield SERVER_DOWN
    return
  }

  // Read with getReader rather than `for await`, which Safari does not support
  // on a ReadableStream.
  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  const push = parser()
  let ended = false
  try {
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      for (const raw of push(value)) {
        // JSON arrives untyped. The cast is the boundary; the server writes
        // these shapes, mirrored in types.ts.
        const e = { event: raw.event, data: JSON.parse(raw.data) } as StreamEvent
        yield e
        if (ends(e)) ended = true
      }
    }
  } catch (err) {
    if (signal.aborted) throw err
    yield SERVER_DOWN
    return
  }
  // A stream that closes before the run ends would leave the screen at a stage
  // with nothing more to come.
  if (!ended) yield SERVER_DOWN
}
