// The corpus as the model reads it, split by path, for a record's view on
// command. render_markdown in src/rules_attorney/corpus.py writes each entry as
// a `## <path>` line, a blank line and its text, the blocks joined by blank
// lines; a `## ` line at a line's start is always a path, since no entry's text
// holds one.

export function splitCorpus(markdown: string): Map<string, string> {
  const entries = new Map<string, string>()
  // The file opens with `## `, so the first piece is empty.
  for (const block of markdown.split(/^## /m).slice(1)) {
    const newline = block.indexOf('\n')
    // Safe to trim: no entry's text begins or ends with whitespace.
    entries.set(block.slice(0, newline), block.slice(newline).trim())
  }
  return entries
}

// supplement.json's passages, the rules the SRD document's prose holds and no
// source file does, copied by hand. Each op is its own variant, so a check on
// `op` narrows to the keys that variant has: only an insert has `after`.
type PassageBase = { path: string; pages: number[]; text: string[] }

export type Passage =
  | (PassageBase & { op: 'append' })
  | (PassageBase & { op: 'insert'; after: string })
  | (PassageBase & { op: 'new' })

export type Supplement = { passages: Passage[] }

// What a record's view shows under it, and the SRD pages it comes from.
export type Addition = { text: string; pages: number[] }

// The text the supplement adds to an entry. An append is its paragraphs; an
// insert completes a run of text, a reaction spell's `Casting time: 1
// reaction`, and reads with that run before it, since its fragment means
// nothing alone. The joins are supplement_joins' in src/rules_attorney/corpus.py.
// A `new` passage makes an entry of its own and adds to none, so it matches
// neither branch.
export function additions(supplement: Supplement, path: string): Addition[] {
  const found: Addition[] = []
  for (const passage of supplement.passages) {
    if (passage.path !== path) continue
    if (passage.op === 'append') found.push({ text: passage.text.join('\n\n'), pages: passage.pages })
    else if (passage.op === 'insert') found.push({ text: `${passage.after}${passage.text.join('')}`, pages: passage.pages })
  }
  return found
}
