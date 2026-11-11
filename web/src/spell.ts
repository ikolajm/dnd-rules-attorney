// A spell's stat lines laid out for reading, built two ways: from its record,
// as the panel opens it, and parsed from its corpus text, which the tests hold
// the record's build to. The corpus writes every spell the same way, eight lines in one
// order, `Level: cantrip` to `Ritual: no`, and that text is what the model was
// measured on, so it stays; this is display only.
import type { Supplement } from './encyclopedia/corpus-text.ts'
import type { SpellRecord } from './encyclopedia/rows.ts'
import { joinTableRows } from './entry.ts'

export type Spell = {
  // "Cantrip · Evocation", "Level 8 · Transmutation · Ritual".
  subtitle: string
  castingTime: string
  range: string
  verbal: boolean
  somatic: boolean
  // The material sentence as the data writes it, its parentheses stripped, or
  // null when the spell has no material component.
  material: string | null
  // "Concentration, up to 8 hours" when the spell takes concentration.
  duration: string
  // The description after the stat lines, as markdown.
  body: string
}

const KEYS = ['Level', 'School', 'Casting time', 'Range', 'Components', 'Duration', 'Concentration', 'Ritual']

// "Cantrip · Evocation", "Level 8 · Transmutation · Ritual". The level is the
// corpus's word, 'cantrip' or '3', which both builders hold.
function subtitle(level: string, school: string, ritual: boolean): string {
  const lead = level === 'cantrip' ? 'Cantrip' : `Level ${level}`
  return `${lead} · ${school}${ritual ? ' · Ritual' : ''}`
}

// The data writes "Up to 1 minute" exactly when concentration is yes, on every
// spell, so the two fold into the SRD's own wording with nothing lost.
function withConcentration(duration: string, concentration: boolean): string {
  return concentration ? `Concentration, ${lowerFirst(duration)}` : duration
}

// The spell in an entry's body, its title already dropped, or null when the
// stat lines are not the eight the corpus writes, so the caller renders the
// body as it stands.
export function parseSpell(body: string): Spell | null {
  const split = body.indexOf('\n\n')
  const head = split === -1 ? body : body.slice(0, split)
  const rest = split === -1 ? '' : body.slice(split + 2)

  const lines = head.split('\n')
  if (lines.length !== KEYS.length) return null
  const field: Record<string, string> = {}
  for (const [i, line] of lines.entries()) {
    const prefix = `${KEYS[i]}: `
    if (!line.startsWith(prefix)) return null
    field[KEYS[i]] = line.slice(prefix.length)
  }

  // "V, S, M (A tiny bell.)": the letters before the parenthesis, the
  // material sentence inside it.
  const components = /^([VSM, ]+?)(?: \((.*)\))?$/.exec(field['Components'])
  if (!components) return null
  const letters = components[1].split(', ')

  return {
    subtitle: subtitle(field['Level'], field['School'], field['Ritual'] === 'yes'),
    castingTime: field['Casting time'],
    range: field['Range'],
    verbal: letters.includes('V'),
    somatic: letters.includes('S'),
    material: letters.includes('M') ? (components[2] ?? null) : null,
    duration: withConcentration(field['Duration'], field['Concentration'] === 'yes'),
    // The SRD sets "At Higher Levels." as a bold lead-in; the corpus runs it
    // into the text.
    body: rest.replace(/^At Higher Levels\. /m, '**At Higher Levels.** '),
  }
}

// The record's Spell, which SpellStats lays out as it does the corpus's. The
// description joins its paragraphs as src/rules_attorney/corpus.py does, with
// At Higher Levels set bold here where the corpus runs it into the text.
// `.length` rather than the list itself: an empty list is truthy here, where
// corpus.py's `if higher:` skips one. The four reaction spells' casting times
// take the supplement's insert, "1 reaction, which you take when you see…",
// since the clause means nothing apart from the line it completes, which is
// how the corpus reads it too.
export function spellFromRecord(record: SpellRecord, supplement: Supplement): Spell {
  const after = `Casting time: ${record.casting_time}`
  const inserted = supplement.passages
    .filter((p) => p.op === 'insert' && p.path === `spells > ${record.index}` && p.after === after)
    .map((p) => p.text.join(''))
    .join('')
  const higher = record.higher_level?.length ? [`**At Higher Levels.** ${record.higher_level.join('\n\n')}`] : []
  return {
    subtitle: subtitle(record.level === 0 ? 'cantrip' : String(record.level), record.school.name, record.ritual),
    castingTime: record.casting_time + inserted,
    range: record.range,
    verbal: record.components.includes('V'),
    somatic: record.components.includes('S'),
    material: record.components.includes('M') ? (record.material ?? null) : null,
    duration: withConcentration(record.duration, record.concentration),
    body: joinTableRows([...record.desc, ...higher].join('\n\n')),
  }
}

function lowerFirst(text: string): string {
  return text.charAt(0).toLowerCase() + text.slice(1)
}
