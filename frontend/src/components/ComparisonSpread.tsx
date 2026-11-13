import { ArrowUpRight, X } from 'lucide-react'
import { cn } from '@/lib/format'
import type { Article } from '@/types'

export function ComparisonSpread({ articles, onClear }: { articles: Article[]; onClear: () => void }) {
  if (articles.length === 0) return null

  const entitySets = articles.map((article) => new Set(article.entities.map((entity) => entity.toLowerCase())))
  const keywordSets = articles.map((article) => new Set(article.keywords.map((keyword) => keyword.toLowerCase())))
  const sharedEntities = articles[0].entities.filter((entity) =>
    entitySets.every((set) => set.has(entity.toLowerCase())),
  )
  const sharedKeywords = articles[0].keywords.filter(
    (keyword) =>
      keywordSets.every((set) => set.has(keyword.toLowerCase())) &&
      !sharedEntities.some((entity) => entity.toLowerCase() === keyword.toLowerCase()),
  )

  const gridClass =
    articles.length === 4
      ? 'md:grid-cols-2 xl:grid-cols-4'
      : articles.length === 3
        ? 'md:grid-cols-3'
        : 'md:grid-cols-2'

  return (
    <section id="comparison" className="mt-14 scroll-mt-10">
      <div className="flex flex-wrap items-end justify-between gap-3 border-b-[3px] border-double border-rule pb-1.5">
        <div>
          <p className="kicker">The Comparison Desk</p>
          <h2 className="section-title mt-1">Compare the Coverage</h2>
        </div>
        <button type="button" onClick={onClear} className="underline-link">
          <X size={11} /> Clear the comparison
        </button>
      </div>

      {(sharedEntities.length > 0 || sharedKeywords.length > 0) && (
        <div className="mt-4 flex flex-wrap items-center gap-x-3 gap-y-2 border-b border-rule/50 pb-3">
          <span className="font-typewriter text-[8px] uppercase tracking-[0.14em] text-ink-soft">
            All reports agree on
          </span>
          {sharedEntities.slice(0, 8).map((entity) => (
            <span
              key={entity}
              className="border border-ink/50 px-1.5 py-0.5 font-typewriter text-[8.5px] uppercase tracking-[0.08em] text-ink"
            >
              {entity}
            </span>
          ))}
          {sharedKeywords.slice(0, 5).map((keyword) => (
            <span
              key={keyword}
              className="border border-rule/60 px-1.5 py-0.5 font-typewriter text-[8.5px] uppercase tracking-[0.08em] text-ink-soft"
            >
              {keyword}
            </span>
          ))}
        </div>
      )}

      <div className={cn('mt-5 grid gap-y-8 md:divide-x md:divide-rule/50', gridClass)}>
        {articles.map((article, index) => {
          const unique = article.entities.filter(
            (entity) => !sharedEntities.some((shared) => shared.toLowerCase() === entity.toLowerCase()),
          )
          return (
            <article key={article.id} className={cn('md:px-5', index === 0 && 'md:pl-0', index === articles.length - 1 && 'md:pr-0')}>
              <div className="flex items-start justify-between gap-2">
                <div>
                  <p className="font-typewriter text-[10px] uppercase tracking-[0.16em] text-oxblood">
                    {article.publisher.name}
                  </p>
                  <p className="mt-1 font-typewriter text-[8px] uppercase tracking-[0.1em] text-ink-soft">
                    {article.publisher.country ?? 'Global'}
                  </p>
                </div>
                <a
                  href={article.url}
                  target="_blank"
                  rel="noreferrer noopener"
                  className="text-ink-soft transition-colors hover:text-oxblood"
                  aria-label={`Open ${article.publisher.name} report`}
                >
                  <ArrowUpRight size={14} />
                </a>
              </div>

              <h3 className="mt-3 font-display text-[clamp(1.25rem,1.8vw,1.55rem)] font-extrabold leading-[1.1] text-ink">
                {article.title}
              </h3>

              <p className="mt-2 font-body text-[14px] leading-relaxed text-ink-soft">
                {article.summary || 'No summary was supplied with this dispatch.'}
              </p>

              {unique.length > 0 && (
                <div className="mt-4 border-t border-rule/40 pt-3">
                  <p className="kicker text-[8px]">Mentioned only here</p>
                  <ul className="mt-2 space-y-1">
                    {unique.slice(0, 5).map((entity) => (
                      <li key={entity} className="font-typewriter text-[9px] uppercase tracking-[0.06em] text-ink">
                        · {entity}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </article>
          )
        })}
      </div>

      <p className="mt-5 border-t border-rule/40 pt-2 font-body text-[12px] italic leading-relaxed text-ink-soft">
        Inclusion in this event means the reports were semantically matched. It does not imply the
        accounts agree, nor that any single account is complete. Original reporting remains with
        the publisher.
      </p>
    </section>
  )
}
