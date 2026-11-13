import { useState, type FormEvent } from 'react'
import { Search } from 'lucide-react'
import { cn } from '@/lib/format'

interface VintageSearchBarProps {
  initialValue?: string
  onSubmit: (value: string) => void
  placeholder?: string
  autoFocus?: boolean
  size?: 'hero' | 'inline'
  className?: string
  label?: string
}

export function VintageSearchBar({
  initialValue = '',
  onSubmit,
  placeholder = 'Search the archive by event, headline, publisher or keyword…',
  autoFocus = false,
  size = 'inline',
  className,
  label = 'Consult the index',
}: VintageSearchBarProps) {
  const [value, setValue] = useState(initialValue)

  function submit(event: FormEvent) {
    event.preventDefault()
    const query = value.trim()
    if (query) onSubmit(query)
  }

  return (
    <form onSubmit={submit} role="search" className={cn('w-full', className)}>
      {label && <label className="kicker block">{label}</label>}
      <div
        className={cn(
          'mt-2 flex items-end gap-2 border-b-2 border-ink pb-1 focus-within:border-oxblood sm:gap-4',
          size === 'hero' && 'mt-4',
        )}
      >
        <Search
          size={size === 'hero' ? 22 : 17}
          strokeWidth={1.4}
          className="mb-2.5 shrink-0 text-ink-soft"
          aria-hidden="true"
        />
        <input
          type="search"
          value={value}
          autoFocus={autoFocus}
          onChange={(event) => setValue(event.target.value)}
          placeholder={placeholder}
          aria-label="Search the archive"
          className={cn(
            'paper-input min-w-0 flex-1 border-0',
            size === 'hero' ? 'h-14 text-[24px] sm:text-[30px]' : 'h-10 text-[17px]',
          )}
        />
        <button type="submit" className="paper-button-solid mb-1 shrink-0">
          <span className="hidden sm:inline">Search</span>
          <span className="sm:hidden">Go</span>
        </button>
      </div>
    </form>
  )
}
