import type { ReactNode } from 'react'
import { cn } from '@/lib/format'

interface EditorialSectionProps {
  title: string
  kicker?: string
  description?: string
  action?: ReactNode
  children: ReactNode
  className?: string
}

export function EditorialSection({
  title,
  kicker,
  description,
  action,
  children,
  className,
}: EditorialSectionProps) {
  return (
    <section className={cn('mt-12', className)}>
      <div className="flex flex-wrap items-end justify-between gap-3 border-b-[3px] border-double border-rule pb-1.5">
        <div className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
          <h2 className="section-title">{title}</h2>
          {kicker && <span className="kicker pb-0.5 text-[8.5px]">{kicker}</span>}
        </div>
        {action}
      </div>
      {description && (
        <p className="mt-2 max-w-2xl font-body text-[14px] italic leading-relaxed text-ink-soft">
          {description}
        </p>
      )}
      <div className="mt-5">{children}</div>
    </section>
  )
}
