import { Link } from 'react-router-dom'
import { relativeTime } from '@/lib/format'
import type { EventListItem } from '@/types'

export function BreakingNewsStrip({ events }: { events: EventListItem[] }) {
  if (events.length === 0) {
    return (
      <div className="border-b border-rule/70 bg-paper-deep/30">
        <div className="container-paper flex h-9 items-center gap-4">
          <span className="bg-ink px-2 py-1 font-typewriter text-[8.5px] uppercase tracking-[0.16em] text-paper">
            The Wire
          </span>
          <span className="font-typewriter text-[9px] uppercase tracking-[0.14em] text-ink-soft">
            Awaiting the first dispatch of the edition
          </span>
        </div>
      </div>
    )
  }

  const track = [...events, ...events]

  return (
    <div className="overflow-hidden border-b border-rule/70 bg-paper-deep/35">
      <div className="container-paper flex h-9 items-center gap-3">
        <span className="shrink-0 bg-ink px-2 py-1 font-typewriter text-[8.5px] uppercase tracking-[0.16em] text-paper">
          Latest Intelligence
        </span>
        <div className="relative min-w-0 flex-1 overflow-hidden">
          <div className="ticker-track">
            {track.map((event, index) => (
              <Link
                key={`${event.code}-${index}`}
                to={`/events/${event.code}`}
                className="flex shrink-0 items-center gap-3 pr-8 transition-colors hover:text-oxblood"
                aria-hidden={index >= events.length}
              >
                <span className="whitespace-nowrap font-typewriter text-[9.5px] uppercase tracking-[0.08em] text-ink">
                  {event.title}
                </span>
                <span className="whitespace-nowrap font-typewriter text-[8.5px] uppercase tracking-[0.1em] text-ink-soft">
                  {event.publisher_count} publishers · {relativeTime(event.last_published_at)}
                </span>
                <span className="text-oxblood">◆</span>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
