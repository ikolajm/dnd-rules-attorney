import type { Entry } from './types.ts'

// The model's commonest slip is copying the `## ` the prompt puts before each
// path. Stripped, the cite names one of the ten entries or none at all; on the
// level 3 dev run no cite named a corpus section outside the ten.
const MARKER = /^##\s*/

export type ResolvedCite =
  | { found: true; cite: string; entry: Entry }
  | { found: false; cite: string }

export function resolveCite(cite: string, entries: Entry[]): ResolvedCite {
  const path = cite.replace(MARKER, '').trim()
  const entry = entries.find((e) => e.path === path)
  return entry ? { found: true, cite, entry } : { found: false, cite }
}

// "making-an-attack > melee-attacks" reads as "Making an attack › Melee attacks".
export function pathSegments(path: string): string[] {
  return path.split(' > ').map((slug) => {
    const words = slug.replace(/-/g, ' ')
    return words.charAt(0).toUpperCase() + words.slice(1)
  })
}

export function pathLabel(path: string): string {
  return pathSegments(path).join(' › ')
}

export type ExplanationPart = { text: string } | { text: string; entry: Entry }

// The explanation names entries by path inline, most often in single quotes:
// 'making-an-attack > melee-attacks'. Each path of the ten becomes a link that
// reads as the entry's title, "Making an attack › Melee attacks", so the prose
// reads as prose. The match takes in a leading marker and any quotes around the
// path, so neither is left behind as text; parentheses stay, since they carry
// the sentence. Longest first, so a path is never matched as the prefix of a
// longer one.
export function linkExplanation(explanation: string, entries: Entry[]): ExplanationPart[] {
  if (entries.length === 0) return [{ text: explanation }]
  const byPath = new Map(entries.map((e) => [e.path, e]))
  const escaped = [...byPath.keys()]
    .sort((a, b) => b.length - a.length)
    .map((p) => p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  const quote = `['"\`]?`
  const pattern = new RegExp(`${quote}(?:##\\s*)?${quote}(${escaped.join('|')})${quote}`, 'g')

  const parts: ExplanationPart[] = []
  let last = 0
  for (const match of explanation.matchAll(pattern)) {
    if (match.index > last) parts.push({ text: explanation.slice(last, match.index) })
    const entry = byPath.get(match[1])!
    parts.push({ text: pathLabel(entry.path), entry })
    last = match.index + match[0].length
  }
  if (last < explanation.length) parts.push({ text: explanation.slice(last) })
  return parts
}
