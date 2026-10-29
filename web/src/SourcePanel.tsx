import { X } from 'lucide-react'
import { useEffect, useRef, useSyncExternalStore } from 'react'
import { Badge } from './components/loom/badge.tsx'
import { Button } from './components/loom/button.tsx'
import { pathSegments } from './cites.ts'
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
  const segments = pathSegments(entry.path)
  const title = segments[segments.length - 1]
  const trail = segments.slice(0, -1)

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
      {/* The entry's markdown shown as written until a renderer is chosen. */}
      <div className="source-panel__text text-body-md">{entry.text}</div>
    </>
  )
}
