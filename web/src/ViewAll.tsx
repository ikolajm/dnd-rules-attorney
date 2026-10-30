import { ChevronRight, Quote } from 'lucide-react'
import { entryLabels, resolveCite } from './cites.ts'
import type { Entry } from './types.ts'

type Props = {
  entries: Entry[]
  // Null until the ruling lands, when the cited entries can be marked.
  cites: string[] | null
  onOpen: (entry: Entry) => void
}

// The ten entries retrieval handed over, in merged order, behind one line. Open,
// a numbered list of links, spaced as the sub-questions are, each cited one
// marked once the ruling lands.
export function ViewAll({ entries, cites, onOpen }: Props) {
  const cited = new Set(
    (cites ?? []).flatMap((cite) => {
      const c = resolveCite(cite, entries)
      return c.found ? [c.entry.path] : []
    }),
  )
  const labels = entryLabels(entries)

  return (
    <details className="view-all">
      <summary className="view-all__summary text-body-lg">
        <ChevronRight className="view-all__chevron" aria-hidden="true" />
        {entries.length} entries retrieved{cites && `, ${cited.size} cited`}
      </summary>
      <ol className="view-all__list text-body-lg">
        {entries.map((entry) => (
          <li key={entry.path}>
            <button type="button" className="link link-prose" onClick={() => onOpen(entry)}>
              {labels.get(entry.path)}
            </button>
            {/* An icon, named for a screen reader, beside each entry the ruling
                cites: what retrieval found set beside what the ruling used. */}
            {cited.has(entry.path) && <Quote className="view-all__cited" role="img" aria-label="Cited" />}
          </li>
        ))}
      </ol>
    </details>
  )
}
