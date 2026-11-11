// The encyclopedia's view: a kind's records in a table, narrowed by a name
// search and a choice per field, each name opening its record in the source
// panel.
import { ArrowDown, ArrowUp, RotateCcw, SlidersHorizontal } from 'lucide-react'
import { useId, useState } from 'react'
import { Badge } from '../components/loom/badge.tsx'
import { Button } from '../components/loom/button.tsx'
import { FormField } from '../components/loom/form-field.tsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/loom/select.tsx'
import type { PanelEntry } from '../shared/SourcePanel.tsx'
import { compareRows, matches, members, NAME, options } from './filter.ts'
import { KINDS, type Kind } from './load.ts'
import { LoadState } from './LoadState.tsx'
import type { Row } from './rows.ts'
import { useLoad } from './use-load.ts'

// The "Any" item's value: Radix's Select refuses '' as an item's value, and no
// field value in the data is '*'. Choosing it deletes the field's key.
const ANY = '*'

// The column sorted, a field's label or NAME, and its direction.
type Sort = { field: string; descending: boolean }

const BY_NAME: Sort = { field: NAME, descending: false }

// A value as the table and the dropdowns show it, its first letter capitalized:
// "Cantrip", "Yes", "Undead". Display only: the data keeps "cantrip", "yes" and
// "undead", which the sort, the filters and the tests match on.
function display(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

// onOpen is App's open, the one the ask screen's cites call.
export function Encyclopedia({ onOpen }: { onOpen: (entry: PanelEntry) => void }) {
  // The Kind itself rather than its root, so nothing looks it up by force.
  const [kind, setKind] = useState<Kind>(KINDS[0])
  // Keyed by root, so picking Monsters and then Races before the monster file
  // arrives cannot let the monster rows land last.
  const { state: loaded, retry } = useLoad(kind.root, kind.rows)
  const [search, setSearch] = useState('')
  const [chosen, setChosen] = useState<Record<string, string>>({})
  const [sort, setSort] = useState<Sort>(BY_NAME)
  const [filtersOpen, setFiltersOpen] = useState(false)
  // One base for the labels' htmlFor: hooks cannot run inside the field loop,
  // so each field takes a suffix on it.
  const id = useId()


  const rows = loaded.status === 'ready' ? loaded.value : []
  // Every row of a kind holds the same fields in one order, so the first speaks
  // for all. Conditions and weapon properties hold none.
  const fields = rows.length > 0 ? Object.keys(rows[0].fields) : []
  // The filters narrowing the table, for the badge. The search is not counted,
  // since it is always in view.
  const active = Object.keys(chosen).length
  const shown = rows.filter((row) => matches(row, search, chosen))
  // A copy, since sort works in place. Reversing the ascending order for
  // descending reverses rows that tie too, which is harmless and needs no second
  // comparator.
  const sorted = [...shown].sort(compareRows(sort.field))
  if (sort.descending) sorted.reverse()

  // A kind's fields are not another's, so its choices and sort go; the search
  // stays.
  const pickKind = (root: string) => {
    const next = KINDS.find((k) => k.root === root)
    if (next) {
      setKind(next)
      setChosen({})
      setSort(BY_NAME)
    }
  }

  // A second press on the sorted header reverses it; a new one starts ascending.
  const sortBy = (field: string) =>
    setSort((current) =>
      current.field === field ? { field, descending: !current.descending } : { field, descending: false },
    )

  // The panel opens at once with the row's name and loads its text itself, so
  // its loading and failure show in the panel.
  const openRow = (row: Row) => onOpen({ path: row.path, title: row.name })

  // Only the sorted column carries aria-sort; `undefined` leaves it off the rest.
  const ariaSort = (field: string) =>
    sort.field !== field ? undefined : sort.descending ? 'descending' : 'ascending'

  // A header's button and the sorted column's arrow, hidden from screen readers
  // since aria-sort says the direction.
  const header = (field: string) => (
    <th key={field} scope="col" aria-sort={ariaSort(field)}>
      <button type="button" className="encyclopedia__sort" onClick={() => sortBy(field)}>
        {field}
        {sort.field === field &&
          (sort.descending ? <ArrowDown aria-hidden="true" /> : <ArrowUp aria-hidden="true" />)}
      </button>
    </th>
  )

  // A copy, since React sees a change only in a new object.
  const choose = (field: string, value: string) =>
    setChosen((current) => {
      const next = { ...current }
      if (value === ANY) delete next[field]
      else next[field] = value
      return next
    })

  return (
    <main className="column encyclopedia">
      {/* Hidden from sight: the tabs show the view and the kind picker names
          what is in it. It stays for screen readers. */}
      <h1 className="visually-hidden">Encyclopedia</h1>

      <div className="encyclopedia__controls">
        {/* A label's `for` names Radix's trigger, which is a button. The field
            holds one width, and a label longer than it is cut with an
            ellipsis; a screen reader still hears it whole. */}
        <FormField className="encyclopedia__kind">
          <label className="label" data-size="sm" htmlFor={`${id}-kind`}>
            Kind
          </label>
          <Select value={kind.root} onValueChange={pickKind}>
            <SelectTrigger id={`${id}-kind`} className="encyclopedia__kind-trigger">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {KINDS.map((k) => (
                <SelectItem key={k.root} value={k.root}>
                  {k.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </FormField>

        <FormField>
          <label className="label" data-size="sm" htmlFor={`${id}-search`}>
            Name
          </label>
          <input
            id={`${id}-search`}
            className="input"
            data-size="md"
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </FormField>

        {/* aria-expanded says whether the panel is open and aria-controls names
            it. The label holds the count, so the badge is hidden from screen
            readers, which would read it twice; it keeps the visible "Filters"
            first, so a voice user can still say it. */}
        {fields.length > 0 && (
          <>
            <Button
              variant="outline"
              color="neutral"
              className="encyclopedia__filters-button"
              aria-expanded={filtersOpen}
              aria-controls={`${id}-filters`}
              aria-label={active > 0 ? `Filters, ${active} active` : 'Filters'}
              leadingIcon={<SlidersHorizontal aria-hidden="true" />}
              onClick={() => setFiltersOpen((open) => !open)}
            >
              Filters
              {active > 0 && (
                <Badge size="sm" color="primary" className="encyclopedia__badge" aria-hidden="true">
                  {active}
                </Badge>
              )}
            </Button>
            {/* The word as well as the icon: a reset arrow alone reads close to
                the sort arrows beside it. */}
            {active > 0 && (
              <Button
                color="primary"
                intensity="soft"
                leadingIcon={<RotateCcw aria-hidden="true" />}
                onClick={() => setChosen({})}
              >
                Clear
              </Button>
            )}
          </>
        )}

        {/* With the filters it counts, at the row's far end. Rendered from the
            first paint with only its text changing: a live region added in the
            same render as its text is often not announced. */}
        <p className="encyclopedia__results text-body-md" aria-live="polite">
          {loaded.status === 'ready' ? `${shown.length} of ${rows.length}` : ''}
        </p>
      </div>

      {/* Hidden rather than unmounted while closed, so each choice holds and
          the badge counts it. The index goes in each id, since labels such as
          "Damage immunities" hold spaces. */}
      <div id={`${id}-filters`} className="encyclopedia__filters" hidden={!filtersOpen || fields.length === 0}>
        {fields.map((field, i) => (
          <FormField key={field}>
            <label className="label" data-size="sm" htmlFor={`${id}-field-${i}`}>
              {field}
            </label>
            <Select value={chosen[field] ?? ANY} onValueChange={(value) => choose(field, value)}>
              <SelectTrigger id={`${id}-field-${i}`}>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ANY}>Any</SelectItem>
                {options(rows, field).map((option) => (
                  <SelectItem key={option} value={option}>
                    {display(option)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </FormField>
        ))}
      </div>

      {/* The table's place holds one of four states: loading or the failure
          here, then no matches or the table below. */}
      <LoadState
        status={loaded.status}
        loading={`Loading ${kind.label.toLowerCase()}…`}
        message={`${kind.label} could not be loaded.`}
        onRetry={retry}
      />

      {/* Outside the live region: the count already announces "0 of 319". The
          controls stay above it, so the search can be edited and Clear
          pressed. */}
      {loaded.status === 'ready' && shown.length === 0 && (
        <p className="encyclopedia__empty text-body-lg text-on-surface-variant">
          {`No ${kind.label.toLowerCase()} match the current search.`}
        </p>
      )}

      {/* A wide table scrolls in its own box, so the box takes Tab to be
          scrolled by keyboard, and a role and a name to say what it is. The
          name is a th with scope="row", what a screen reader reads as each
          row's header, and a button, since a clickable row reaches no
          keyboard. */}
      {loaded.status === 'ready' && shown.length > 0 && (
        <div className="encyclopedia__table" role="region" aria-label={`${kind.label} table`} tabIndex={0}>
          <table className="table" data-size="sm">
            <caption className="visually-hidden">{kind.label}</caption>
            <thead>
              <tr>
                {header(NAME)}
                {fields.map(header)}
              </tr>
            </thead>
            <tbody>
              {sorted.map((row) => (
                <tr key={row.path}>
                  <th scope="row">
                    <button type="button" className="link link-prose" onClick={() => openRow(row)}>
                      {row.name}
                    </button>
                  </th>
                  {fields.map((field) => (
                    <td key={field}>{members(row, field).map(display).join(', ')}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </main>
  )
}
