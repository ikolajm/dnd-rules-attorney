import { entryTitle } from './entry.ts'
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

// An entry as the screen names it: its own title line, "Fire Bolt", alone. The
// trail of parent sections shows only in the source panel, and is built from
// the path, since the parents' own entries are seldom among the ten.
export function entryLabel(entry: Entry): string {
  const segments = pathSegments(entry.path)
  return entryTitle(entry.text) ?? segments[segments.length - 1]
}

// How a run names each of its entries, by path. A title stands alone unless
// another of the run's entries shares it; then each takes its parent section in
// parentheses, "Spellcasting Ability (Intelligence)", so the three Spellcasting
// Ability entries under Intelligence, Wisdom and Charisma read apart. The title
// stays first, so a list still scans by title. Every place a run names an
// entry reads these, so the citations, the rules list and the explanation's
// links agree.
export function entryLabels(entries: Entry[]): Map<string, string> {
  const titles = new Map(entries.map((e) => [e.path, entryLabel(e)]))
  const counts = new Map<string, number>()
  for (const title of titles.values()) counts.set(title, (counts.get(title) ?? 0) + 1)

  const labels = new Map<string, string>()
  for (const [path, title] of titles) {
    const segments = pathSegments(path)
    const parent = segments[segments.length - 2]
    labels.set(path, counts.get(title)! > 1 && parent ? `${title} (${parent})` : title)
  }
  return labels
}

export type ExplanationPart = { text: string } | { text: string; entry: Entry }

// The explanation names entries by path inline, most often in single quotes:
// 'making-an-attack > melee-attacks'. Each path of the ten becomes a link that
// reads as the run names that entry, "Melee Attacks", so the prose reads as
// prose. The match takes in a leading marker and any quotes around the path, so
// neither is left behind as text; parentheses stay, since they carry the
// sentence. Longest first, so a path is never matched as the prefix of a
// longer one.
export function linkExplanation(explanation: string, entries: Entry[]): ExplanationPart[] {
  if (entries.length === 0) return [{ text: explanation }]
  const labels = entryLabels(entries)
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
    parts.push({ text: labels.get(entry.path)!, entry })
    last = match.index + match[0].length
  }
  if (last < explanation.length) parts.push({ text: explanation.slice(last) })
  return parts
}
