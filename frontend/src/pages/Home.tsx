import { Link } from 'react-router-dom'
import { ArrowRight, ArrowUpRight } from 'lucide-react'
import { EditorialSection } from '@/components/EditorialSection'
import { EmptyEdition, ErrorNotice, StorySkeleton } from '@/components/PaperStates'
import { StoryCard } from '@/components/StoryCard'
import { useEvents, useOverview, useTimeline } from '@/hooks/queries'
import { cn, editionDate, formatDate, formatNumber, spanLabel } from '@/lib/format'
import type { EventListItem, Overview, TimelineDay } from '@/types'

function take(pool: EventListItem[], count: number, used: Set<number>): EventListItem[] {
  const picked: EventListItem[] = []
  for (const event of pool) {
    if (picked.length >= count) break
    if (used.has(event.id)) continue
    used.add(event.id)
    picked.push(event)
  }
  return picked
}

function EditionStats({ overview }: { overview?: Overview }) {
  const distribution = overview?.coverage_distribution ?? {}
  const total = Object.values(distribution).reduce((sum, value) => sum + value, 0) || 1
  const segments = [
    { key: '1', width: (distribution['1'] ?? 0) / total, tone: 'bg-ink/20' },
    { key: '2', width: (distribution['2'] ?? 0) / total, tone: 'bg-ink/40' },
    { key: '3-4', width: (distribution['3-4'] ?? 0) / total, tone: 'bg-ink/65' },
    { key: '5+', width: (distribution['5+'] ?? 0) / total, tone: 'bg-oxblood' },
  ]

  return (
    <div className="mt-8 border-y border-rule/60 py-4">
      <p className="kicker">The Edition at a Glance</p>
      <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-4">
        <div>
          <dt className="dateline">Events</dt>
          <dd className="mt-0.5 font-display text-[30px] font-extrabold leading-none tabular">
            {overview ? formatNumber(overview.events_total) : '—'}
          </dd>
        </div>
        <div>
          <dt className="dateline">Multi-Source</dt>
          <dd className="mt-0.5 font-display text-[30px] font-extrabold leading-none tabular text-oxblood">
            {overview ? formatNumber(overview.multi_source_events) : '—'}
          </dd>
        </div>
        <div>
          <dt className="dateline">Publishers</dt>
          <dd className="mt-0.5 font-display text-[30px] font-extrabold leading-none tabular">
            {overview ? `${overview.publishers_reporting}/${overview.publishers_total}` : '—'}
          </dd>
        </div>
        <div>
          <dt className="dateline">Dispatches</dt>
          <dd className="mt-0.5 font-display text-[30px] font-extrabold leading-none tabular">
            {overview ? formatNumber(overview.articles_total) : '—'}
          </dd>
        </div>
      </dl>

      <div className="mt-5">
        <div className="flex items-center justify-between">
          <span className="dateline">Source Spread</span>
          <span className="font-typewriter text-[8px] uppercase tracking-[0.1em] text-ink-soft">
            {overview ? `${overview.multi_source_events} multi-source` : ''}
          </span>
        </div>
        <div className="mt-1.5 flex h-2 w-full overflow-hidden border border-rule/40">
          {segments.map((segment) =>
            segment.width > 0 ? (
              <span
                key={segment.key}
                className={segment.tone}
                style={{ width: `${segment.width * 100}%` }}
                title={`${segment.key} publisher(s)`}
              />
            ) : null,
          )}
        </div>
        <div className="mt-1.5 flex flex-wrap gap-x-3 gap-y-1 font-typewriter text-[7.5px] uppercase tracking-[0.08em] text-ink-soft">
          <span>1 · {distribution['1'] ?? 0}</span>
          <span>2 · {distribution['2'] ?? 0}</span>
          <span>3–4 · {distribution['3-4'] ?? 0}</span>
          <span>5+ · {distribution['5+'] ?? 0}</span>
        </div>
      </div>
    </div>
  )
}

function DispatchLine({ event, index }: { event: EventListItem; index: number }) {
  return (
    <div className="flex items-baseline gap-3 border-b border-rule/40 py-2.5 last:border-0">
      <span className="index-number w-5 shrink-0">{String(index + 1).padStart(2, '0')}</span>
      <Link to={`/events/${event.code}`} className="ink-link min-w-0 flex-1 font-display text-[16px] font-bold leading-snug">
        {event.title}
      </Link>
      <span className="hidden shrink-0 font-typewriter text-[8px] uppercase tracking-[0.08em] text-ink-soft sm:block">
        {event.publisher_count}p
      </span>
    </div>
  )
}

