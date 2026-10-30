import { linkExplanation } from './cites.ts'
import type { Entry } from './types.ts'

type Props = {
  explanation: string
  entries: Entry[]
  onOpen: (entry: Entry) => void
}

// The ruling's explanation as paragraphs, each entry it names by path a link
// that reads as the entry's title and opens it.
export function Explanation({ explanation, entries, onOpen }: Props) {
  return (
    <div className="explanation text-body-lg">
      {explanation.split(/\n\s*\n/).map((paragraph, i) => (
        <p key={i}>
          {linkExplanation(paragraph, entries).map((part, j) =>
            'entry' in part ? (
              <button key={j} type="button" className="link link-prose" onClick={() => onOpen(part.entry)}>
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
