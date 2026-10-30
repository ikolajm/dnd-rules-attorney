import { ChevronRight } from 'lucide-react'
import { Badge } from './components/loom/badge.tsx'
import { entryLabel, resolveCite } from './cites.ts'
import type { Entry } from './types.ts'

type Props = {
  entries: Entry[]
  // Null until the ruling lands, when the cited entries can be marked.
  cites: string[] | null
  onOpen: (entry: Entry) => void
}

export function ViewAll({ entries, cites, onOpen }: Props) {
  const cited = new Set(
    (cites ?? []).flatMap((cite) => {
      const c = resolveCite(cite, entries)
      return c.found ? [c.entry.path] : []
    }),
  )

  return (
    <details className="view-all">
      <summary className="view-all__summary text-label-lg">
        <ChevronRight className="view-all__chevron" aria-hidden="true" />
        {entries.length} entries retrieved{cites && `, ${cited.size} cited`}
      </summary>
      <ol className="view-all__list">
        {entries.map((entry) => (
          <li key={entry.path}>
            <button type="button" className="view-all__entry list-item interactive" data-size="md" onClick={() => onOpen(entry)}>
              <span className="text-body-md">{entryLabel(entry)}</span>
              {cited.has(entry.path) && (
                <Badge size="sm" color="primary" intensity="soft">
                  Cited
                </Badge>
              )}
            </button>
          </li>
        ))}
      </ol>
    </details>
  )
}
