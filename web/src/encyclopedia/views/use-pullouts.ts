// The entries an entry's lists open to, once the corpus is loaded to find them
// in. From the encyclopedia it already is; a cited race or weapon carries only
// its own text, so the corpus loads here, and a row opened before it arrives
// says so.
import { corpus } from '../load.ts'
import { useLoad, type Load } from '../use-load.ts'
import { PULLOUT_HEADINGS, pullouts, type Pullouts } from './pullouts.ts'
import type { Section } from './section.ts'

export function usePullouts(path: string, sections: Section[]): { state: Load<Pullouts>; retry: () => void } {
  const lists = sections.filter((s) => s.kind === 'list' && PULLOUT_HEADINGS.has(s.heading))
  // Keyed by path, since an entry's sections follow from it; null loads nothing.
  return useLoad(lists.length > 0 ? path : null, async () => pullouts(path, lists, await corpus()))
}
