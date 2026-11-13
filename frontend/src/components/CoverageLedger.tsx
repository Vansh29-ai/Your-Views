import { formatDateTime, relativeTime } from '@/lib/format'
import type { TimelinePoint } from '@/types'

export function CoverageLedger({ points }: { points: TimelinePoint[] }) {
  if (points.length === 0) {
    return <p className="font-body text-[13px] italic text-ink-soft">No reporting timestamps recorded.</p>
  }

  return (
    <ol className="relative ml-1 max-h-[420px] overflow-y-auto border-l border-rule/60 pr-2">
      {points.map((point, index) => (
        <li key={point.article_id} className="relative pb-5 pl-4 last:pb-0">
          <span
            className="absolute -left-[4.5px] top-1.5 h-2 w-2 rounded-full border border-paper bg-ink"
            aria-hidden="true"
          />
          <div className="flex flex-wrap items-center gap-x-2">
            <span className="font-typewriter text-[9px] uppercase tracking-[0.12em] text-ink">
              {point.publisher.short_name}
            </span>
            {index === 0 && (
              <span className="border border-rule/60 px-1 py-[1px] font-typewriter text-[7px] uppercase tracking-[0.12em] text-oxblood">
                First Report
              </span>
            )}
          </div>
          <p className="mt-1 font-body text-[13px] leading-snug text-ink-soft">{point.title}</p>
          <p className="mt-1 font-typewriter text-[8px] uppercase tracking-[0.1em] text-ink-soft/80">
            {formatDateTime(point.published_at)} · {relativeTime(point.published_at)}
          </p>
        </li>
      ))}
    </ol>
  )
}
