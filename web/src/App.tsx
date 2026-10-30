import { useCallback, useRef, useState } from 'react'
import { AskForm } from './AskForm.tsx'
import { Attribution } from './Attribution.tsx'
import { resolveCite } from './cites.ts'
import { fixtures } from './fixtures/index.ts'
import { live } from './live.ts'
import { Reasoning } from './Reasoning.tsx'
import { applyEvent, startRun, type Run } from './run.ts'
import { RunStatus } from './RunStatus.tsx'
import { SourcePanel } from './SourcePanel.tsx'
import { replay, SCENARIOS, type Scenario } from './stream.ts'
import type { Entry } from './types.ts'
import { Verdict } from './Verdict.tsx'
import { ViewAll } from './ViewAll.tsx'
import './app.css'

export default function App() {
  // Dev only: 'live' or a fixture's id. A production build is live alone.
  const [source, setSource] = useState('live')
  const [scenario, setScenario] = useState<Scenario>('ruled')
  const [draft, setDraft] = useState('')
  const [run, setRun] = useState<Run | null>(null)
  const [openEntry, setOpenEntry] = useState<Entry | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  // The control that opened the panel, so focus goes back to it on close.
  const triggerRef = useRef<HTMLElement | null>(null)
  const fixture = fixtures.find((f) => f.source.id === source)

  const running = run?.phase === 'running'
  const entries = run?.entries ?? []
  const citedPaths = new Set(
    (run?.ruling?.cites ?? []).flatMap((cite) => {
      const c = resolveCite(cite, entries)
      return c.found ? [c.entry.path] : []
    }),
  )

  // A new question clears the screen: a ruling left up while the next one
  // streams would read as the answer to it.
  const ask = async (question: string) => {
    const controller = new AbortController()
    abortRef.current = controller
    setOpenEntry(null)
    setDraft('')
    setRun(startRun(question))
    try {
      const events = fixture
        ? replay(fixture, scenario, controller.signal)
        : live(question, controller.signal)
      for await (const e of events) {
        setRun((r) => r && applyEvent(r, e))
        // A refused question goes back in the box to be edited.
        if (e.event === 'gate' && !e.data.about_rules) setDraft(question)
      }
    } catch (err) {
      if (!controller.signal.aborted) throw err
      setRun((r) => r && { ...r, phase: 'stopped' })
    } finally {
      abortRef.current = null
    }
  }

  const stop = () => abortRef.current?.abort()

  const open = (entry: Entry) => {
    triggerRef.current = document.activeElement as HTMLElement | null
    setOpenEntry(entry)
  }
  const close = useCallback(() => {
    setOpenEntry(null)
    triggerRef.current?.focus()
  }, [])

  const form = (
    <AskForm draft={draft} running={running} onDraft={setDraft} onSubmit={(q) => void ask(q)} onStop={stop} />
  )

  return (
    <div className="app" data-idle={run === null || undefined}>
      {import.meta.env.DEV && (
        <div className="dev-switcher">
          <label className="text-label-sm" htmlFor="source">
            Source
          </label>
          <select
            id="source"
            className="input control"
            data-size="sm"
            value={source}
            disabled={running}
            onChange={(e) => {
              setSource(e.target.value)
              const next = fixtures.find((f) => f.source.id === e.target.value)
              if (next) setDraft(next.question)
            }}
          >
            <option value="live">live</option>
            {fixtures.map((f) => (
              <option key={f.source.id} value={f.source.id}>
                {f.source.id}
              </option>
            ))}
          </select>
          {/* How a replay ends; a live run ends however the server does. */}
          {fixture && (
            <>
              <label className="text-label-sm" htmlFor="scenario">
                Ends
              </label>
              <select
                id="scenario"
                className="input control"
                data-size="sm"
                value={scenario}
                disabled={running}
                onChange={(e) => setScenario(e.target.value as Scenario)}
              >
                {SCENARIOS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </>
          )}
        </div>
      )}

      {run === null ? (
        // The empty screen: the input centred under the name, until a question runs.
        <main className="column empty">
          <h1 className="text-display-md">Lazy Dunmas</h1>
          {form}
        </main>
      ) : (
        <main className="column">
          <h1 className="question text-title-lg">{run.question}</h1>

          {run.ruling ? (
            <Verdict ruling={run.ruling} entries={entries} onOpen={open} />
          ) : (
            <RunStatus run={run} onRetry={() => void ask(run.question)} />
          )}

          {run.subQuestions && (
            <Reasoning
              subQuestions={run.subQuestions}
              explanation={run.ruling?.explanation ?? null}
              entries={entries}
              onOpen={open}
            />
          )}

          {run.entries && <ViewAll entries={run.entries} cites={run.ruling?.cites ?? null} onOpen={open} />}
        </main>
      )}

      <div className="ask">
        {run !== null && <div className="column">{form}</div>}
        <footer className="attribution column text-body-sm text-on-surface-variant">
          <Attribution />
        </footer>
      </div>

      <SourcePanel entry={openEntry} cited={openEntry ? citedPaths.has(openEntry.path) : false} onClose={close} />
    </div>
  )
}
