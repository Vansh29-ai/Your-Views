import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { AlertCircle, CheckCircle2, RefreshCw } from 'lucide-react'
import { useIngestionStatus, useTriggerIngestion } from '@/hooks/queries'
import { cn, formatNumber, relativeTime } from '@/lib/format'
import type { Overview, TimelineDay } from '@/types'

function Sparkline({ data }: { data: TimelineDay[] }) {
  const values = data.map((day) => day.events)
  const max = Math.max(1, ...values)
  const width = 150
  const height = 34
  const step = values.length > 1 ? width / (values.length - 1) : width
  const points = values
    .map((value, index) => `${(index * step).toFixed(1)},${(height - (value / max) * (height - 4) - 2).toFixed(1)}`)
    .join(' ')

  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="h-8 w-[150px] text-ink" role="img" aria-label="Events per day, last fourteen days">
      <line x1="0" y1={height - 1} x2={width} y2={height - 1} stroke="currentColor" strokeWidth="0.6" opacity="0.35" />
      <polyline points={points} fill="none" stroke="currentColor" strokeWidth="1.2" />
    </svg>
  )
}

export function PressRoom({ overview, timeline }: { overview?: Overview; timeline?: TimelineDay[] }) {
  const { data, isError } = useIngestionStatus()
  const trigger = useTriggerIngestion()
  const queryClient = useQueryClient()
  const [notice, setNotice] = useState<string | null>(null)
  const wasRunning = useRef(false)
  const run = data?.latest_run

  useEffect(() => {
    if (!data) return
    if (wasRunning.current && !data.running) {
      setNotice('The presses have run. A new edition is on the stands.')
      queryClient.invalidateQueries()
      const timer = window.setTimeout(() => setNotice(null), 7000)
      return () => window.clearTimeout(timer)
    }
    wasRunning.current = data.running
  }, [data, queryClient])

  async function runPresses() {
    setNotice(null)
    try {
      const result = await trigger.mutateAsync()
      setNotice(result.started ? 'The presses are running…' : result.message)
    } catch (error) {
      setNotice((error as Error).message)
    }
  }

  return (
    <section className="mt-8 border-y border-rule/70 bg-paper-deep/30">
      <div className="container-paper py-4">
        <div className="grid gap-4 md:flex md:flex-wrap md:items-center md:justify-between md:gap-x-8">
          <div className="min-w-0">
            <p className="kicker">The Press Room</p>
            <h2 className="mt-1 font-display text-[22px] font-extrabold leading-none text-ink">
              {isError ? 'Wire disconnected' : data?.running ? 'Presses running' : 'The wire is quiet'}
            </h2>
            <p className="mt-1.5 font-typewriter text-[8.5px] uppercase tracking-[0.12em] text-ink-soft">
              {data ? `${data.feeds_healthy}/${data.feeds_total} feeds live · ${data.publishers} sources` : 'Checking the wire…'}
            </p>
          </div>

          <dl className="grid w-full grid-cols-2 gap-x-6 gap-y-2 sm:grid-cols-4 md:w-auto md:flex-1">
            <div>
              <dt className="dateline">Last Run</dt>
              <dd className="mt-0.5 font-display text-[19px] font-bold leading-none">
                {run ? relativeTime(run.started_at) : '—'}
              </dd>
            </div>
            <div>
              <dt className="dateline">New Dispatches</dt>
              <dd className="mt-0.5 font-display text-[19px] font-bold leading-none">
                {run ? formatNumber(run.items_new) : '—'}
              </dd>
            </div>
            <div>
              <dt className="dateline">Events in Archive</dt>
              <dd className="mt-0.5 font-display text-[19px] font-bold leading-none">
                {overview ? formatNumber(overview.events_total) : '—'}
              </dd>
            </div>
            <div>
              <dt className="dateline">Fourteen Days</dt>
              <dd className="mt-0.5">
                <Sparkline data={timeline ?? []} />
              </dd>
            </div>
          </dl>

          <div className="flex flex-col items-start gap-1.5">
            <button
              type="button"
              onClick={runPresses}
              disabled={trigger.isPending || Boolean(data?.running)}
              className="paper-button-solid"
            >
              <RefreshCw size={12} className={cn((trigger.isPending || data?.running) && 'animate-spin')} />
              {data?.running ? 'Presses Running' : 'Run the Presses'}
            </button>
            <span className="font-typewriter text-[8px] uppercase tracking-[0.12em] text-ink-soft">
              Scheduled every 30 minutes
            </span>
          </div>
        </div>

        {(notice || (run?.errors && run.errors.length > 0)) && (
          <div className="mt-3 flex flex-wrap items-center gap-x-6 gap-y-1 border-t border-rule/40 pt-2">
            {notice && (
              <span className="flex items-center gap-1.5 font-typewriter text-[8.5px] uppercase tracking-[0.1em] text-ink-soft">
                <CheckCircle2 size={11} className="text-oxblood" /> {notice}
              </span>
            )}
            {run?.errors && run.errors.length > 0 && (
              <span className="flex items-center gap-1.5 font-typewriter text-[8.5px] uppercase tracking-[0.1em] text-ink-soft">
                <AlertCircle size={11} className="text-oxblood" />
                {run.errors.length} feed{run.errors.length === 1 ? '' : 's'} reported difficulties on the last run
              </span>
            )}
          </div>
        )}
      </div>
    </section>
  )
}
