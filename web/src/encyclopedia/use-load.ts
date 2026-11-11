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
  // The state names the key it is for. A component that stays mounted while
  // its key changes, the side panel from entry to entry, would otherwise show
  // the last key's value on the first render after the switch.
  const [loaded, setLoaded] = useState<{ key: string | null } & Load<T>>({ key, status: 'loading' })
  // Raised by Retry, which the effect lists, so a retry loads the same key
  // again; `once` forgets a failed load, so it fetches afresh.
  const [attempt, setAttempt] = useState(0)
  // The latest `load`, read by the effect below without listing it: listed, a
  // function built each render would re-run the load every render. Set in an
  // effect, since a ref is not written during render; effects run in order, so
  // this one runs first.
  const latest = useRef(load)
  useEffect(() => {
    latest.current = load
  })

  // `current` drops a load a later key has overtaken, so its value cannot land
  // last. The screen says only that the load failed; the console says why.
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
  // The key is the state's own bookkeeping, left out of what the caller reads.
  const { key: _, ...state } = loaded
  return { state, retry }
}
