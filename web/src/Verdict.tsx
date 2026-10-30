import { CircleSlash, Scale } from 'lucide-react'
import { Badge } from './components/loom/badge.tsx'
import { Button } from './components/loom/button.tsx'
import { entryLabels, resolveCite } from './cites.ts'
import { Explanation } from './Explanation.tsx'
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

// The Verdict phase's body: the answer, the ambiguity when it is set, then the
// explanation and the citations, each under a sub-heading.
export function Verdict({ ruling, entries, onOpen }: Props) {
  const cites = ruling.cites.map((cite) => resolveCite(cite, entries))
  const labels = entryLabels(entries)
  // A word or a number reads at display size; a sentence would wrap into a
  // wall at that size, so it steps down to a title.
  const short = ruling.answer.kind !== 'what'

  return (
    <div className="verdict" data-ambiguous={ruling.ambiguous || undefined}>
      <p className={short ? 'verdict__answer text-display-lg' : 'verdict__answer text-title-lg'}>
        {verdictText(ruling.answer)}
      </p>

      {ruling.ambiguous && (
        <p className="verdict__ambiguous">
          {/* Soft primary, not warning: the warning ramp is the secondary gold
              the phase labels use, so a warning badge would read as a label. */}
          <Badge color="primary" intensity="soft" leadingIcon={<Scale />}>
            Ambiguous
          </Badge>
          <span className="text-body-lg text-on-surface-variant">
            The text allows more than one reading. The explanation gives each.
          </span>
        </p>
      )}

      {/* The answer stands alone; the rest sits under sub-headings of its own. */}
      <div className="verdict__part">
        <h3 className="subhead text-label-md">Explanation</h3>
        <Explanation explanation={ruling.explanation} entries={entries} onOpen={onOpen} />
      </div>

      <div className="verdict__part">
        <h3 className="subhead text-label-md">Citations</h3>
        {/* A ruling grounded in no named text is the failure this screen is
            there to show, so the section stays and says so. */}
        {cites.length === 0 ? (
          <p className="verdict__no-cites text-body-lg text-on-surface-variant">The ruling cites no entry.</p>
        ) : (
          <ul className="verdict__cite-list">
            {cites.map((c) => (
              <li key={c.cite}>
                {c.found ? (
                  <Button variant="outline" color="neutral" size="sm" onClick={() => onOpen(c.entry)}>
                    {labels.get(c.entry.path)}
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
        )}
      </div>
    </div>
  )
}
