// A record's view in the panel, built from its record by path: a spell's, a
// monster's or a magic item's. Loading and a failure are said in a live region,
// as the table says its own.
import type { JSX } from 'react'
import { Prose } from '../../shared/Prose.tsx'
import { SpellStats } from './SpellStats.tsx'
import { LoadState } from '../LoadState.tsx'
import { useLoad } from '../use-load.ts'
import { MagicItemStats } from './MagicItemStats.tsx'
import { MonsterStats } from './MonsterStats.tsx'
import { loadView, type View } from './record.ts'

// The return type is written out and there is no default, so a kind added to
// View fails to compile here until it is laid out.
function ViewBody({ view }: { view: View }): JSX.Element {
  switch (view.kind) {
    case 'spell':
      return (
        <>
          <SpellStats spell={view.spell} />
          <Prose>{view.spell.body}</Prose>
        </>
      )
    case 'monster':
      return <MonsterStats monster={view.monster} />
    case 'magic-item':
      return <MagicItemStats item={view.item} />
  }
}

export function RecordView({ path }: { path: string }) {
  const { state, retry } = useLoad(path, async () => {
    const view = await loadView(path)
    if (!view) throw new Error(`no record for ${path}`)
    return view
  })

  return (
    <>
      <LoadState status={state.status} message="This record could not be loaded." onRetry={retry} compact />
      {state.status === 'ready' && <ViewBody view={state.value} />}
    </>
  )
}
