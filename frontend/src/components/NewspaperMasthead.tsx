import { useEffect, useState } from 'react'
import { Link, NavLink, useLocation } from 'react-router-dom'
import { Search } from 'lucide-react'
import { ThemeToggle } from '@/components/ThemeToggle'
import { useHealth, useOverview } from '@/hooks/queries'
import { cn, editionDate } from '@/lib/format'

const DESKS = [
  { label: 'Front Page', to: '/' },
  { label: 'The Archive', to: '/dashboard' },
  { label: 'World', to: '/dashboard?category=World' },
  { label: 'Politics', to: '/dashboard?category=Politics' },
  { label: 'Business', to: '/dashboard?category=Business' },
  { label: 'Technology', to: '/dashboard?category=Technology' },
  { label: 'Science', to: '/dashboard?category=Science' },
  { label: 'The Index', to: '/search' },
  { label: 'Methodology', to: '/about' },
]

function Navigation() {
  const location = useLocation()
  const activeCategory = new URLSearchParams(location.search).get('category')

  return (
    <nav className="border-y border-rule/70 bg-paper-deep/20" aria-label="Newspaper sections">
      <div className="container-paper">
        <div className="nav-strip py-0">
          {DESKS.map((link) => {
            const [path, query] = link.to.split('?')
            const category = query ? new URLSearchParams(query).get('category') : null
            const isActive =
              category !== null
                ? location.pathname === path && activeCategory === category
                : location.pathname === link.to
            return (
              <Link
                key={link.to}
                to={link.to}
                className={cn('nav-link', isActive && 'nav-link-active')}
                aria-current={isActive ? 'page' : undefined}
              >
                {link.label}
              </Link>
            )
          })}
          <NavLink
            to="/search"
            className={({ isActive }) =>
              cn('nav-link inline-flex items-center gap-1.5 sm:ml-auto', isActive && 'nav-link-active')
            }
          >
            <Search size={11} strokeWidth={1.6} /> Index &amp; Search
          </NavLink>
        </div>
      </div>
    </nav>
  )
}

function MastheadWordmark({ small = false }: { small?: boolean }) {
  return (
    <Link to="/" className="inline-block text-center" aria-label="YOUR VIEWS front page">
      <span
        className={cn(
          'masthead block text-ink transition-colors duration-300 hover:text-oxblood',
          small ? 'text-[clamp(2rem,4.5vw,3.1rem)] leading-none' : 'text-masthead',
        )}
      >
        YOUR VIEWS
      </span>
      {!small && (
        <span className="mt-5 block font-typewriter text-[8px] uppercase leading-[1.6] tracking-[0.3em] text-ink-soft sm:mt-4 sm:text-[9.5px]">
          Every Story · Multiple Perspectives · One Place
        </span>
      )}
    </Link>
  )
}

export function NewspaperMasthead({ variant = 'inner' }: { variant?: 'front' | 'inner' }) {
  const { data: overview } = useOverview()
  const { data: health } = useHealth()
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 60_000)
    return () => window.clearInterval(timer)
  }, [])

  const issue = overview ? String(overview.events_total).padStart(3, '0') : '—'
  const feeds = health ? `${health.feeds_healthy}/${health.feeds_total} feeds` : 'wire pending'
  const live = health?.status === 'ok'

  return (
    <header className="relative z-30">
      <div className="border-b border-rule/60 bg-paper-deep/20">
        <div className="container-paper flex h-8 items-center justify-between gap-3 font-typewriter text-[8.5px] uppercase tracking-[0.14em] text-ink-soft sm:text-[9.5px]">
          <span>Vol. I · No. {issue}</span>
          <span className="hidden md:inline">The Daily Edition · Independent, Event-Centric Coverage</span>
          <span className="text-right">{editionDate(now)}</span>
        </div>
      </div>

      {variant === 'front' ? (
        <>
          <div className="container-paper pb-4 pt-7 text-center sm:pb-6 sm:pt-10">
            <MastheadWordmark />
            <div className="mx-auto mt-6 flex max-w-4xl items-center gap-4">
              <span className="h-px flex-1 bg-rule/80" />
              <span className="kicker whitespace-nowrap text-[8.5px] sm:text-[10px]">
                The World, Reported in Full
              </span>
              <span className="h-px flex-1 bg-rule/80" />
            </div>
          </div>

          <div className="container-paper">
            <div className="rule-double flex flex-wrap items-center justify-between gap-3 py-2">
              <p className="font-typewriter text-[8.5px] uppercase tracking-[0.14em] text-ink-soft sm:text-[9.5px]">
                Est. MMXXVI · {overview ? `${overview.articles_total} dispatches` : 'Dispatches pending'}
              </p>
              <div className="flex items-center gap-4">
                <span className="flex items-center gap-1.5 font-typewriter text-[8.5px] uppercase tracking-[0.14em] text-ink-soft sm:text-[9.5px]">
                  <span className={cn('h-1.5 w-1.5 rounded-full', live ? 'bg-oxblood' : 'bg-rule')} />
                  {feeds}
                </span>
                <ThemeToggle />
              </div>
            </div>
          </div>
          <Navigation />
        </>
      ) : (
        <>
          <div className="container-paper flex items-end justify-between gap-4 py-4 sm:py-5">
            <MastheadWordmark small />
            <div className="flex items-center gap-4">
              <div className="hidden text-right sm:block">
                <p className="dateline">The Daily Edition</p>
                <p className="mt-1 font-typewriter text-[9px] uppercase tracking-[0.12em] text-ink-soft">
                  No. {issue} · {feeds}
                </p>
              </div>
              <div className="hidden sm:block">
                <ThemeToggle />
              </div>
              <div className="sm:hidden">
                <ThemeToggle compact />
              </div>
            </div>
          </div>
          <Navigation />
        </>
      )}
    </header>
  )
}

export { MastheadWordmark }
