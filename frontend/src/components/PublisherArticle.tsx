import { ArrowUpRight } from 'lucide-react'
import { ArticleImage } from '@/components/ArticleImage'
import { cn, formatDateTime, isRedundantSummary, readingTime } from '@/lib/format'
import type { Article } from '@/types'

interface PublisherArticleProps {
  article: Article
  selected: boolean
  onToggle: (article: Article) => void
}

export function PublisherArticle({ article, selected, onToggle }: PublisherArticleProps) {
  const summary =
    article.summary && !isRedundantSummary(article.title, article.summary) ? article.summary : null

  return (
    <article
      className={cn(
        'border-t border-rule/60 pt-4 transition-colors duration-200',
        selected && 'bg-paper-deep/20',
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-typewriter text-[10px] uppercase tracking-[0.16em] text-oxblood">
            {article.publisher.name}
          </p>
          <p className="mt-1 font-typewriter text-[8px] uppercase tracking-[0.1em] text-ink-soft">
            {formatDateTime(article.published_at)} Â· {article.publisher.country ?? 'Global'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => onToggle(article)}
          aria-pressed={selected}
          aria-label={selected ? `Remove ${article.publisher.short_name} from comparison` : `Add ${article.publisher.short_name} to comparison`}
          className={cn('paper-check shrink-0 pt-0.5', selected && 'paper-check-active text-ink')}
        >
          <span className="paper-check-box">{selected && 'Ã—'}</span>
          <span className="hidden sm:inline">{selected ? 'Selected' : 'Compare'}</span>
        </button>
      </div>

      {article.image_url && (
        <div className="mt-3">
          <ArticleImage
            src={article.image_url}
            alt={article.title}
            ratio="16/9"
            credit={article.publisher.name}
            hideCaption
            compact
          />
        </div>
      )}

      <h3 className="mt-3 font-display text-[clamp(1.3rem,2vw,1.7rem)] font-extrabold leading-[1.08] text-ink">
        {article.title}
      </h3>

      {summary && (
        <p className="mt-2 line-clamp-4 font-body text-[14.5px] leading-relaxed text-ink-soft">
          {summary}
        </p>
      )}

      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-rule/40 pt-2">
        <span className="font-typewriter text-[8px] uppercase tracking-[0.1em] text-ink-soft">
          {article.word_count} words Â· {readingTime(article.word_count)}
        </span>
        <a
          href={article.url}
          target="_blank"
          rel="noreferrer noopener"
          className="underline-link"
        >
          Read the original report <ArrowUpRight size={11} />
        </a>
      </div>
    </article>
  )
}

