import { Link } from 'react-router-dom'
import { ArrowUpRight } from 'lucide-react'
import { useOverview } from '@/hooks/queries'

export function NewspaperFooter() {
  const { data: overview } = useOverview()

  return (
    <footer className="relative z-10 mt-20 border-t-[3px] border-double border-rule bg-paper-deep/25">
      <div className="container-paper py-10">
        <div className="flex flex-col items-center border-b border-rule/60 pb-6 text-center">
          <Link to="/" className="masthead text-[2.4rem] leading-none text-ink sm:text-[3rem]">
            YOUR VIEWS
          </Link>
          <p className="mt-2 font-typewriter text-[8.5px] uppercase tracking-[0.32em] text-ink-soft">
            Every Story · Multiple Perspectives · One Place
          </p>
        </div>

        <div className="grid gap-8 py-8 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <h2 className="kicker">This Edition</h2>
            <p className="mt-3 max-w-xs text-[13px] leading-relaxed text-ink-soft">
              An event-centric reading of the day's reporting. Coverage is grouped by the story it
              describes, not by the feed it arrived on.
            </p>
            <p className="mt-3 font-typewriter text-[9px] uppercase tracking-[0.12em] text-ink-soft">
              {overview ? `${overview.events_total} events · ${overview.articles_total} dispatches` : 'Edition in preparation'}
            </p>
          </div>

          <div>
            <h2 className="kicker">Sections</h2>
            <ul className="mt-3 space-y-2 font-serif text-[12.5px]">
              <li><Link to="/" className="ink-link">Front Page</Link></li>
              <li><Link to="/dashboard" className="ink-link">The Archive</Link></li>
              <li><Link to="/search" className="ink-link">The Index</Link></li>
              <li><Link to="/about" className="ink-link">Methodology</Link></li>
            </ul>
          </div>

          <div>
            <h2 className="kicker">The Press Room</h2>
            <ul className="mt-3 space-y-2 font-serif text-[12.5px]">
              <li>
                <a href="/api/docs" target="_blank" rel="noreferrer" className="ink-link inline-flex items-center gap-1">
                  API Reference <ArrowUpRight size={11} />
                </a>
              </li>
              <li>
                <a href="/api/health" target="_blank" rel="noreferrer" className="ink-link inline-flex items-center gap-1">
                  Wire Health <ArrowUpRight size={11} />
                </a>
              </li>
              <li><Link to="/about#sources" className="ink-link">Publisher Registry</Link></li>
              <li><Link to="/about#limits" className="ink-link">Known Limits</Link></li>
            </ul>
          </div>

          <div>
            <h2 className="kicker">Rights &amp; Attribution</h2>
            <p className="mt-3 text-[12px] leading-relaxed text-ink-soft">
              Headlines, summaries and publisher-supplied images only. Full reports remain the
              property of their publishers and open on the original sites. Decorative plates are
              original illustrations, not photographs.
            </p>
          </div>
        </div>

        <div className="flex flex-col gap-3 border-t border-rule/60 pt-5 text-center font-typewriter text-[8.5px] uppercase tracking-[0.12em] text-ink-soft sm:flex-row sm:items-center sm:justify-between sm:text-left">
          <p>© {new Date().getFullYear()} Your Views · Vol. I · Printed digitally from the wire</p>
          <p>Set in UnifrakturCook, Playfair Display, IM Fell English &amp; Special Elite</p>
        </div>
      </div>
    </footer>
  )
}
