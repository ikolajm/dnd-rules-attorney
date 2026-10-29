import { linkExplanation } from './cites.ts'
import type { Entry } from './types.ts'

type Props = {
  subQuestions: string[]
  // Absent until the ruling lands; the sub-questions show on their own first.
  explanation: string | null
  entries: Entry[]
  onOpen: (entry: Entry) => void
}

export function Reasoning({ subQuestions, explanation, entries, onOpen }: Props) {
  const paragraphs = explanation ? explanation.split(/\n\s*\n/) : []

  return (
    <section className="reasoning" aria-labelledby="reasoning-heading">
      <h2 id="reasoning-heading" className="text-label-md text-on-surface-variant">
        Reasoning
      </h2>

      <div className="reasoning__plan">
        <h3 className="text-label-md">Split into</h3>
        <ol className="reasoning__sub-questions text-body-md">
          {subQuestions.map((q) => (
            <li key={q}>{q}</li>
          ))}
        </ol>
      </div>

      {paragraphs.length > 0 && (
        <div className="reasoning__explanation text-body-lg">
          {paragraphs.map((paragraph, i) => (
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
      )}
    </section>
  )
}
