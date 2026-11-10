// A load that runs on the first call and hands every later call the same
// promise. The promise is kept rather than its value, so two calls made while
// the load is still running wait on one request. A load that fails is
// forgotten, so the next call tries again: kept, its rejection would answer
// every call until the page reloads.
export function once<T>(load: () => Promise<T>): () => Promise<T> {
  let pending: Promise<T> | undefined
  return () =>
    (pending ??= load().catch((error: unknown) => {
      pending = undefined
      throw error
    }))
}
