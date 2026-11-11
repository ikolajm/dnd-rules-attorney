// Server-sent events from text, one chunk at a time. Pure, with no fetch and no
// DOM, so Node can test it on its own.

export type RawEvent = {
  event: string
  data: string
}

// A function from each text chunk to the events that chunk completed. A chunk
// can end mid-line, so the unfinished line is held for the next one.
export function parser(): (chunk: string) => RawEvent[] {
  let partial = ''
  let event = ''
  let data: string[] = []

  return (chunk) => {
    const lines = (partial + chunk).split('\n')
    partial = lines.pop() ?? ''
    const done: RawEvent[] = []

    for (const raw of lines) {
      const line = raw.endsWith('\r') ? raw.slice(0, -1) : raw
      if (line.startsWith(':')) {
        // A comment, such as the keepalive FastAPI sends on a quiet stream.
        continue
      }
      if (line.startsWith('event: ')) {
        event = line.slice('event: '.length)
      } else if (line.startsWith('data: ')) {
        data.push(line.slice('data: '.length))
      } else if (line === '') {
        // A blank line ends the event.
        if (data.length > 0) done.push({ event, data: data.join('\n') })
        event = ''
        data = []
      }
    }
    return done
  }
}
