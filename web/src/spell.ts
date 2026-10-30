// A spell's stat lines laid out for reading. The corpus writes every spell the
// same way, eight lines in one order, `Level: cantrip` to `Ritual: no`, and that
// text is what the model was measured on, so it stays; this is display only.

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

  const level = field['Level'] === 'cantrip' ? 'Cantrip' : `Level ${field['Level']}`
  const ritual = field['Ritual'] === 'yes' ? ' · Ritual' : ''

  // The corpus writes "Up to 1 minute" exactly when concentration is yes, on
  // every spell, so the two fold into the SRD's own wording with nothing lost.
  const duration = field['Concentration'] === 'yes' ? `Concentration, ${lowerFirst(field['Duration'])}` : field['Duration']

  return {
    subtitle: `${level} · ${field['School']}${ritual}`,
    castingTime: field['Casting time'],
    range: field['Range'],
    verbal: letters.includes('V'),
    somatic: letters.includes('S'),
    material: letters.includes('M') ? (components[2] ?? null) : null,
    duration,
    // The SRD sets "At Higher Levels." as a bold lead-in; the corpus runs it
    // into the text.
    body: rest.replace(/^At Higher Levels\. /m, '**At Higher Levels.** '),
  }
}

function lowerFirst(text: string): string {
  return text.charAt(0).toLowerCase() + text.slice(1)
}
