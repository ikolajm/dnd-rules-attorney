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
  // Counts the questions asked. It keys the run's phases, so each new question
  // mounts them afresh and they play their entrance again.
  const [turn, setTurn] = useState(0)
  const [openEntry, setOpenEntry] = useState<PanelEntry | null>(null)
  const [view, setView] = useState<View>('ask')
  // The encyclopedia mounts on its first visit, so its files load then rather
  // than at startup, and stays mounted after, so a switch keeps its state.
  const [visited, setVisited] = useState(false)
  // Each view's scroll position, saved on leaving it, since both share the
  // window's scroll.
  const scrollRef = useRef<Record<View, number>>({ ask: 0, encyclopedia: 0 })
  const abortRef = useRef<AbortController | null>(null)
  // The control that opened the panel, so focus goes back to it on close.
  const triggerRef = useRef<HTMLElement | null>(null)

  const running = run?.phase === 'running'
  const entries = run?.entries ?? []
  const citedPaths = new Set(
    (run?.ruling?.cites ?? []).flatMap((cite) => {
      const c = resolveCite(cite, entries)
      return c.found ? [c.entry.path] : []
    }),
  )

  // The ask view follows the newest phase unless the reader has scrolled up from
  // the foot. The scroll is instant: the phase's own fade and rise is the motion,
  // and a smooth scroll's in-between positions would read as the reader leaving.
  // Both act only while the ask view shows: the encyclopedia shares the window's
  // scroll, and neither its scrolling nor a run streaming behind it is the
  // thread's.
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

  // The shown view's own scroll position, put back before the browser paints.
  // Layout effects run before plain ones, so the follow above lands after this:
  // a thread that was following goes to its foot. Focus stays on the tab, as
  // the tab pattern has it.
  useLayoutEffect(() => {
    window.scrollTo(0, scrollRef.current[view])
  }, [view])

  // A new question clears the screen: a ruling left up while the next one
  // streams would read as the answer to it.
  const ask = async (question: string) => {
    const controller = new AbortController()
    abortRef.current = controller
    followRef.current = true
    setTurn((t) => t + 1)
    setOpenEntry(null)
    setDraft('')
    setRun(startRun(question))
    try {
      for await (const e of live(question, controller.signal)) {
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

  const open = (entry: PanelEntry) => {
    triggerRef.current = document.activeElement as HTMLElement | null
    setOpenEntry(entry)
  }
  const close = useCallback(() => {
    setOpenEntry(null)
    triggerRef.current?.focus()
  }, [])

  // A switch closes the panel, which belongs to the view that opened it. Focus
  // does not go back to its trigger, which is about to be hidden.
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
    // The tabs take the app's own element, so its grid rows stay the tab list,
    // the view and the input bar. data-view lets the layout know which view
    // shows: the encyclopedia fixes the app's height so its table scrolls in its
    // own box.
    <Tabs asChild value={view} onValueChange={(next) => show(next as View)}>
      <div className="app" data-idle={run === null || undefined} data-view={view}>
        <div className="views">
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

        {/* Both views stay mounted and the other is hidden, so a switch keeps
            each one's state. -1 keeps a panel out of the Tab order: each holds
            controls of its own, which are the next stop after the tabs. */}
        <TabsContent value="ask" keepMounted tabIndex={-1} className="view">
          {run === null ? (
            // The empty screen: the input centred under the name, until a question runs.
            <main className="column empty">
              <h1 className="text-display-md">Lazy Dunmas</h1>
              {form}
            </main>
          ) : (
            // One turn told in time order, each phase mounting as its event lands.
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
                  <ViewAll entries={run.entries} cites={run.ruling?.cites ?? null} onOpen={open} />
                </Phase>
              )}

              {/* A ruling, or how the run ended without one, in the Verdict's place. */}
              {run.ruling ? (
                <Phase id="phase-verdict" label={PHASE_LABEL.verdict}>
                  <Verdict ruling={run.ruling} entries={entries} onOpen={open} />
                </Phase>
              ) : (
                !running && (
                  <Phase id="phase-verdict" label={PHASE_LABEL.verdict}>
                    <RunStatus run={run} onRetry={() => void ask(run.question)} />
                  </Phase>
                )
              )}

              {/* The phase the run waits on, pending at the foot. The slot stays
                  mounted so a screen reader hears each label as it changes. */}
              <div aria-live="polite">
                {running && (
                  <p className="phase__pending phase__label eyebrow text-label-lg">{PENDING_LABEL[run.stage]}</p>
                )}
              </div>
            </main>
          )}
        </TabsContent>

        {/* The panel is there from the start, so its tab names a real element;
            the encyclopedia inside it waits for the first visit. */}
        <TabsContent value="encyclopedia" keepMounted tabIndex={-1} className="view">
          {visited && <Encyclopedia onOpen={open} />}
        </TabsContent>

        <div className="ask">
          {run !== null && view === 'ask' && <div className="column">{form}</div>}
          <footer className="attribution column text-body-sm text-on-surface-variant">
            <Attribution />
          </footer>
        </div>

        {/* "Cited" is about the ruling, so it shows only on the ask view: a
            record opened from the encyclopedia is not a cite. */}
        <SourcePanel
          entry={openEntry}
          cited={openEntry !== null && view === 'ask' && citedPaths.has(openEntry.path)}
          onClose={close}
        />
      </div>
    </Tabs>
  )
}
