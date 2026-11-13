// A load's state said the same way wherever one is: a kind's rows in the
// table, and a record's view, an entry's source text and a list item's text in
// the panel. Loading, then nothing once ready, or the failure with a Retry.
import { CircleAlert, RotateCcw } from 'lucide-react'
import { useRef } from 'react'
import { Button } from '../components/loom/button.tsx'
import type { Load } from './use-load.ts'

export function LoadState({
  status,
  message,
  onRetry,
  loading = 'Loading…',
  compact = false,
  live = true,
}: {
  status: Load<unknown>['status']
  // What failed, said as the failure's line: "Monsters could not be loaded."
  message: string
  onRetry: () => void
  loading?: string
  // In the panel, where the state is a note on one part of an entry rather
  // than the table's whole place, and the table's title size would rival the
  // panel's own title.
  compact?: boolean
  // Off where the caller's own region is live already, so the two do not nest.
  live?: boolean
}) {
  const regionRef = useRef<HTMLDivElement>(null)
  // Focus moves first: Retry is about to unmount, and focus on a removed element drops to the page's start.
  const retry = () => {
    regionRef.current?.focus()
    onRetry()
  }

  // Rendered even when empty: a live region added with its text is often not announced.
  return (
    <div
      ref={regionRef}
      tabIndex={-1}
      className={`status ${compact ? 'status--compact' : ''}`}
      aria-live={live ? 'polite' : undefined}
    >
      {status === 'loading' && (
        <p className={`${compact ? 'text-body-md' : 'text-body-lg'} text-on-surface-variant`}>{loading}</p>
      )}
      {status === 'failed' && (
        <>
          <p
            className={`status__line tone-error ${compact ? 'status__line--compact text-label-lg' : 'text-title-md'}`}
          >
            <CircleAlert aria-hidden="true" />
            {message}
          </p>
          <p className={`${compact ? 'text-body-md' : 'text-body-lg'} text-on-surface-variant`}>
            Check your connection and try again.
          </p>
          <Button
            variant="outline"
            color="neutral"
            size="sm"
            leadingIcon={<RotateCcw aria-hidden="true" />}
            onClick={retry}
          >
            Retry
          </Button>
        </>
      )}
    </div>
  )
}
