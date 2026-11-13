import type { ReactNode } from 'react'
import { AlertTriangle, Inbox, RotateCcw } from 'lucide-react'
import { cn } from '@/lib/format'

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn('animate-pulse border border-rule/40 bg-paper-deep/40', className)} aria-hidden="true" />
}

export function StorySkeleton({ image = true }: { image?: boolean }) {
  return (
    <div className="space-y-3">
      {image && <Skeleton className="aspect-[3/2] w-full" />}
      <Skeleton className="h-2.5 w-24" />
      <Skeleton className="h-6 w-11/12" />
      <Skeleton className="h-6 w-2/3" />
      <Skeleton className="h-2.5 w-full" />
      <Skeleton className="h-2.5 w-4/5" />
    </div>
  )
}

export function EditionSkeleton({ stories = 6 }: { stories?: number }) {
  return (
    <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: stories }).map((_, index) => (
        <StorySkeleton key={index} />
      ))}
    </div>
  )
}

export function LoadingRule({ label = 'Setting the type…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-4 py-10" role="status" aria-live="polite">
      <span className="h-px flex-1 bg-rule/50" />
      <span className="font-typewriter text-[9px] uppercase tracking-[0.2em] text-ink-soft">
        {label}
      </span>
      <span className="h-px flex-1 bg-rule/50" />
    </div>
  )
}

export function EmptyEdition({
  title,
  description,
  action,
  label = 'The archive is silent',
}: {
  title: string
  description: string
  action?: ReactNode
  label?: string
}) {
  return (
    <div className="border border-rule/70 bg-paper-deep/25 px-6 py-14 text-center">
      <div className="divider-ornament mx-auto max-w-xs">
        <span className="text-[13px] text-oxblood">❦</span>
      </div>
      <p className="kicker">{label}</p>
      <h3 className="mt-3 font-display text-[clamp(1.5rem,2.4vw,2rem)] font-extrabold text-ink">
        {title}
      </h3>
      <p className="mx-auto mt-3 max-w-md font-body text-[15px] leading-relaxed text-ink-soft">
        {description}
      </p>
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  )
}

export function ErrorNotice({
  title = 'The presses have stalled',
  description,
  onRetry,
}: {
  title?: string
  description?: string
  onRetry?: () => void
}) {
  return (
    <div className="border border-rule/70 bg-paper-deep/25 px-6 py-12 text-center">
      <div className="mx-auto flex h-10 w-10 items-center justify-center border border-rule text-oxblood">
        <AlertTriangle size={18} strokeWidth={1.4} />
      </div>
      <h3 className="mt-4 font-display text-2xl font-extrabold text-ink">{title}</h3>
      <p className="mx-auto mt-2 max-w-md font-body text-[14.5px] leading-relaxed text-ink-soft">
        {description ?? 'The edition could not be retrieved. Check the wire and try again.'}
      </p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="paper-button mt-6">
          <RotateCcw size={12} /> Try the wire again
        </button>
      )}
    </div>
  )
}

export function EmptyColumn({ label, description }: { label: string; description: string }) {
  return (
    <div className="border border-dashed border-rule/60 px-4 py-8 text-center">
      <Inbox size={16} className="mx-auto text-ink-soft" strokeWidth={1.3} />
      <p className="mt-2 font-typewriter text-[9px] uppercase tracking-[0.14em] text-ink-soft">{label}</p>
      <p className="mx-auto mt-1 max-w-xs font-body text-[13px] text-ink-soft">{description}</p>
    </div>
  )
}
