import { X } from 'lucide-react'
import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { Badge } from '../components/loom/badge.tsx'
import { Button } from '../components/loom/button.tsx'
import { entryLabel, pathSegments } from './cites.ts'
import { useEntryText } from '../encyclopedia/entry-text.ts'
import { LoadState } from '../encyclopedia/LoadState.tsx'
import { corpusFields } from '../encyclopedia/views/fields.ts'
import { FieldsView } from '../encyclopedia/views/FieldsView.tsx'
import { hasView } from '../encyclopedia/views/roots.ts'
import { RecordView } from '../encyclopedia/views/RecordView.tsx'
import { PULLOUT_HEADINGS, pulloutText } from '../encyclopedia/views/pullouts.ts'
import type { Expand } from '../encyclopedia/views/StatBlock.tsx'
import { usePullouts } from '../encyclopedia/views/use-pullouts.ts'
import { entryBody, entryTitle } from './entry.ts'
import { Prose } from './Prose.tsx'
import type { Entry } from './types.ts'

// Wide enough that a panel beside the column leaves the ruling readable. Below
// it nothing can be read beside the panel, so it becomes a modal.
const WIDE = '(min-width: 60rem)'

function useWide(): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const query = window.matchMedia(WIDE)
      query.addEventListener('change', onChange)
      return () => query.removeEventListener('change', onChange)
    },
    () => window.matchMedia(WIDE).matches,
  )
}

// What the panel opens. A cite's entry carries its text from the run; a row
// opened from the encyclopedia carries its path and name, and the panel loads
// its text. `'text' in entry` tells them apart.
export type PanelEntry = Entry | { path: string; title: string }

type Props = {
  entry: PanelEntry | null
  cited: boolean
  onClose: () => void
}

export function SourcePanel({ entry, cited, onClose }: Props) {
  const wide = useWide()
  return wide ? (
    <SidePanel entry={entry} cited={cited} onClose={onClose} />
  ) : (
    <ModalPanel entry={entry} cited={cited} onClose={onClose} />
  )
}

// Non-modal: no scrim and no focus trap, so the ruling behind stays readable
// and clickable, and another cite swaps the entry shown. A native <dialog>
// opened with show() would not close on Escape, so Escape is handled here.
function SidePanel({ entry, cited, onClose }: Props) {
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!entry) return
    closeRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [entry, onClose])

  if (!entry) return null
  return (
    <aside className="source-panel surface-1 elevate-3" role="dialog" aria-modal="false" aria-labelledby="source-title">
      <PanelBody entry={entry} cited={cited} onClose={onClose} closeRef={closeRef} />
    </aside>
  )
}

// On a narrow screen the panel would cover the ruling entirely, so it is a
// modal <dialog>: the focus trap, Escape and the inert page come with it.
function ModalPanel({ entry, cited, onClose }: Props) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return
    if (entry && !dialog.open) dialog.showModal()
    if (!entry && dialog.open) dialog.close()
  }, [entry])

  return (
    <dialog ref={dialogRef} className="source-panel source-panel--modal surface-1" aria-labelledby="source-title" onClose={onClose}>
      {entry && <PanelBody entry={entry} cited={cited} onClose={onClose} closeRef={closeRef} />}
    </dialog>
  )
}

// Which text the panel shows for an entry with a view of its own: the view, or
// the source text, the corpus entry the model is handed. Each button says
// whether it is the one on through aria-pressed.
function SourceToggle({ source, onChange }: { source: boolean; onChange: (source: boolean) => void }) {
  return (
    <div className="source-panel__toggle" role="group" aria-label="Text shown">
      <Button size="sm" variant={source ? 'ghost' : 'filled'} aria-pressed={!source} onClick={() => onChange(false)}>
        Formatted
      </Button>
      <Button size="sm" variant={source ? 'filled' : 'ghost'} aria-pressed={source} onClick={() => onChange(true)}>
        Source text
      </Button>
    </div>
  )
}

