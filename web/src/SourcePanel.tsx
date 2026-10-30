import { X } from 'lucide-react'
import { useEffect, useRef, useSyncExternalStore } from 'react'
import Markdown, { type Components } from 'react-markdown'
import remarkBreaks from 'remark-breaks'
import remarkGfm from 'remark-gfm'
import { Badge } from './components/loom/badge.tsx'
import { Button } from './components/loom/button.tsx'
import { entryLabel, pathSegments } from './cites.ts'
import { entryBody } from './entry.ts'
import { parseSpell } from './spell.ts'
import { SpellStats } from './SpellStats.tsx'
import type { Entry } from './types.ts'

// Tables are GFM, not CommonMark. Breaks keeps each single line break, which
// two rule sections write as one; the spells' stat lines, which wrote most of
// them, are laid out by SpellStats instead.
const PLUGINS = [remarkGfm, remarkBreaks]

// The corpus's markdown onto Loom. Headings inside an entry sit under the
// panel's own h2, whatever level the source wrote them at, and a table scrolls
// on its own rather than widening the panel.
const ELEMENTS: Components = {
  h1: ({ children }) => <h3 className="text-title-sm">{children}</h3>,
  h2: ({ children }) => <h3 className="text-title-sm">{children}</h3>,
  h3: ({ children }) => <h3 className="text-title-sm">{children}</h3>,
  h4: ({ children }) => <h3 className="text-title-sm">{children}</h3>,
  h5: ({ children }) => <h3 className="text-title-sm">{children}</h3>,
  h6: ({ children }) => <h3 className="text-title-sm">{children}</h3>,
  table: ({ children }) => (
    <div className="source-panel__table">
      <table className="table">{children}</table>
    </div>
  ),
}

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

type Props = {
  entry: Entry | null
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

function PanelBody({
  entry,
  cited,
  onClose,
  closeRef,
}: Props & { entry: Entry; closeRef: React.RefObject<HTMLButtonElement | null> }) {
  const title = entryLabel(entry)
  const trail = pathSegments(entry.path).slice(0, -1)
  const body = entryBody(entry.text)
  // A spell's stat lines get their own layout; anything that does not parse as
  // one renders as markdown, as every other entry does.
  const spell = entry.path.startsWith('spells > ') ? parseSpell(body) : null

  return (
    <>
      <header className="source-panel__header">
        <div className="source-panel__heading">
          {trail.length > 0 && <p className="text-label-sm text-on-surface-variant">{trail.join(' › ')}</p>}
          <h2 id="source-title" className="text-title-md">
            {title}
          </h2>
          {cited && (
            <Badge size="sm" color="primary" intensity="soft">
              Cited
            </Badge>
          )}
        </div>
        <Button ref={closeRef} variant="ghost" color="neutral" iconOnly aria-label="Close source" onClick={onClose}>
          <X />
        </Button>
      </header>
      <div className="source-panel__text text-body-md">
        {spell && <SpellStats spell={spell} />}
        <Markdown remarkPlugins={PLUGINS} components={ELEMENTS}>
          {spell ? spell.body : body}
        </Markdown>
      </div>
    </>
  )
}
