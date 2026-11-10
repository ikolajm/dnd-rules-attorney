// The encyclopedia's view: the table over a kind's records, which part G fills.
export function Encyclopedia() {
  return (
    <main className="column">
      {/* Focused on a switch to this view; -1 keeps it out of the Tab order. */}
      <h1 className="text-display-sm" tabIndex={-1}>
        Encyclopedia
      </h1>
    </main>
  )
}
