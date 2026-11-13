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
export function Encyclopedia({
  openPath,
  onOpen,
}: {
  openPath: string | null
  onOpen: (entry: PanelEntry) => void
}) {
  const [kind, setKind] = useState<Kind>(KINDS[0])
  // Keyed by root, so a slow file cannot land after a later pick.
  const { state: loaded, retry } = useLoad(kind.root, kind.rows)
  const [search, setSearch] = useState('')
  const [chosen, setChosen] = useState<Record<string, string>>({})
  const [sort, setSort] = useState<Sort>(BY_NAME)
  const [filtersOpen, setFiltersOpen] = useState(false)
  const id = useId()

  const rows = loaded.status === 'ready' ? loaded.value : []
  // Every row of a kind holds the same fields in one order, so the first speaks for all.
  const fields = rows.length > 0 ? Object.keys(rows[0].fields) : []
  const active = Object.keys(chosen).length
  const shown = rows.filter((row) => matches(row, search, chosen))
  const sorted = [...shown].sort(compareRows(sort.field))
  // Reverses ties too, which is harmless.
  if (sort.descending) sorted.reverse()

  // Another kind's fields differ, so choices and sort reset; the search stays.
  const pickKind = (root: string) => {
    const next = KINDS.find((k) => k.root === root)
    if (next) {
      setKind(next)
      setChosen({})
      setSort(BY_NAME)
    }
  }

  const sortBy = (field: string) =>
    setSort((current) =>
      current.field === field ? { field, descending: !current.descending } : { field, descending: false },
    )

  const openRow = (row: Row) => onOpen({ path: row.path, title: row.name })

  const ariaSort = (field: string) =>
    sort.field !== field ? undefined : sort.descending ? 'descending' : 'ascending'

  // A list field has no order of its own: Classes would sort by whichever class is named first.
  const header = (field: string) =>
    Array.isArray(rows[0]?.fields[field]) ? (
      <th key={field} scope="col">
        {field}
      </th>
    ) : (
      <th key={field} scope="col" aria-sort={ariaSort(field)}>
        <button type="button" className="encyclopedia__sort" onClick={() => sortBy(field)}>
          {field}
          {sort.field === field &&
            (sort.descending ? <ArrowDown aria-hidden="true" /> : <ArrowUp aria-hidden="true" />)}
        </button>
      </th>
    )

  const choose = (field: string, value: string) =>
    setChosen((current) => {
      const next = { ...current }
      if (value === ANY) delete next[field]
      else next[field] = value
      return next
    })

  return (
    <main className="column encyclopedia">
      <h1 className="visually-hidden">Encyclopedia</h1>

      <div className="encyclopedia__controls">
        {/* The label's htmlFor names Radix's trigger, which is a button. */}
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

        {/* The label carries the count, so the badge is hidden; it opens with the
            visible "Filters", so voice control can still name the button. */}
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

        {/* Mounted from the first paint: a live region added with its text is often not announced. */}
        <p className="encyclopedia__results text-body-md" aria-live="polite">
          {loaded.status === 'ready' ? `${shown.length} of ${rows.length}` : ''}
        </p>
      </div>

      {/* Hidden, not unmounted, so the choices hold. Ids take the index: labels hold spaces. */}
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

      <LoadState
        status={loaded.status}
        loading={`Loading ${kind.label.toLowerCase()}…`}
        message={`${kind.label} could not be loaded.`}
        onRetry={retry}
      />

      {/* Not live: the count above already announces the zero. */}
      {loaded.status === 'ready' && shown.length === 0 && (
        <p className="encyclopedia__empty text-body-lg text-on-surface-variant">
          {`No ${kind.label.toLowerCase()} match the current search.`}
        </p>
      )}

      {/* tabIndex 0, so the scrolling box can be scrolled by keyboard. */}
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
                    <button
                      type="button"
                      className="link link-prose"
                      aria-expanded={openPath === row.path}
                      onClick={() => openRow(row)}
                    >
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
