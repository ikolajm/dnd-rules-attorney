// The roots whose paths have a view built from their record. Apart from
// record.ts, which imports the loaders, so the panel and the tests can ask
// without them: Node cannot run the loaders' Vite `?url` imports.
import { pathRoot } from '../../cites.ts'

// `as const` keeps each root a literal, so `Root` is their union and the
// switch in record.ts's loadView can check it has a case for every one.
export const ROOTS = ['spells', 'monsters', 'magic-items'] as const
export type Root = (typeof ROOTS)[number]

// A type guard: true narrows the string to Root where it is called, so no
// cast is needed. `some` rather than `includes`, which on the literal tuple
// refuses a plain string.
function isRoot(root: string): root is Root {
  return ROOTS.some((r) => r === root)
}

// "monsters > aboleth" to "monsters", or null for a root with no view.
export function rootOf(path: string): Root | null {
  const root = pathRoot(path)
  return isRoot(root) ? root : null
}

export function hasView(path: string): boolean {
  return rootOf(path) !== null
}
