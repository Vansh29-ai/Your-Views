import { ChevronLeft, ChevronRight } from 'lucide-react'
import { roman } from '@/lib/format'

export function ArchivePagination({
  page,
  pages,
  onChange,
}: {
  page: number
  pages: number
  onChange: (page: number) => void
}) {
  if (pages <= 1) return null

  return (
    <nav className="mt-10 flex items-center justify-center gap-4 border-y border-rule/60 py-3" aria-label="Archive pages">
      <button
        type="button"
        onClick={() => onChange(page - 1)}
        disabled={page <= 1}
        className="inline-flex items-center gap-1 font-typewriter text-[9px] uppercase tracking-[0.14em] text-ink transition-colors hover:text-oxblood disabled:text-ink-soft/40"
      >
        <ChevronLeft size={12} /> Previous
      </button>
      <span className="font-typewriter text-[9px] uppercase tracking-[0.14em] text-ink-soft">
        Page {roman(page)} of {roman(pages)}
      </span>
      <button
        type="button"
        onClick={() => onChange(page + 1)}
        disabled={page >= pages}
        className="inline-flex items-center gap-1 font-typewriter text-[9px] uppercase tracking-[0.14em] text-ink transition-colors hover:text-oxblood disabled:text-ink-soft/40"
      >
        Next <ChevronRight size={12} />
      </button>
    </nav>
  )
}
