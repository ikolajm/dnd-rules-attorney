import { ArrowUp, Square } from 'lucide-react'
import { Button } from './components/loom/button.tsx'

type Props = {
  draft: string
  running: boolean
  onDraft: (value: string) => void
  onSubmit: (question: string) => void
  onStop: () => void
}

// While a run is open the input stays editable, but the button is stop and a
// new question cannot start until the run has ended.
export function AskForm({ draft, running, onDraft, onSubmit, onStop }: Props) {
  const question = draft.trim()
  const submit = () => {
    if (!running && question !== '') onSubmit(question)
  }

  return (
    <form
      className="ask__form"
      onSubmit={(e) => {
        e.preventDefault()
        submit()
      }}
    >
      <label className="visually-hidden" htmlFor="question">
        A rules question
      </label>
      <textarea
        id="question"
        className="textarea"
        data-size="sm"
        rows={2}
        placeholder="Ask a rules question"
        value={draft}
        onChange={(e) => onDraft(e.target.value)}
        onKeyDown={(e) => {
          // Enter asks and Shift+Enter breaks the line, as in the agent chats.
          // An IME composing a character also sends Enter, which must not submit.
          if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
            e.preventDefault()
            submit()
          }
        }}
      />
      {running ? (
        <Button type="button" iconOnly color="neutral" aria-label="Stop" onClick={onStop}>
          <Square />
        </Button>
      ) : (
        <Button type="submit" iconOnly aria-label="Ask" disabled={question === ''}>
          <ArrowUp />
        </Button>
      )}
    </form>
  )
}