function PanelBody({
  entry,
  cited,
  onClose,
  closeRef,
}: Props & { entry: PanelEntry; closeRef: React.RefObject<HTMLButtonElement | null> }) {
  // A row's name from the first frame, so the heading does not change when its
  // text arrives.
  const title = 'text' in entry ? entryLabel(entry) : entry.title
  const trail = pathSegments(entry.path).slice(0, -1)
  const { text, retry } = useEntryText(entry)
  const body = text.status === 'ready' ? entryBody(text.value) : null
  // A spell, a monster or a magic item opens its view, built from its record,
  // which needs no source text; a weapon, a piece of armor or a race its fields
  // as rows, read from the text once it is there; anything else renders as
  // markdown.
  const hasRecordView = hasView(entry.path)
  const fields = hasRecordView || body === null ? null : corpusFields(entry.path, body)
  // Only a view that differs from the source text gets the toggle; a condition
  // already shows its source text. The choice lives here, which the side panel
  // keeps mounted from entry to entry, so it holds until the panel closes.
  const formatted = hasRecordView || fields !== null
  // What a race's traits and subraces and a weapon's properties open to in
  // place, once the corpus is loaded to find them in.
  const pulled = usePullouts(entry.path, fields?.sections ?? [])
  // An open row's own region is live already, so its state's is not.
  const expand: Expand = (heading, item) => {
    if (!PULLOUT_HEADINGS.has(heading)) return undefined
    if (pulled.state.status !== 'ready') {
      return (
        <LoadState
          status={pulled.state.status}
          message="This text could not be loaded."
          onRetry={pulled.retry}
          compact
          live={false}
        />
      )
    }
    const entries = pulled.state.value.get(heading)?.get(item)
    if (!entries) return undefined
    // A subrace opens to its traits, each under its own name; a trait or a
    // property to its own text, its name already the row's.
    return (
      <Prose>
        {entries.length === 1 && heading !== 'Subraces'
          ? pulloutText(entries[0])
          : entries.map((e) => `**${entryTitle(e.text) ?? ''}.** ${pulloutText(e)}`).join('\n\n')}
      </Prose>
    )
  }
  const [source, setSource] = useState(false)

  // The source text's loading or failure. Empty for a cite, whose text is
  // there from the start.
  const textState = (
    <LoadState status={text.status} message="The source text could not be loaded." onRetry={retry} compact />
  )

  return (
    <>
      <header className="source-panel__header">
        <div className="source-panel__heading">
          {trail.length > 0 && <p className="eyebrow text-label-sm">{trail.join(' › ')}</p>}
          <h2 id="source-title" className="text-title-md">
            {title}
          </h2>
          {cited && (
            <Badge size="md" color="primary" intensity="soft">
              Cited
            </Badge>
          )}
        </div>
        <Button ref={closeRef} variant="ghost" color="neutral" iconOnly aria-label="Close source" onClick={onClose}>
          <X />
        </Button>
      </header>
      {formatted && <SourceToggle source={source} onChange={setSource} />}
      <div className="source-panel__text text-body-md">
        {formatted ? (
          <>
            {/* Both stay mounted and the other is hidden, so switching back
                does not load the record again; `hidden` keeps it out of the
                page's find and the accessibility tree too. The key mounts a
                fresh RecordView for each path, so the last record does not
                show while the next one loads. A record's view does not wait
                for the source text; only its Source text side does. */}
            <div hidden={source}>
              {hasRecordView ? <RecordView key={entry.path} path={entry.path} /> : fields && <FieldsView key={entry.path} fields={fields} expand={expand} />}
            </div>
            <div hidden={!source}>
              {textState}
              {body !== null && <Prose>{body}</Prose>}
            </div>
          </>
        ) : (
          <>
            {textState}
            {body !== null && <Prose>{body}</Prose>}
          </>
        )}
      </div>
    </>
  )
}
