// A load the screen says the state of: loading, ready with its value, or
// failed, with a retry. The table's rows, a record's view, an entry's source
// text and its pull-outs all load this way.
import { useEffect, useRef, useState } from 'react'

// A union, so a check on `status` narrows to the variant holding the value.
export type Load<T> = { status: 'loading' } | { status: 'ready'; value: T } | { status: 'failed' }

// `key` names what is loaded, a path or a kind: a new key loads afresh, and a
// null one loads nothing. `load` may be a new function each render; the one
// from the latest render runs.
export function useLoad<T>(key: string | null, load: () => Promise<T>): { state: Load<T>; retry: () => void } {
  // Tagged with its key, so a component kept mounted across keys never shows the last key's value.
  const [loaded, setLoaded] = useState<{ key: string | null } & Load<T>>({ key, status: 'loading' })
  const [attempt, setAttempt] = useState(0)
  // Read by the effect below without listing it, which would rerun the load
  // every render. Written in an effect, since a ref is not written during render.
  const latest = useRef(load)
  useEffect(() => {
    latest.current = load
  })

  // `current` drops a load a later key has overtaken.
  useEffect(() => {
    if (key === null) return
    let current = true
    setLoaded({ key, status: 'loading' })
    latest
      .current()
      .then((value) => {
        if (current) setLoaded({ key, status: 'ready', value })
      })
      .catch((error: unknown) => {
        console.error(error)
        if (current) setLoaded({ key, status: 'failed' })
      })
    return () => {
      current = false
    }
  }, [key, attempt])

  const retry = () => setAttempt((a) => a + 1)
  if (loaded.key !== key) return { state: { status: 'loading' }, retry }
  const { key: _, ...state } = loaded
  return { state, retry }
}
