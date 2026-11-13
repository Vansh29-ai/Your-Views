import { useSearchParams } from 'react-router-dom'
import { ArchiveFilters, type ArchiveFilterState } from '@/components/ArchiveFilters'
import { ArchivePagination } from '@/components/ArchivePagination'
import { EditionSkeleton, EmptyEdition, ErrorNotice } from '@/components/PaperStates'
import { PressRoom } from '@/components/PressRoom'
import { StoryCard } from '@/components/StoryCard'
import { VintageSearchBar } from '@/components/VintageSearchBar'
import { useEvents, useFacets, useOverview, useTimeline } from '@/hooks/queries'
import { editionDate, formatNumber } from '@/lib/format'
import type { EventSort } from '@/types'

const VALID_SORTS: EventSort[] = ['latest', 'coverage', 'trending', 'oldest', 'relevance']

export function Dashboard() {
  const [params, setParams] = useSearchParams()
  const overview = useOverview()
  const facets = useFacets()
  const timeline = useTimeline(14)

  const page = Math.max(1, Number(params.get('page') ?? 1) || 1)
  const category = params.get('category') ?? undefined
  const publisher = params.get('publisher') ?? undefined
  const query = params.get('q') ?? ''
  const multiOnly = params.get('multi') === '1'
  const requestedSort = params.get('sort') as EventSort | null
  const sort: EventSort = VALID_SORTS.includes(requestedSort ?? 'trending')
    ? (requestedSort ?? 'trending')
    : 'trending'

  const events = useEvents({
    page,
    page_size: 12,
    category,
    publisher,
    q: query || undefined,
    sort,
    min_publishers: multiOnly ? 2 : undefined,
  })

  function update(next: Record<string, string | undefined>) {
    const merged = new URLSearchParams(params)
    for (const [key, value] of Object.entries(next)) {
      if (!value || (key === 'page' && value === '1')) merged.delete(key)
      else merged.set(key, value)
    }
    setParams(merged, { replace: true })
  }

  function onFilterChange(next: Partial<ArchiveFilterState>) {
    update({
      category: next.category,
      publisher: next.publisher,
      sort: next.sort,
      multi:
        next.multiOnly === undefined ? (multiOnly ? '1' : undefined) : next.multiOnly ? '1' : undefined,
      page: '1',
    })
  }

  const data = events.data
  const items = data?.items ?? []
  const hasFilters = Boolean(category || publisher || multiOnly || query)
  const [lead, ...rest] = items

  return (
    <div className="container-paper pb-8 pt-6">
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-rule/60 pb-3">
        <div>
          <p className="kicker">The Archive · {editionDate()}</p>
          <h1 className="mt-2 font-display text-[clamp(2.3rem,4.6vw,3.8rem)] font-extrabold leading-[0.95] tracking-[-0.02em] text-ink">
            The Late Edition
          </h1>
          <p className="mt-2 max-w-xl font-body text-[15px] leading-relaxed text-ink-soft">
            Every event the wire has carried, arranged by prominence. Filter by desk, publisher or
            depth of coverage.
          </p>
        </div>
        <div className="ml-auto text-right">
          <p className="font-display text-[34px] font-extrabold leading-none tabular text-ink">
            {formatNumber(data?.total ?? overview.data?.events_total ?? 0)}
          </p>
          <p className="mt-1 font-typewriter text-[8px] uppercase tracking-[0.14em] text-ink-soft">
            events in this view
          </p>
        </div>
      </div>

      <PressRoom overview={overview.data} timeline={timeline.data} />

      <div className="mt-6">
        <VintageSearchBar
          key={query}
          initialValue={query}
          size="inline"
          label="Search the archive"
          placeholder="Event, headline, publisher or keyword…"
          onSubmit={(value) => update({ q: value, page: '1' })}
        />
      </div>

      <div className="mt-5">
        <ArchiveFilters
          categories={facets.data?.categories ?? []}
          publishers={facets.data?.publishers ?? []}
          value={{ category, publisher, sort, multiOnly }}
          onChange={onFilterChange}
          total={data?.total}
          onClear={() => setParams(new URLSearchParams(), { replace: true })}
        />
      </div>

      <div className="mt-8">
        {events.isError && (
          <ErrorNotice
            title="The archive could not be opened"
            description="The wire returned an error while retrieving this page of events."
            onRetry={() => events.refetch()}
          />
        )}

        {events.isLoading && <EditionSkeleton stories={6} />}

        {!events.isLoading && !events.isError && items.length === 0 && (
          <EmptyEdition
            label={hasFilters ? 'No such dispatch' : 'The archive is empty'}
            title={hasFilters ? 'Nothing matches this desk' : 'The first edition awaits the wire'}
            description={
              hasFilters
                ? 'Try a broader search, another desk, or clear the filters to see the full archive.'
                : 'Run the presses from the room above to collect the first dispatches of the edition.'
            }
            action={
              hasFilters ? (
                <button type="button" className="paper-button" onClick={() => setParams(new URLSearchParams())}>
                  Clear the desk
                </button>
              ) : undefined
            }
          />
        )}

        {!events.isLoading && items.length > 0 && (
          <>
            {lead && (
              <div className="border-b-[3px] border-double border-rule pb-8">
                <StoryCard event={lead} variant="lead" />
              </div>
            )}

            <div className="mt-8 grid gap-x-10 gap-y-8 sm:grid-cols-2 lg:grid-cols-3">
              {rest.map((event) => (
                <StoryCard key={event.id} event={event} variant="column" className="border-t border-rule/50 pt-4" />
              ))}
            </div>

            <ArchivePagination
              page={data?.page ?? 1}
              pages={data?.pages ?? 1}
              onChange={(nextPage) => update({ page: String(nextPage) })}
            />
          </>
        )}
      </div>
    </div>
  )
}
