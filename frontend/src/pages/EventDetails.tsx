import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, ArrowUpRight, Check, ChevronRight, Share2 } from 'lucide-react'
import { ArticleImage } from '@/components/ArticleImage'
import { ComparisonSpread } from '@/components/ComparisonSpread'
import { CoverageLedger } from '@/components/CoverageLedger'
import { DynamicBackdrop } from '@/components/DynamicBackdrop'
import { EmphasisTable } from '@/components/EmphasisTable'
import { ErrorNotice } from '@/components/PaperStates'
import { PublisherArticle } from '@/components/PublisherArticle'
import { StoryCard } from '@/components/StoryCard'
import { useEvent, useSimilarEvents } from '@/hooks/queries'
import { formatDate, formatDateTime, relativeTime, spanLabel } from '@/lib/format'
import type { Article } from '@/types'

const MAX_COMPARE = 4

export function EventDetails() {
  const { code = '' } = useParams()
  const { data, isLoading, isError, error, refetch } = useEvent(code)
  const similar = useSimilarEvents(code)
  const [selected, setSelected] = useState<number[]>([])
  const [visibleCount, setVisibleCount] = useState(10)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    setSelected([])
    setVisibleCount(10)
  }, [code])

  const selectedArticles = useMemo(
    () => (data?.articles ?? []).filter((article) => selected.includes(article.id)),
    [data, selected],
  )

  function toggle(article: Article) {
    setSelected((current) => {
      if (current.includes(article.id)) return current.filter((id) => id !== article.id)
      if (current.length >= MAX_COMPARE) return current
      return [...current, article.id]
    })
  }

  async function share() {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2200)
    } catch {
      setCopied(false)
    }
  }

  if (isLoading) {
    return (
      <div className="container-paper py-12">
        <div className="space-y-4">
          <div className="h-2 w-40 animate-pulse bg-paper-deep" />
          <div className="h-14 w-4/5 animate-pulse bg-paper-deep" />
          <div className="h-14 w-3/5 animate-pulse bg-paper-deep" />
          <div className="h-4 w-3/4 animate-pulse bg-paper-deep" />
        </div>
        <div className="mt-8 aspect-[16/7] w-full animate-pulse border border-rule/40 bg-paper-deep/60" />
      </div>
    )
  }

  if (isError || !data) {
    const status = (error as { status?: number } | null)?.status
    return (
      <div className="container-paper py-16">
        {status === 404 ? (
          <div className="mx-auto max-w-xl border-y-[3px] border-double border-rule py-12 text-center">
            <p className="kicker">Not in this edition</p>
            <h1 className="mt-3 font-display text-4xl font-extrabold">This dispatch does not exist</h1>
            <p className="mt-3 font-body text-[15px] leading-relaxed text-ink-soft">
              The event code <span className="font-typewriter text-ink">{code}</span> is no longer in
              the archive. It may have been re-typeset after a re-clustering.
            </p>
            <Link to="/dashboard" className="paper-button mt-6">
              <ArrowLeft size={12} /> Return to the archive
            </Link>
          </div>
        ) : (
          <ErrorNotice
            title="This page failed to come off the press"
            description="The wire returned an error while assembling the coverage."
            onRetry={() => refetch()}
          />
        )}
      </div>
    )
  }

  const heroImage = data.image_url ?? data.articles.find((article) => article.image_url)?.image_url ?? null
  const credit = data.image_credit ?? data.lead_article?.publisher.name ?? null

  return (
    <div className="relative">
      <DynamicBackdrop image={heroImage} label={`${data.category ?? 'World'} · ${data.code}`} />

      <div className="container-paper relative z-10 pb-20 pt-5">
        <nav className="flex items-center gap-1.5 font-typewriter text-[8px] uppercase tracking-[0.14em] text-ink-soft" aria-label="Breadcrumb">
          <Link to="/" className="hover:text-oxblood">Front Page</Link>
          <ChevronRight size={9} />
          <Link to="/dashboard" className="hover:text-oxblood">The Archive</Link>
          <ChevronRight size={9} />
          <span className="text-ink">{data.code}</span>
        </nav>

        <header className="mt-5 border-b border-rule/60 pb-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <p className="kicker">The World Report · {data.category ?? 'World'}</p>
            <p className="font-typewriter text-[8px] uppercase tracking-[0.14em] text-ink-soft">
              Filed {formatDate(data.first_published_at)} · Updated {relativeTime(data.last_published_at)}
            </p>
          </div>

          <h1 className="mt-4 max-w-5xl text-lead headline">{data.title}</h1>

          {data.summary && (
            <p className="mt-4 max-w-3xl font-body text-[clamp(1.1rem,1.6vw,1.35rem)] leading-[1.5] text-ink-soft">
              {data.summary}
            </p>
          )}

          <div className="mt-5 flex flex-wrap items-center justify-between gap-x-6 gap-y-3">
            <p className="font-typewriter text-[8.5px] uppercase tracking-[0.12em] text-ink-soft">
              Reported by {data.publishers.map((publisher) => publisher.short_name).join(' · ')}
            </p>
            <div className="flex items-center gap-4">
              <button type="button" onClick={share} className="underline-link">
                {copied ? <Check size={11} /> : <Share2 size={11} />}
                {copied ? 'Link copied' : 'Share this page'}
              </button>
              {data.lead_article && (
                <a
                  href={data.lead_article.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="underline-link"
                >
                  Lead report <ArrowUpRight size={11} />
                </a>
              )}
            </div>
          </div>
        </header>

        <div className="mt-6">
          <ArticleImage
            src={heroImage}
            alt={data.title}
            ratio="16/7"
            priority
            credit={credit}
            caption={`${data.category ?? 'World'} · ${data.publisher_count} publishers · ${data.article_count} reports`}
          />
        </div>

        <dl className="mt-5 grid grid-cols-2 gap-y-3 border-y border-rule/60 py-4 sm:grid-cols-4">
          <div>
            <dt className="dateline">Publishers</dt>
            <dd className="mt-0.5 font-display text-[22px] font-extrabold leading-none tabular">
              {data.stats.publisher_count}
            </dd>
          </div>
          <div>
            <dt className="dateline">Reports</dt>
            <dd className="mt-0.5 font-display text-[22px] font-extrabold leading-none tabular">
              {data.stats.article_count}
            </dd>
          </div>
          <div>
            <dt className="dateline">Coverage Span</dt>
            <dd className="mt-0.5 font-display text-[22px] font-extrabold leading-none">
              {spanLabel(data.stats.span_hours)}
            </dd>
          </div>
          <div>
            <dt className="dateline">First Report</dt>
            <dd className="mt-0.5 font-display text-[18px] font-extrabold leading-none">
              {formatDateTime(data.stats.first_published_at)}
            </dd>
          </div>
        </dl>

        <div className="mt-8 grid gap-10 lg:grid-cols-12">
          <div className="lg:col-span-8">
            <div className="border-b-[3px] border-double border-rule pb-1.5">
              <p className="kicker">The Coverage</p>
              <h2 className="section-title mt-1">Reports from the Newsrooms</h2>
            </div>
            <p className="mt-2 max-w-2xl font-body text-[14px] italic leading-relaxed text-ink-soft">
              Select up to {MAX_COMPARE} reports to compare how each publication told this story.
            </p>

            <div className="mt-6 grid gap-x-8 gap-y-8 sm:grid-cols-2">
              {data.articles.slice(0, visibleCount).map((article) => (
                <PublisherArticle
                  key={article.id}
                  article={article}
                  selected={selected.includes(article.id)}
                  onToggle={toggle}
                />
              ))}
            </div>

            {visibleCount < data.articles.length && (
              <div className="mt-6 border-t border-rule/50 pt-4 text-center">
                <button
                  type="button"
                  className="paper-button"
                  onClick={() => setVisibleCount((count) => count + 10)}
                >
                  Reveal {Math.min(10, data.articles.length - visibleCount)} more reports
                </button>
                <p className="mt-2 font-typewriter text-[8px] uppercase tracking-[0.12em] text-ink-soft">
                  {data.articles.length - visibleCount} reports remain in the archive
                </p>
              </div>
            )}

            {selectedArticles.length >= 2 && (
              <ComparisonSpread articles={selectedArticles} onClear={() => setSelected([])} />
            )}

            <EmphasisTable emphasis={data.emphasis} />
          </div>

          <aside className="lg:sticky lg:top-4 lg:col-span-4 lg:self-start lg:border-l lg:border-rule/60 lg:pl-7">
            <section>
              <div className="border-b-[3px] border-double border-rule pb-1">
                <p className="kicker">The Ledger</p>
                <h2 className="section-title mt-1 text-[22px]">Who Reported When</h2>
              </div>
              <div className="mt-4">
                <CoverageLedger points={data.timeline} />
              </div>
            </section>

            <section className="mt-8 border-t border-rule/60 pt-4">
              <p className="kicker">At a Glance</p>
              <ul className="mt-2 space-y-1.5 font-body text-[13.5px] text-ink-soft">
                <li className="flex justify-between gap-3 border-b border-rule/30 pb-1.5">
                  <span>Publishers covering</span>
                  <span className="font-typewriter text-[10px] text-ink">{data.publisher_count}</span>
                </li>
                <li className="flex justify-between gap-3 border-b border-rule/30 pb-1.5">
                  <span>Reports in archive</span>
                  <span className="font-typewriter text-[10px] text-ink">{data.article_count}</span>
                </li>
                <li className="flex justify-between gap-3 border-b border-rule/30 pb-1.5">
                  <span>Shared names</span>
                  <span className="font-typewriter text-[10px] text-ink">{data.emphasis.shared_entities.length}</span>
                </li>
                <li className="flex justify-between gap-3">
                  <span>Named only once</span>
                  <span className="font-typewriter text-[10px] text-ink">{data.emphasis.divergent_entities.length}</span>
                </li>
              </ul>
              <p className="mt-3 font-body text-[12px] leading-relaxed text-ink-soft">
                Event membership is decided by the semantic matching engine. It is probabilistic,
                not editorial.
              </p>
            </section>

            {(similar.data?.length ?? 0) > 0 && (
              <section className="mt-8 border-t border-rule/60 pt-4">
                <p className="kicker">Related Dispatches</p>
                <div className="mt-2">
                  {similar.data?.slice(0, 4).map((event) => (
                    <StoryCard key={event.id} event={event} variant="compact" />
                  ))}
                </div>
              </section>
            )}

            <p className="mt-8 border-t border-rule/60 pt-3 font-body text-[11.5px] italic leading-relaxed text-ink-soft">
              Headlines and summaries remain the property of their publishers. Full reports open on
              the original sites.
            </p>
          </aside>
        </div>
      </div>

      {selectedArticles.length > 0 && (
        <div className="fixed bottom-4 left-1/2 z-40 w-[calc(100%-2rem)] max-w-2xl -translate-x-1/2">
          <div className="flex items-center justify-between gap-3 border border-ink bg-paper px-4 py-2.5">
            <p className="font-typewriter text-[8.5px] uppercase tracking-[0.12em] text-ink">
              {selectedArticles.length} report{selectedArticles.length === 1 ? '' : 's'} selected
              {selectedArticles.length < 2 && ' · choose one more'}
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => setSelected([])}
                className="font-typewriter text-[8px] uppercase tracking-[0.1em] text-ink-soft underline-offset-2 hover:text-oxblood hover:underline"
              >
                Clear
              </button>
              <button
                type="button"
                disabled={selectedArticles.length < 2}
                onClick={() => document.getElementById('comparison')?.scrollIntoView({ behavior: 'smooth', block: 'start' })}
                className="paper-button-solid disabled:opacity-40"
              >
                Compare
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
