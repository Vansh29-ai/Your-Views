import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import { ArticleImage } from '@/components/ArticleImage'
import { cn, coverageNames, formatDate, isRedundantSummary, relativeTime } from '@/lib/format'
import type { EventListItem } from '@/types'

type Variant = 'lead' | 'feature' | 'column' | 'brief' | 'archive' | 'compact'

interface StoryCardProps {
  event: EventListItem
  variant?: Variant
  index?: number
  className?: string
  showImage?: boolean
  asH1?: boolean
}

function StoryMeta({ event, className }: { event: EventListItem; className?: string }) {
  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-x-2 gap-y-1 font-typewriter text-[8.5px] uppercase tracking-[0.13em] text-ink-soft',
        className,
      )}
    >
      <span className="text-oxblood">{event.category ?? 'World'}</span>
      <span aria-hidden="true">Â·</span>
      <span>{relativeTime(event.last_published_at)}</span>
      <span aria-hidden="true">Â·</span>
      <span>
        {event.publisher_count} {event.publisher_count === 1 ? 'publisher' : 'publishers'}
      </span>
    </div>
  )
}

function CoverageLine({ event }: { event: EventListItem }) {
  return (
    <span className="byline">
      Reported by {coverageNames(event.publishers, 3)}
    </span>
  )
}

export function StoryCard({
  event,
  variant = 'column',
  index = 0,
  className,
  showImage = true,
  asH1 = false,
}: StoryCardProps) {
  const href = `/events/${event.code}`
  const image = event.image_url ?? event.lead_article?.image_url ?? null
  const credit = event.image_credit ?? event.lead_article?.publisher.name ?? null
  const LeadHeading = asH1 ? 'h1' : 'h2'
  const summary =
    event.summary && !isRedundantSummary(event.title, event.summary) ? event.summary : null

  if (variant === 'compact') {
    return (
      <article className={cn('group border-b border-rule/45 py-3.5 last:border-0', className)}>
        <StoryMeta event={event} />
        <h3 className="mt-1.5 font-display text-[17px] font-bold leading-[1.15]">
          <Link to={href} className="ink-link">
            {event.title}
          </Link>
        </h3>
      </article>
    )
  }

  if (variant === 'brief') {
    return (
      <article className={cn('group index-row items-start', className)}>
        <span className="index-number mt-1 w-6 shrink-0">{String(index + 1).padStart(2, '0')}</span>
        <div className="min-w-0 flex-1">
          <h3 className="font-display text-[18px] font-bold leading-[1.18]">
            <Link to={href} className="ink-link">
              {event.title}
            </Link>
          </h3>
          <StoryMeta event={event} className="mt-1.5" />
        </div>
        <ArrowUpRight
          size={14}
          className="mt-1.5 shrink-0 text-ink-soft transition-transform duration-300 group-hover:-translate-y-0.5 group-hover:text-oxblood"
          aria-hidden="true"
        />
      </article>
    )
  }

  if (variant === 'archive') {
    return (
      <article className={cn('group grid gap-4 border-b border-rule/60 py-5 first:pt-0 sm:grid-cols-[210px_1fr]', className)}>
        {showImage && (
          <Link to={href} aria-label={event.title}>
            <ArticleImage
              src={image}
              alt={event.title}
              ratio="4/3"
              credit={credit}
              hideCaption
              compact
            />
          </Link>
        )}
        <div className="min-w-0">
          <StoryMeta event={event} />
          <h3 className="mt-2 font-display text-[clamp(1.3rem,1.9vw,1.75rem)] font-extrabold leading-[1.08]">
            <Link to={href} className="ink-link">
              {event.title}
            </Link>
          </h3>
          {summary && (
            <p className="mt-2 line-clamp-2 font-body text-[14.5px] leading-relaxed text-ink-soft">
              {summary}
            </p>
          )}
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-rule/40 pt-2">
            <CoverageLine event={event} />
            <Link to={href} className="underline-link">
              Full coverage <ArrowUpRight size={11} />
            </Link>
          </div>
        </div>
      </article>
    )
  }

  if (variant === 'lead') {
    return (
      <article className={cn('group', className)}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <StoryMeta event={event} />
          {event.publisher_count > 1 && (
            <span className="font-typewriter text-[8.5px] uppercase tracking-[0.16em] text-oxblood">
              Multi-Source Dispatch
            </span>
          )}
        </div>

        <LeadHeading className="mt-3 text-lead headline">
          <Link to={href} className="ink-link">
            {event.title}
          </Link>
        </LeadHeading>

        {summary && (
          <p className="mt-4 line-clamp-3 font-body text-[20px] leading-[1.45] text-ink-soft">
            {summary}
          </p>
        )}        {showImage && (
          <Link to={href} className="mt-6 block" aria-label={event.title} tabIndex={-1}>
            <ArticleImage
              src={image}
              alt={event.title}
              ratio="16/9"
              priority
              credit={credit}
              caption={`${event.category ?? 'World'} Â· ${formatDate(event.first_published_at)}`}
            />
          </Link>
        )}

        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-rule/60 pt-2.5">
          <CoverageLine event={event} />
          <span className="byline">{formatDate(event.first_published_at)}</span>
        </div>

        <Link to={href} className="underline-link mt-4">
          Read the full coverage <ArrowUpRight size={12} />
        </Link>
      </article>
    )
  }

  if (variant === 'feature') {
    return (
      <article className={cn('group', className)}>
        {showImage && (
          <Link to={href} className="block" aria-label={event.title} tabIndex={-1}>
            <ArticleImage src={image} alt={event.title} ratio="3/2" credit={credit} hideCaption compact />
          </Link>
        )}
        <div className={cn(showImage && 'mt-3')}>
          <StoryMeta event={event} />
          <h3 className="mt-2 font-display text-[clamp(1.45rem,2.2vw,2rem)] font-extrabold leading-[1.05]">
            <Link to={href} className="ink-link">
              {event.title}
            </Link>
          </h3>
          {summary && (
            <p className="mt-2 line-clamp-2 font-body text-[14.5px] leading-relaxed text-ink-soft">
              {summary}
            </p>
          )}
        </div>
      </article>
    )
  }

  return (
    <article className={cn('group', className)}>
      {showImage && (
        <Link to={href} className="block" aria-label={event.title} tabIndex={-1}>
          <ArticleImage src={image} alt={event.title} ratio="3/2" credit={credit} hideCaption compact />
        </Link>
      )}
      <div className={cn(showImage && 'mt-3')}>
        <StoryMeta event={event} />
        <h3 className="mt-2 font-display text-[clamp(1.25rem,1.7vw,1.55rem)] font-extrabold leading-[1.1]">
          <Link to={href} className="ink-link">
            {event.title}
          </Link>
        </h3>
        {summary && (
          <p className="mt-2 line-clamp-3 font-body text-[14px] leading-relaxed text-ink-soft">
            {summary}
          </p>
        )}
        <div className="mt-3">
          <CoverageLine event={event} />
        </div>
      </div>
    </article>
  )
}

