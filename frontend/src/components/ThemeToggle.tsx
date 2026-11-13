import { Moon, Sun } from 'lucide-react'
import { useTheme } from '@/hooks/useTheme'
import { cn } from '@/lib/format'

export function ThemeToggle({ compact = false }: { compact?: boolean }) {
  const { edition, toggle } = useTheme()
  const isNight = edition === 'night'

  return (
    <button
      type="button"
      onClick={toggle}
      className={cn(
        'inline-flex items-center gap-1.5 border-b border-rule/60 pb-0.5 font-typewriter text-[8.5px] uppercase tracking-[0.14em] text-ink-soft transition-colors duration-200 hover:border-oxblood hover:text-oxblood sm:text-[9.5px]',
        compact && 'border-0 pb-0',
      )}
      aria-label={isNight ? 'Switch to day edition' : 'Switch to night edition'}
      title={isNight ? 'Day edition' : 'Night edition'}
    >
      {isNight ? <Sun size={11} strokeWidth={1.5} /> : <Moon size={11} strokeWidth={1.5} />}
      {!compact && <span>{isNight ? 'Day Edition' : 'Night Edition'}</span>}
    </button>
  )
}
