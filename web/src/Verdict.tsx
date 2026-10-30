import { CircleSlash, Scale } from 'lucide-react'
import { Badge } from './components/loom/badge.tsx'
import { Button } from './components/loom/button.tsx'
import { entryLabel, resolveCite } from './cites.ts'
import type { Answer, Entry, Ruling } from './types.ts'

type Props = {
  ruling: Ruling
  entries: Entry[]
  onOpen: (entry: Entry) => void
}

function verdictText(answer: Answer): string {
  switch (answer.kind) {
    case 'yes-or-no':
      return answer.verdict === 'yes' ? 'Yes' : 'No'
    case 'how-many':
      return String(answer.verdict)
    case 'what':
      return answer.verdict
  }
}

export function Verdict({ ruling, entries, onOpen }: Props) {
  const cites = ruling.cites.map((cite) => resolveCite(cite, entries))
  // A word or a number reads at display size; a sentence would wrap into a
  // wall at that size, so it steps down to a title.
  const short = ruling.answer.kind !== 'what'

  return (
    <section className="verdict" aria-labelledby="verdict-heading" data-ambiguous={ruling.ambiguous || undefined}>
      <h2 id="verdict-heading" className="text-label-md text-on-surface-variant">
        Verdict
      </h2>
      <p className={short ? 'verdict__answer text-display-lg' : 'verdict__answer text-title-lg'}>
        {verdictText(ruling.answer)}
      </p>

      {ruling.ambiguous && (
        <p className="verdict__ambiguous">
          <Badge color="warning" intensity="soft" leadingIcon={<Scale />}>
            Ambiguous
          </Badge>
          <span className="text-body-md text-on-surface-variant">
            The text allows more than one reading. The reasoning gives each.
          </span>
        </p>
      )}

      <div className="verdict__cites">
        <h3 className="text-label-md text-on-surface-variant">Cited</h3>
        <ul className="verdict__cite-list">
          {cites.map((c) => (
            <li key={c.cite}>
              {c.found ? (
                <Button variant="outline" color="neutral" size="sm" onClick={() => onOpen(c.entry)}>
                  {entryLabel(c.entry)}
                </Button>
              ) : (
                <Badge
                  variant="outline"
                  color="neutral"
                  leadingIcon={<CircleSlash />}
                  title="The ruling cites a section that is not among the entries it was given."
                >
                  {c.cite} · not found
                </Badge>
              )}
            </li>
          ))}
        </ul>
      </div>
    </section>
  )
}