export function Home() {
  const overview = useOverview()
  const trending = useEvents({ page_size: 24, sort: 'trending' })
  const latest = useEvents({ page_size: 8, sort: 'latest' })
  const timeline = useTimeline(14)

  const pool = trending.data?.items ?? []
  const used = new Set<number>()

  const lead = pool[0]
  if (lead) used.add(lead.id)

  const sideFeatures = take(pool, 2, used)
  const sideBriefs = take(pool, 3, used)
  const topStories = take(pool, 3, used)
  const latestDispatches = latest.data?.items ?? []

  const worldStories = take(
    pool.filter((event) => event.category === 'World'),
    4,
    used,
  )
  const picks = take(pool.filter((event) => event.publisher_count >= 2), 4, used)

  const deskOrder = ['Business', 'Technology', 'Science', 'Politics']
  const desks = deskOrder
    .map((name) => ({ name, stories: take(pool.filter((event) => event.category === name), 2, used) }))
    .filter((desk) => desk.stories.length > 0)
    .slice(0, 3)

  if (trending.isError) {
    return (
      <div className="container-paper py-12">
        <ErrorNotice
          title="The front page could not be set"
          description="The wire returned an error while assembling the edition."
          onRetry={() => trending.refetch()}
        />
      </div>
    )
  }

  return (
    <div className="container-paper pb-10 pt-6">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-rule/60 pb-2">
        <p className="kicker">The Front Page</p>
        <p className="font-typewriter text-[8.5px] uppercase tracking-[0.14em] text-ink-soft">
          {editionDate()} · {overview.data ? `${overview.data.events_last_24h} events updated in the last day` : 'Edition in preparation'}
        </p>
      </div>

      {trending.isLoading ? (
        <div className="mt-6 grid gap-8 lg:grid-cols-12">
          <div className="lg:col-span-8 lg:border-r lg:border-rule/60 lg:pr-8">
            <StorySkeleton />
          </div>
          <div className="space-y-6 lg:col-span-4">
            <StorySkeleton image={false} />
            <StorySkeleton image={false} />
          </div>
        </div>
      ) : pool.length === 0 ? (
        <div className="mt-10">
          <EmptyEdition
            title="The first edition is still at press"
            description="No events have been typeset yet. Run the presses from the archive to collect the first dispatches."
            action={<Link to="/dashboard" className="paper-button">Open the press room</Link>}
          />
        </div>
      ) : (
        <>
          {/* ------------------------------------------------ front page hero */}
          <section className="mt-6 grid gap-8 lg:grid-cols-12">
            <div className="lg:col-span-8 lg:border-r lg:border-rule/60 lg:pr-8">
              {lead && (
                <>
                  <StoryCard event={lead} variant="lead" asH1 />
                  <div className="mt-8 grid gap-4 border-t border-rule/60 pt-3 sm:grid-cols-[1.4fr_1fr_1fr]">
                    <div>
                      <p className="kicker text-[8px]">The Coverage Ledger</p>
                      <p className="mt-1 font-body text-[13px] leading-relaxed text-ink-soft">
                        Assembled from {lead.publisher_count} newsrooms and {lead.article_count}{' '}
                        reports. Open the coverage to compare every headline.
                      </p>
                    </div>
                    <div>
                      <p className="dateline">First Report</p>
                      <p className="mt-0.5 font-display text-[17px] font-bold">
                        {formatDate(lead.first_published_at)}
                      </p>
                    </div>
                    <div>
                      <p className="dateline">Coverage Span</p>
                      <p className="mt-0.5 font-display text-[17px] font-bold">
                        {spanLabel(
                          Math.max(
                            0,
                            (new Date(lead.last_published_at).getTime() -
                              new Date(lead.first_published_at).getTime()) /
                              3_600_000,
                          ),
                        )}
                      </p>
                    </div>
                  </div>

                  <div className="mt-5 border-y border-rule/50 py-4">
                    <p className="kicker text-[8px]">From the Desk</p>
                    <p className="mt-2 font-display text-[clamp(1.2rem,2.1vw,1.6rem)] italic leading-tight text-ink">
                      “{lead.publisher_count} newsrooms, one event. The value is not the consensus;
                      it is the comparison.”
                    </p>
                    <p className="mt-2 font-body text-[12.5px] leading-relaxed text-ink-soft">
                      Read every headline, then see which names each paper chose to print.
                    </p>
                  </div>

                  <div className="mt-4 border-t border-rule/40 pt-3">
                    <p className="kicker text-[8px]">Reporting From</p>
                    <p className="mt-1 font-typewriter text-[8.5px] uppercase leading-relaxed tracking-[0.1em] text-ink-soft">
                      {lead.publishers.map((publisher) => publisher.short_name).join(' · ')}
                    </p>
                    <p className="mt-2 font-body text-[11.5px] italic leading-relaxed text-ink-soft">
                      Each report was matched to this event by semantic similarity, shared names
                      and time proximity.
                    </p>
                  </div>
                </>
              )}
            </div>

            <aside className="lg:col-span-4">
              <div className="border-b-[3px] border-double border-rule pb-1">
                <h2 className="section-title">Also in This Edition</h2>
              </div>
              <div className="mt-4 space-y-5">
                {sideFeatures.map((event) => (
                  <div key={event.id} className="border-b border-rule/50 pb-5">
                    <StoryCard event={event} variant="feature" />
                  </div>
                ))}
              </div>
              <div className="mt-4">
                {sideBriefs.map((event, index) => (
                  <StoryCard key={event.id} event={event} variant="brief" index={index} />
                ))}
              </div>
              <EditionStats overview={overview.data} />
            </aside>
          </section>

          {/* ------------------------------------------------------- top stories */}
          {topStories.length > 0 && (
            <EditorialSection title="Top Stories" kicker="Chosen by the desk">
              <div className="grid gap-x-8 gap-y-8 sm:grid-cols-2 lg:grid-cols-3 lg:divide-x lg:divide-rule/50">
                {topStories.map((event, index) => (
                  <div key={event.id} className={cn(index > 0 && 'lg:pl-8')}>
                    <StoryCard event={event} variant="feature" />
                  </div>
                ))}
              </div>
            </EditorialSection>
          )}

          {/* ---------------------------------------------- world report / picks */}
          <div className="mt-4 grid gap-8 lg:grid-cols-12">
            <div className="lg:col-span-8">
              {worldStories.length > 0 && (
                <EditorialSection title="The World Report" kicker="Dispatches from abroad">
                  <div className="grid gap-x-8 gap-y-8 sm:grid-cols-2">
                    {worldStories.map((event) => (
                      <StoryCard key={event.id} event={event} variant="column" />
                    ))}
                  </div>
                </EditorialSection>
              )}
            </div>

            <aside className="lg:col-span-4 lg:border-l lg:border-rule/60 lg:pl-8">
              <div className="border-b-[3px] border-double border-rule pb-1.5">
                <h2 className="section-title">Editor's Picks</h2>
                <p className="mt-1 font-typewriter text-[8px] uppercase tracking-[0.12em] text-ink-soft">
                  Further dispatches from the desk
                </p>
              </div>
              <div className="mt-3">
                {picks.length > 0 ? (
                  picks.map((event, index) => (
                    <StoryCard key={event.id} event={event} variant="brief" index={index} />
                  ))
                ) : (
                  <p className="py-4 font-body text-[14px] italic text-ink-soft">
                    No multi-source picks in this edition yet.
                  </p>
                )}
              </div>

              <div className="mt-6 border border-rule/70 bg-paper-deep/25 p-4">
                <p className="kicker">The Editor's Note</p>
                <p className="mt-2 font-body text-[13.5px] leading-relaxed text-ink-soft">
                  Every card on this page is an event, not a single article. The archive counts the
                  publishers who covered it, not the publishers who agree with it.
                </p>
                <Link to="/about" className="underline-link mt-3">
                  Read the methodology <ArrowUpRight size={11} />
                </Link>
              </div>
            </aside>
          </div>

          {/* ------------------------------------------------------------ desks */}
          {desks.map((desk) => (
            <EditorialSection
              key={desk.name}
              title={`${desk.name} Desk`}
              kicker={`Two reports from ${desk.name.toLowerCase()}`}
              action={
                <Link to={`/dashboard?category=${desk.name}`} className="underline-link">
                  More from this desk <ArrowUpRight size={11} />
                </Link>
              }
            >
              <div className="grid gap-x-8 gap-y-8 lg:grid-cols-2">
                {desk.stories.map((event) => (
                  <StoryCard key={event.id} event={event} variant="archive" />
                ))}
              </div>
            </EditorialSection>
          ))}

          {/* ----------------------------------------------------- dispatches */}
          {latestDispatches.length > 0 && (
            <section className="mt-14 border-y border-rule/70 bg-paper-deep/25">
              <div className="container-paper py-6">
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <div>
                    <p className="kicker">Latest Dispatches</p>
                    <h2 className="section-title mt-1">Straight from the Wire</h2>
                  </div>
                  <Link to="/dashboard" className="underline-link">
                    The full archive <ArrowRight size={11} />
                  </Link>
                </div>
                <div className="mt-4 grid gap-x-10 sm:grid-cols-2">
                  {latestDispatches.slice(0, 8).map((event, index) => (
                    <DispatchLine key={event.id} event={event} index={index} />
                  ))}
                </div>
              </div>
            </section>
          )}

          {/* ------------------------------------------------------------ note */}
          <section className="mt-14 border-y-[3px] border-double border-rule py-8 text-center">
            <p className="kicker">The Comparison Desk</p>
            <h2 className="mx-auto mt-3 max-w-2xl font-display text-[clamp(1.8rem,3.4vw,2.9rem)] font-extrabold leading-[1.05]">
              One event. Six headlines. Zero guesswork.
            </h2>
            <p className="mx-auto mt-3 max-w-xl font-body text-[15px] leading-relaxed text-ink-soft">
              Open any event to read every publisher's report side by side, and see exactly which
              names and details each newsroom chose to emphasise.
            </p>
            <Link to="/dashboard" className="paper-button mt-5">
              Enter the archive <ArrowRight size={12} />
            </Link>
            {timeline.data && (
              <p className="mt-4 font-typewriter text-[8px] uppercase tracking-[0.12em] text-ink-soft">
                {timeline.data.reduce((sum, day: TimelineDay) => sum + day.events, 0)} events composed
                across the last fortnight
              </p>
            )}
          </section>
        </>
      )}
    </div>
  )
}
