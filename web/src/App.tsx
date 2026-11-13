import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react'
import { AskForm } from './ask/AskForm.tsx'
import { Attribution } from './shared/Attribution.tsx'
import { resolveCite } from './shared/cites.ts'
import { live } from './ask/live.ts'
import { Phase } from './ask/Phase.tsx'
import { applyEvent, PENDING_LABEL, PHASE_LABEL, startRun, type Run } from './ask/run.ts'
import { RunStatus } from './ask/RunStatus.tsx'
import { SourcePanel, type PanelEntry } from './shared/SourcePanel.tsx'
import { Verdict } from './ask/Verdict.tsx'
import { ViewAll } from './ask/ViewAll.tsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/loom/tabs.tsx'
import { Encyclopedia } from './encyclopedia/Encyclopedia.tsx'
// app.css first: main.encyclopedia and main.empty tie main.column and win by order.
import './app.css'
import './ask/ask.css'
import './encyclopedia/encyclopedia.css'
import './shared/shared.css'

type View = 'ask' | 'encyclopedia'

// Each view and its tab's label, in the tab list's order.
const VIEWS: [View, string][] = [
  ['ask', 'Ask'],
  ['encyclopedia', 'Encyclopedia'],
]

export default function App() {
  const [draft, setDraft] = useState('')
  const [run, setRun] = useState<Run | null>(null)
  // Keys the thread, so each question remounts its phases and replays their entrance.
  const [turn, setTurn] = useState(0)
  const [openEntry, setOpenEntry] = useState<PanelEntry | null>(null)
  const [view, setView] = useState<View>('ask')
  // The encyclopedia mounts on its first visit, so its files load then and not at startup.
  const [visited, setVisited] = useState(false)
  // Saved per view, since both views share the window's scroll.
  const scrollRef = useRef<Record<View, number>>({ ask: 0, encyclopedia: 0 })
  const abortRef = useRef<AbortController | null>(null)
  const triggerRef = useRef<HTMLElement | null>(null)

  const running = run?.phase === 'running'
  const entries = run?.entries ?? []
  const openPath = openEntry?.path ?? null
  const citedPaths = new Set(
    (run?.ruling?.cites ?? []).flatMap((cite) => {
      const c = resolveCite(cite, entries)
      return c.found ? [c.entry.path] : []
    }),
  )

  // Follows the newest phase unless the reader scrolled up. Ask view only: the
  // encyclopedia shares the window's scroll.
  const followRef = useRef(true)
  useEffect(() => {
    if (view !== 'ask') return
    const onScroll = () => {
      const below = document.documentElement.scrollHeight - (window.scrollY + window.innerHeight)
      followRef.current = below < 96
    }
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [view])
  useEffect(() => {
    if (view === 'ask' && run && followRef.current) window.scrollTo({ top: document.documentElement.scrollHeight })
  }, [run, view])

  // The sticky bars' heights, as the page's scroll padding reads them, so a
  // control scrolled into view clears both bars.
  const viewsRef = useRef<HTMLDivElement>(null)
  const askRef = useRef<HTMLDivElement>(null)
  useLayoutEffect(() => {
    const bars: [HTMLElement | null, string][] = [
      [viewsRef.current, '--views-height'],
      [askRef.current, '--ask-height'],
    ]
    const root = document.documentElement.style
    const observer = new ResizeObserver((records) => {
      for (const record of records) {
        const name = bars.find(([bar]) => bar === record.target)?.[1]
        if (name) root.setProperty(name, `${record.borderBoxSize[0].blockSize}px`)
      }
    })
    for (const [bar] of bars) if (bar) observer.observe(bar)
    return () => observer.disconnect()
  }, [])

  // A layout effect, so it runs before the follow above, which then wins.
  useLayoutEffect(() => {
    window.scrollTo(0, scrollRef.current[view])
  }, [view])

  const ask = async (question: string) => {
    const controller = new AbortController()
    abortRef.current = controller
    followRef.current = true
    setTurn((t) => t + 1)
    setOpenEntry(null)
    setRun(startRun(question))
    try {
      for await (const e of live(question, controller.signal)) {
        setRun((r) => r && applyEvent(r, e))
      }
    } catch (err) {
      if (!controller.signal.aborted) throw err
      setRun((r) => r && { ...r, phase: 'stopped' })
    } finally {
      abortRef.current = null
    }
  }

  const stop = () => abortRef.current?.abort()

  const open = (entry: PanelEntry) => {
    triggerRef.current = document.activeElement as HTMLElement | null
    setOpenEntry(entry)
  }
  const close = useCallback(() => {
    setOpenEntry(null)
    triggerRef.current?.focus()
  }, [])

  // Closes the panel without returning focus, unlike close: the trigger is about to be hidden.
  const show = (next: View) => {
    // `view` is still the view being left; the update has not happened yet.
    scrollRef.current[view] = window.scrollY
    setOpenEntry(null)
    setView(next)
    if (next === 'encyclopedia') setVisited(true)
  }

  const form = (
    <AskForm draft={draft} running={running} onDraft={setDraft} onSubmit={(q) => void ask(q)} onStop={stop} />
  )

  return (
    // asChild: the tabs take the app's element, so its grid rows stay tabs, view, input bar.
    <Tabs asChild value={view} onValueChange={(next) => show(next as View)}>
      <div className="app" data-idle={run === null || undefined} data-view={view}>
        <div ref={viewsRef} className="views">
          <div className="column">
            <TabsList aria-label="Views">
              {VIEWS.map(([id, label]) => (
                <TabsTrigger key={id} value={id}>
                  {label}
                </TabsTrigger>
              ))}
            </TabsList>
          </div>
        </div>

        {/* -1: each panel's own controls are the next Tab stop after the tabs. */}
        <TabsContent value="ask" keepMounted tabIndex={-1} className="view">
          {run === null ? (
            <main className="column empty">
              <h1 className="text-display-md">Lazy Dunmas</h1>
              {form}
            </main>
          ) : (
            <main key={turn} className="column thread">
              <h1 className="visually-hidden">Lazy Dunmas</h1>

              <Phase id="phase-question" label={PHASE_LABEL.question}>
                <blockquote className="phase__question text-body-lg">
                  <p>“{run.question}”</p>
                </blockquote>
              </Phase>

              {run.subQuestions && (
                <Phase id="phase-plan" label={PHASE_LABEL.plan}>
                  {run.subQuestions.length > 0 ? (
                    <ol className="sub-questions text-body-lg">
                      {run.subQuestions.map((q) => (
                        <li key={q}>{q}</li>
                      ))}
                    </ol>
                  ) : (
                    <p className="text-body-lg text-on-surface-variant">
                      Not split: the question is searched as it was asked.
                    </p>
                  )}
                </Phase>
              )}

              {run.entries && (
                <Phase id="phase-entries" label={PHASE_LABEL.entries}>
                  <ViewAll entries={run.entries} cites={run.ruling?.cites ?? null} openPath={openPath} onOpen={open} />
                </Phase>
              )}

              {run.ruling ? (
                <Phase id="phase-verdict" label={PHASE_LABEL.verdict}>
                  <Verdict ruling={run.ruling} entries={entries} openPath={openPath} onOpen={open} />
                </Phase>
              ) : (
                !running && (
                  <Phase id="phase-verdict" label={PHASE_LABEL.verdict}>
                    <RunStatus run={run} onRetry={() => void ask(run.question)} />
                  </Phase>
                )
              )}

              {/* Mounted while empty, so a screen reader hears each label as it changes. */}
              <div aria-live="polite">
                {running && (
                  <p className="phase__pending phase__label eyebrow text-label-lg">{PENDING_LABEL[run.stage]}</p>
                )}
              </div>
            </main>
          )}
        </TabsContent>

        {/* Mounted from the start, so its tab's aria-controls names a real element. */}
        <TabsContent value="encyclopedia" keepMounted tabIndex={-1} className="view">
          {visited && <Encyclopedia openPath={openPath} onOpen={open} />}
        </TabsContent>

        <div ref={askRef} className="ask">
          {run !== null && view === 'ask' && <div className="column">{form}</div>}
          <footer className="attribution column text-body-sm text-on-surface-variant">
            <Attribution />
          </footer>
        </div>

        <SourcePanel
          entry={openEntry}
          cited={openEntry !== null && view === 'ask' && citedPaths.has(openEntry.path)}
          onClose={close}
        />
      </div>
    </Tabs>
  )
}
