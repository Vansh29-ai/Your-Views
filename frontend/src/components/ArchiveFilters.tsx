import { cn, formatNumber } from '@/lib/format'
import type { EventSort, FacetValue } from '@/types'

export interface ArchiveFilterState {
  category?: string
  publisher?: string
  sort: EventSort
  multiOnly: boolean
}

interface ArchiveFiltersProps {
  categories: FacetValue[]
  publishers: FacetValue[]
  value: ArchiveFilterState
  onChange: (next: Partial<ArchiveFilterState>) => void
  total?: number
  onClear: () => void
}

const SORTS: { value: EventSort; label: string }[] = [
  { value: 'trending', label: 'By Prominence' },
  { value: 'latest', label: 'Most Recent' },
  { value: 'coverage', label: 'Most Covered' },
  { value: 'oldest', label: 'Oldest First' },
]

export function ArchiveFilters({ categories, publishers, value, onChange, total, onClear }: ArchiveFiltersProps) {
  const active = Boolean(value.category || value.publisher || value.multiOnly)

  return (
    <div className="border-y border-rule/60 py-3">
      <div className="flex items-start gap-3">
        <span className="mt-1.5 hidden shrink-0 font-typewriter text-[9px] uppercase tracking-[0.14em] text-ink-soft sm:block">
          Desks
        </span>
        <div className="no-scrollbar flex flex-1 flex-wrap items-center gap-x-4 gap-y-1 whitespace-nowrap sm:flex-nowrap sm:overflow-x-auto">
          <button
            type="button"
            onClick={() => onChange({ category: undefined })}
            className={cn(
              'border-b border-transparent pb-0.5 font-typewriter text-[9px] uppercase tracking-[0.12em] transition-colors',
              !value.category ? 'border-oxblood text-oxblood' : 'text-ink-soft hover:text-ink',
            )}
          >
            All Desks
          </button>
          {categories.slice(0, 9).map((category) => (
            <button
              key={category.value}
              type="button"
              onClick={() => onChange({ category: value.category === category.value ? undefined : category.value })}
              className={cn(
                'border-b border-transparent pb-0.5 font-typewriter text-[9px] uppercase tracking-[0.12em] transition-colors',
                value.category === category.value ? 'border-oxblood text-oxblood' : 'text-ink-soft hover:text-ink',
              )}
            >
              {category.label}
              <span className="ml-1.5 text-[8px] tabular text-ink-soft/70">{category.count}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-4 flex flex-wrap items-end justify-between gap-x-6 gap-y-3">
        <div className="flex flex-wrap items-end gap-x-5 gap-y-3">
          <label className="flex flex-col gap-1">
            <span className="kicker text-[8px]">Publisher</span>
            <select
              value={value.publisher ?? ''}
              onChange={(event) => onChange({ publisher: event.target.value || undefined })}
              className="paper-select"
            >
              <option value="">All Publishers</option>
              {publishers.map((publisher) => (
                <option key={publisher.value} value={publisher.value}>
                  {publisher.label} ({publisher.count})
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-1">
            <span className="kicker text-[8px]">Order</span>
            <select
              value={value.sort}
              onChange={(event) => onChange({ sort: event.target.value as EventSort })}
              className="paper-select"
            >
              {SORTS.map((sort) => (
                <option key={sort.value} value={sort.value}>
                  {sort.label}
                </option>
              ))}
            </select>
          </label>

          <button
            type="button"
            onClick={() => onChange({ multiOnly: !value.multiOnly })}
            className={cn('paper-check h-10', value.multiOnly && 'paper-check-active text-ink')}
            aria-pressed={value.multiOnly}
          >
            <span className="paper-check-box">{value.multiOnly && '×'}</span>
            Multi-source only
          </button>
        </div>

        <div className="flex items-center gap-4">
          {typeof total === 'number' && (
            <span className="font-typewriter text-[9px] uppercase tracking-[0.12em] text-ink-soft">
              {formatNumber(total)} dispatches in view
            </span>
          )}
          {active && (
            <button type="button" onClick={onClear} className="underline-link">
              Clear the desk
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
