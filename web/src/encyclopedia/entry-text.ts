// The source text for the panel's entry. A cite's entry carries its text from
// the run; a row opened from the encyclopedia carries only its path and name,
// and its text loads here with the corpus, so the panel opens at once and says
// in its own body that the text is loading or could not be loaded.
import type { PanelEntry } from '../shared/SourcePanel.tsx'
import { corpus } from './load.ts'
import { useLoad, type Load } from './use-load.ts'

export function useEntryText(entry: PanelEntry): { text: Load<string>; retry: () => void } {
  const given = 'text' in entry ? entry.text : null
  // A cite's text needs no load, so its key is null. A path the corpus lacks
  // fails, the error saying which; every row's path is a corpus path, which
  // rows.test.ts proves.
  const { state, retry } = useLoad(given === null ? entry.path : null, async () => {
    const text = (await corpus()).get(entry.path)
    if (text === undefined) throw new Error(`no corpus entry for ${entry.path}`)
    return text
  })
  return { text: given === null ? state : { status: 'ready', value: given }, retry }
}
