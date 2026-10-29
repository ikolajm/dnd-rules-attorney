import { useCallback, useRef, useState } from 'react'
import { AskForm } from './AskForm.tsx'
import { resolveCite } from './cites.ts'
import { fixtures } from './fixtures/index.ts'
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
  const [fixtureId, setFixtureId] = useState(fixtures[0].source.id)
  const [scenario, setScenario] = useState<Scenario>('ruled')
  const [draft, setDraft] = useState(fixtures[0].question)
  const [run, setRun] = useState<Run | null>(null)
  const [openEntry, setOpenEntry] = useState<Entry | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  // The control that opened the panel, so focus goes back to it on close.
  const triggerRef = useRef<HTMLElement | null>(null)
  const fixture = fixtures.find((f) => f.source.id === fixtureId) ?? fixtures[0]

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
      for await (const e of replay(fixture, scenario, controller.signal)) {
        setRun((r) => r && applyEvent(r, e))
        // A refused question goes back in the box to be edited.
        if (e.event === 'gate' && !e.data.allowed) setDraft(question)
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
          <label className="text-label-sm" htmlFor="fixture">
            Fixture
          </label>
          <select
            id="fixture"
            className="input control"
            data-size="sm"
            value={fixtureId}
            disabled={running}
            onChange={(e) => {
              const next = fixtures.find((f) => f.source.id === e.target.value) ?? fixtures[0]
              setFixtureId(next.source.id)
              setDraft(next.question)
            }}
          >
            {fixtures.map((f) => (
              <option key={f.source.id} value={f.source.id}>
                {f.source.id}
              </option>
            ))}
          </select>
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
          Rules text from the System Reference Document 5.1 by Wizards of the Coast LLC, licensed under{' '}
          <a className="link link-prose" href="https://creativecommons.org/licenses/by/4.0/legalcode">
            CC-BY-4.0
          </a>
          .
        </footer>
      </div>

      <SourcePanel entry={openEntry} cited={openEntry ? citedPaths.has(openEntry.path) : false} onClose={close} />
    </div>
  )
}
