// Every corpus entry opens with its own title on a line of its own: "Fire Bolt",
// where the path's slug only gives "fire-bolt". Most follow it with a blank
// line; six follow it straight with a list or a table, Strength's skills and
// the coin exchange rates among them. The panel shows that line as its heading
// and renders the body after it. Display only: the entry the model was handed
// keeps its title.
const TITLE = /^([^\n]+)\n+/

// The entry's title as the source writes it, or null for text with no line
// break, which no entry has, so the caller falls back to one built from the
// path.
export function entryTitle(text: string): string | null {
  return TITLE.exec(text)?.[1] ?? null
}

export function entryBody(text: string): string {
  const match = TITLE.exec(text)
  return joinTableRows(match ? text.slice(match[0].length) : text)
}

// The SRD data stores a spell's description as a list of paragraphs, a table's
// rows among them, and the corpus joins those with blank lines. A blank line
// ends a markdown table, so seven spells' tables, Control Weather's among them,
// would render as a paragraph per row. A blank line between two table rows is
// closed up; every other blank line stays. Display only, as above: the corpus
// keeps the text the model was measured on.
function joinTableRows(text: string): string {
  return text.replace(/(\|[ \t]*)\n\n(?=[ \t]*\|)/g, '$1\n')
}
