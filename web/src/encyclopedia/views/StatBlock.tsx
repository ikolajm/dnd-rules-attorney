// The parts every stat block lays out the same way: its headed sections, each
// rows of label and value or a bulleted list.
import { ChevronDown } from 'lucide-react'
import { Fragment, type JSX, type ReactNode } from 'react'
import type { Line, Section } from './section.ts'

// What a list item opens to in place, by its section's heading and its text: a
// race's trait to its rule. Undefined for an item that opens to nothing.
export type Expand = (heading: string, item: string) => ReactNode | undefined

// A dl may group each dt and dd in a div, and the div is what draws the row's
// one rule across both columns. A label alone can repeat, so the key takes the
// value too.
function Rows({ lines }: { lines: Line[] }) {
  return (
    <dl className="stat-rows text-body-md">
      {lines.map((line) => (
        <div key={`${line.label} ${line.value}`}>
          <dt>{line.label}</dt>
          <dd>{line.value}</dd>
        </div>
      ))}
    </dl>
  )
}

// Rows, or a list for entries too long for a value: left-aligned, full width,
// a bullet each. There is no default, and the return type is written out, so
// deleting a case fails to compile; left to inference, the missing case would
// return undefined and render nothing.
//
// A list whose items open in place, a race's traits, is a ruled list of
// disclosures instead: <details> and <summary> carry the keyboard and the
// open state a screen reader announces, and the chevron says a row opens.
function SectionBody({ section, expand }: { section: Section; expand?: Expand }): JSX.Element {
  switch (section.kind) {
    case 'rows':
      return <Rows lines={section.lines} />
    case 'list': {
      const contents = section.items.map((item) => expand?.(section.heading, item))
      if (contents.every((content) => content === undefined)) {
        return (
          <ul className="stat-block__list text-body-md">
            {section.items.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        )
      }
      return (
        <ul className="stat-block__pullouts text-body-md">
          {section.items.map((item, i) => (
            <li key={item}>
              {contents[i] === undefined ? (
                item
              ) : (
                <details>
                  <summary>
                    <span>{item}</span>
                    <ChevronDown aria-hidden="true" />
                  </summary>
                  {/* Live for text that arrives or fails in an open row; opening one is not announced. */}
                  <div className="stat-block__pullout" aria-live="polite">
                    {contents[i]}
                  </div>
                </details>
              )}
            </li>
          ))}
        </ul>
      )
    }
  }
}

// Each section under its heading. The panel's title is the h2, so a section's
// heading is an h3, the level Prose gives a corpus heading.
export function Sections({ sections, expand }: { sections: Section[]; expand?: Expand }) {
  return sections.map((s) => (
    <Fragment key={s.heading}>
      <h3 className="text-title-sm">{s.heading}</h3>
      <SectionBody section={s} expand={expand} />
    </Fragment>
  ))
}
