import { CircleAlert, CircleSlash, RotateCcw, Square } from 'lucide-react'
import { Button } from './components/loom/button.tsx'
import { STAGE_LABEL, type Run } from './run.ts'
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

// The Verdict region before there is a verdict: the stage a run has reached,
// or how it ended without one. Announced politely, so a screen reader hears
// each stage without being interrupted.
export function RunStatus({ run, onRetry }: Props) {
  return (
    <section className="verdict" aria-labelledby="verdict-heading">
      <h2 id="verdict-heading" className="text-label-md text-on-surface-variant">
        Verdict
      </h2>
      <div className="run-status" aria-live="polite">
        {run.phase === 'running' && (
          <p className="run-status__stage text-title-md text-on-surface-variant">{STAGE_LABEL[run.stage]}…</p>
        )}

        {run.phase === 'refused' && (
          <>
            <p className="run-status__line text-title-md">
              <CircleSlash aria-hidden="true" />
              Not a rules question
            </p>
            <p className="text-body-md text-on-surface-variant">
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
            <p className="text-body-md text-on-surface-variant">{ERROR_TEXT[run.error]}</p>
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
    </section>
  )
}
