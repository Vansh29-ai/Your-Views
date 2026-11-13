import { useEffect } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { BreakingNewsStrip } from '@/components/BreakingNewsStrip'
import { NewspaperFooter } from '@/components/NewspaperFooter'
import { NewspaperMasthead } from '@/components/NewspaperMasthead'
import { useEvents } from '@/hooks/queries'

export function AppShell() {
  const location = useLocation()
  const isFront = location.pathname === '/'
  const { data: latest } = useEvents({ page_size: 8, sort: 'latest' })

  useEffect(() => {
    window.scrollTo(0, 0)
  }, [location.pathname])

  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:border focus:border-ink focus:bg-paper focus:px-4 focus:py-2 focus:font-typewriter focus:text-[10px] focus:uppercase focus:tracking-widest focus:text-ink"
      >
        Skip to the edition
      </a>

      <div className="paper-texture" aria-hidden="true" />
      <div className="vignette" aria-hidden="true" />

      <NewspaperMasthead variant={isFront ? 'front' : 'inner'} />
      {isFront && <BreakingNewsStrip events={latest?.items ?? []} />}

      <main id="main" className="relative z-10 flex-1">
        <div key={location.pathname} className="page-enter">
          <Outlet />
        </div>
      </main>

      <NewspaperFooter />
    </div>
  )
}
