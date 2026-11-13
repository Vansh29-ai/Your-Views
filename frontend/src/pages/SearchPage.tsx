import { Link, useSearchParams } from 'react-router-dom'
import { ArrowUpRight, Clock } from 'lucide-react'
import { StoryCard } from '@/components/StoryCard'
import { EditionSkeleton, EmptyEdition, ErrorNotice } from '@/components/PaperStates'
import { VintageSearchBar } from '@/components/VintageSearchBar'
import { useFacets, useSearch } from '@/hooks/queries'
import { cn, formatDate, formatNumber, relativeTime } from '@/lib/format'

export function SearchPage() {
  const [params, setParams] = useSearchParams()
  const query = (params.get('q') ?? '').trim()
  const category = params.get('category') ?? undefined
  const publisher = params.get('publisher') ?? undefined
  const results = useSearch(query, category, publisher)
  const facets = useFacets()

  function update(next: Record<string, string | undefined>) {
    const merged = new URLSearchParams(params)
    for (const [key, value] of Object.entries(next)) {
      if (!value) merged.delete(key)
      else merged.set(key, value)
    }
    setParams(merged, { replace: true })
  }

  const events = results.data?.events ?? []
  const hasFilters = Boolean(category || publisher)

  return (
    <div className="container-paper pb-10 pt-6">
      <header className="border-b-[3px] border-double border-rule pb-8 pt-4 text-center">
        <p className="kicker">The Index · Archive of Events</p>
        <h1 className="mx-auto mt-3 max-w-4xl font-display text-[clamp(2.4rem,5.2vw,4.4rem)] font-extrabold leading-[0.95] tracking-[-0.02em] text-ink">
          Consult the Archive
        </h1>
        <p className="mx-auto mt-3 max-w-xl font-body text-[15px] leading-relaxed text-ink-soft">
          Search the edition by event, headline, publisher or keyword. Results are grouped by the
          story, not by the article.
        </p>
        <div className="mx-auto mt-7 max-w-3xl text-left">
          <VintageSearchBar
            key={query}
            initialValue={query}
            size="hero"
            autoFocus={!query}
            label="Search the index"
            placeholder="Try “election”, “climate”, “central bank”…"
            onSubmit={(value) => update({ q: value })}
          />
        </div>
      </header>

      {!query && (
        <div className="mx-auto mt-10 max-w-4xl">
          <div className="flex items-center gap-3">
            <h2 className="section-title">Begin With a Desk</h2>
            <span className="h-px flex-1 bg-rule/60" />
          </div>
          <div className="mt-4 grid gap-x-8 gap-y-0 sm:grid-cols-2">
            {(facets.data?.categories ?? []).map((item) => (
              <Link
                key={item.value}
                to={`/dashboard?category=${encodeURIComponent(item.value)}`}
                className="group flex items-baseline justify-between gap-3 border-b border-rule/40 py-3 transition-colors hover:text-oxblood"
              >
                <span className="font-display text-[20px] font-bold">{item.label}</span>
                <span className="font-typewriter text-[9px] uppercase tracking-[0.1em] text-ink-soft">
                  {item.count} events
                </span>
              </Link>
            ))}
          </div>

          <div className="mt-8 grid gap-4 border-y border-rule/60 py-5 sm:grid-cols-3">
            {[
              ['Event-first', 'Results are clusters of reporting on one occurrence.'],
              ['Publisher-aware', 'Search a newsroom to see the events it covered.'],
              ['Sourced', 'Every result links back to the original reporting.'],
            ].map(([title, body]) => (
              <div key={title}>
                <p className="kicker text-[8px]">{title}</p>
                <p className="mt-1.5 font-body text-[13px] leading-relaxed text-ink-soft">{body}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {query.length === 1 && (
        <p className="mx-auto mt-8 max-w-md text-center font-body text-[14px] italic text-ink-soft">
          The index requires at least two characters. Add another letter to consult the archive.
        </p>
      )}

      {query.length >= 2 && (
        <>
          <div className="mt-6 border-y border-rule/60 py-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <span className="font-typewriter text-[9px] uppercase tracking-[0.12em] text-ink-soft">
                {results.isLoading
                  ? 'Consulting the index…'
                  : `${formatNumber(results.data?.total ?? 0)} results · ${results.data?.took_ms ?? 0}ms`}
              </span>
              <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
                <label className="flex items-center gap-2">
                  <span className="kicker text-[8px]">Desk</span>
                  <select
                    value={category ?? ''}
                    onChange={(event) => update({ category: event.target.value || undefined })}
                    className="paper-select h-8"
                  >
                    <option value="">All Desks</option>
                    {(facets.data?.categories ?? []).map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="flex items-center gap-2">
                  <span className="kicker text-[8px]">Publisher</span>
                  <select
                    value={publisher ?? ''}
                    onChange={(event) => update({ publisher: event.target.value || undefined })}
                    className="paper-select h-8"
                  >
                    <option value="">All Publishers</option>
                    {(facets.data?.publishers ?? []).map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </select>
                </label>
                {hasFilters && (
                  <button
                    type="button"
                    onClick={() => update({ category: undefined, publisher: undefined })}
                    className="font-typewriter text-[8px] uppercase tracking-[0.1em] text-oxblood underline underline-offset-2"
                  >
                    Clear filters
                  </button>
                )}
              </div>
            </div>

            {results.data && results.data.suggestions.length > 0 && (
              <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 border-t border-rule/30 pt-2">
                <span className="kicker text-[8px]">Related in the archive</span>
                {results.data.suggestions.slice(0, 3).map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => update({ q: suggestion })}
                    className="max-w-[280px] truncate font-body text-[12.5px] italic text-ink-soft underline-offset-2 hover:text-oxblood hover:underline"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}
          </div>

          {results.isError && (
            <div className="mt-6">
              <ErrorNotice
                title="The index could not be consulted"
                description="The search desk returned an error. Try again in a moment."
                onRetry={() => results.refetch()}
              />
            </div>
          )}

          {results.isLoading && (
            <div className="mt-8">
              <EditionSkeleton stories={3} />
            </div>
          )}

          {!results.isLoading && results.data && (
            <>
              {events.length > 0 && (
                <section className="mt-8">
                  <div className="border-b-[3px] border-double border-rule pb-1.5">
                    <div className="flex items-baseline justify-between gap-3">
                      <h2 className="section-title">Events in the Archive</h2>
                      <span className="font-typewriter text-[8px] uppercase tracking-[0.12em] text-ink-soft">
                        {events.length} shown
                      </span>
                    </div>
                  </div>
                  <div className="mt-2">
                    {events.map((event, index) => (
                      <StoryCard
                        key={event.id}
                        event={event}
                        variant={index === 0 ? 'archive' : 'archive'}
                        className={cn(index === 0 && 'pt-4')}
                      />
                    ))}
                  </div>
                </section>
              )}

              {(results.data.articles.length > 0 || results.data.publishers.length > 0) && (
                <div className="mt-12 grid gap-10 lg:grid-cols-12">
                  {results.data.articles.length > 0 && (
                    <section className="lg:col-span-8">
                      <div className="border-b-[3px] border-double border-rule pb-1.5">
                        <h2 className="section-title">Headlines from the Wire</h2>
                      </div>
                      <div className="mt-2">
                        {results.data.articles.map((article) => (
                          <div key={article.id} className="border-b border-rule/40 py-3">
                            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-typewriter text-[8px] uppercase tracking-[0.1em] text-ink-soft">
                              <span className="text-oxblood">{article.publisher.short_name}</span>
                              <span>·</span>
                              <Clock size={9} />
                              <span>{formatDate(article.published_at)}</span>
                              <span>·</span>
                              <span>{relativeTime(article.published_at)}</span>
                            </div>
                            <a
                              href={article.url}
                              target="_blank"
                              rel="noreferrer noopener"
                              className="ink-link mt-1 inline-flex items-start gap-2 font-display text-[17px] font-bold leading-snug"
                            >
                              {article.title}
                              <ArrowUpRight size={12} className="mt-1 shrink-0" />
                            </a>
                          </div>
                        ))}
                      </div>
                    </section>
                  )}

                  {results.data.publishers.length > 0 && (
                    <aside className="lg:col-span-4 lg:border-l lg:border-rule/60 lg:pl-7">
                      <div className="border-b-[3px] border-double border-rule pb-1.5">
                        <h2 className="section-title">Sources</h2>
                      </div>
                      <ul className="mt-2">
                        {results.data.publishers.map((item) => (
                          <li key={item.id} className="border-b border-rule/40 py-2.5">
                            <Link
                              to={`/dashboard?publisher=${item.id}`}
                              className="group flex items-center justify-between gap-2"
                            >
                              <span>
                                <span className="block font-typewriter text-[10px] uppercase tracking-[0.1em] text-ink">
                                  {item.name}
                                </span>
                                <span className="mt-0.5 block font-typewriter text-[8px] uppercase tracking-[0.08em] text-ink-soft">
                                  {item.country ?? 'Global'}
                                </span>
                              </span>
                              <ArrowUpRight size={12} className="text-ink-soft transition-colors group-hover:text-oxblood" />
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </aside>
                  )}
                </div>
              )}

              {results.data.total === 0 && (
                <div className="mt-8">
                  <EmptyEdition
                    label="Nothing in the archive"
                    title={`No dispatches for “${query}”`}
                    description="Try a broader term, a named person, a place, or a desk such as Business. The index searches event titles, summaries, keywords and extracted names."
                    action={
                      <Link to="/dashboard" className="paper-button">
                        Browse the archive
                      </Link>
                    }
                  />
                </div>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
