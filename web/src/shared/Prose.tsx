// The corpus's markdown as the panel renders it, shared by the panel and the
// stat blocks, whose traits hold markdown lists and line breaks.
import Markdown, { type Components } from 'react-markdown'
import remarkBreaks from 'remark-breaks'
import remarkGfm from 'remark-gfm'

// Tables are GFM, not CommonMark. Breaks keeps each single line break, which
// two rule sections write as one; the spells' stat lines, which wrote most of
// them, are laid out by SpellStats instead.
const PLUGINS = [remarkGfm, remarkBreaks]

// The corpus's markdown onto Loom. Headings inside an entry sit under the
// panel's own h2, whatever level the source wrote them at, and a table scrolls
// on its own rather than widening the panel.
const ELEMENTS: Components = {
  h1: ({ children }) => <h3 className="text-title-sm">{children}</h3>,
  h2: ({ children }) => <h3 className="text-title-sm">{children}</h3>,
  h3: ({ children }) => <h3 className="text-title-sm">{children}</h3>,
  h4: ({ children }) => <h3 className="text-title-sm">{children}</h3>,
  h5: ({ children }) => <h3 className="text-title-sm">{children}</h3>,
  h6: ({ children }) => <h3 className="text-title-sm">{children}</h3>,
  table: ({ children }) => (
    <div className="source-panel__table">
      <table className="table">{children}</table>
    </div>
  ),
}

export function Prose({ children }: { children: string }) {
  return (
    <Markdown remarkPlugins={PLUGINS} components={ELEMENTS}>
      {children}
    </Markdown>
  )
}
