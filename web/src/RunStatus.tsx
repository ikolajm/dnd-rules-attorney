import { CircleAlert, CircleSlash, RotateCcw, Square } from 'lucide-react'
import { Button } from './components/loom/button.tsx'
import type { Run } from './run.ts'
import type { ErrorReason } from './types.ts'

const ERROR_TEXT: Record<ErrorReason, string> = {
  unreachable: 'The model could not be reached. Check that Ollama is running.',
  'ruling-unparsed': 'The model’s ruling came back in a shape that could not be read.',
  timeout: 'The ruling took too long and was ended.',
  'server-unreachable': 'The rules server could not be reached. Check that it is running.',
}

type Props = {
  run: Run
  onRetry: () => void
}

// How a run ended without a ruling, in the Verdict phase's place: refused,
// failed, or stopped. Each carries an icon as well as its words, so none rests
// on colour.
export function RunStatus({ run, onRetry }: Props) {
  return (
    <div className="run-status">
      {run.phase === 'refused' && (
        <>
          <p className="run-status__line text-title-md">
            <CircleSlash aria-hidden="true" />
            Not a rules question
          </p>
          <p className="text-body-lg text-on-surface-variant">
            This rules only on questions the SRD 5.1 answers. Your question is back in the box to edit.
          </p>
        </>
      )}

      {run.phase === 'error' && run.error && (
        <>
          <p className="run-status__line text-title-md tone-error">
            <CircleAlert aria-hidden="true" />
            Something went wrong
          </p>
          <p className="text-body-lg text-on-surface-variant">{ERROR_TEXT[run.error]}</p>
          <div>
            <Button variant="outline" color="neutral" size="sm" leadingIcon={<RotateCcw />} onClick={onRetry}>
              Retry
            </Button>
          </div>
        </>
      )}

      {run.phase === 'stopped' && (
        <p className="run-status__line text-title-md text-on-surface-variant">
          <Square aria-hidden="true" />
          Stopped
        </p>
      )}
    </div>
  )
}
