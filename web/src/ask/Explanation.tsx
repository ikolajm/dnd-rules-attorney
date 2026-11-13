import { linkExplanation } from '../shared/cites.ts'
import type { Entry } from '../shared/types.ts'

type Props = {
  explanation: string
  entries: Entry[]
  openPath: string | null
  onOpen: (entry: Entry) => void
}

// The ruling's explanation as paragraphs, each entry it names by path a link
// that reads as the entry's title and opens it.
export function Explanation({ explanation, entries, openPath, onOpen }: Props) {
  return (
    <div className="explanation text-body-lg">
      {explanation.split(/\n\s*\n/).map((paragraph, i) => (
        <p key={i}>
          {linkExplanation(paragraph, entries).map((part, j) =>
            'entry' in part ? (
              <button
                key={j}
                type="button"
                className="link link-prose"
                aria-expanded={openPath === part.entry.path}
                onClick={() => onOpen(part.entry)}
              >
                {part.text}
              </button>
            ) : (
              part.text
            ),
          )}
        </p>
      ))}
    </div>
  )
}
