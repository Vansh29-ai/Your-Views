export function cn(...values: Array<string | false | null | undefined>): string {
  return values.filter(Boolean).join(' ')
}

const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' })

export function relativeTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  const diffSeconds = Math.round((date.getTime() - Date.now()) / 1000)
  const abs = Math.abs(diffSeconds)
  if (abs < 45) return 'just now'
  if (abs < 3600) return rtf.format(Math.round(diffSeconds / 60), 'minute')
  if (abs < 86400) return rtf.format(Math.round(diffSeconds / 3600), 'hour')
  if (abs < 604800) return rtf.format(Math.round(diffSeconds / 86400), 'day')
  return rtf.format(Math.round(diffSeconds / 604800), 'week')
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  }).format(new Date(iso))
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(iso))
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(iso))
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('en').format(value)
}

export function initials(name: string): string {
  const words = name.replace(/[^\w\s]/g, ' ').trim().split(/\s+/)
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase()
  return (words[0][0] + words[words.length - 1][0]).toUpperCase()
}

export function coverageLabel(count: number): string {
  if (count <= 0) return 'No coverage'
  if (count === 1) return 'Single source'
  return `${count} publishers`
}

export function spanLabel(hours: number): string {
  if (hours < 1) return 'under an hour'
  if (hours < 24) return `${Math.round(hours)}h span`
  const days = Math.round(hours / 24)
  return `${days}d span`
}

export function readingTime(words: number): string {
  const minutes = Math.max(1, Math.round(words / 220))
  return `${minutes} min read`
}

export function accentFor(index: number): string {
  const palette = ['#C8F751', '#7E9EFF', '#FFB86B', '#64E3C1', '#FF8FA3', '#B69CFF']
  return palette[index % palette.length]
}

export function editionDate(date = new Date()): string {
  return new Intl.DateTimeFormat('en-GB', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(date)
}

export function shortDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Intl.DateTimeFormat('en-GB', {
    day: 'numeric',
    month: 'short',
  }).format(new Date(iso))
}

export function coverageNames(publishers: { short_name: string }[], max = 3): string {
  const names = publishers.slice(0, max).map((publisher) => publisher.short_name)
  const remaining = publishers.length - names.length
  return remaining > 0 ? `${names.join(' · ')} +${remaining}` : names.join(' · ')
}

const ROMAN = [
  [1000, 'M'],
  [900, 'CM'],
  [500, 'D'],
  [400, 'CD'],
  [100, 'C'],
  [90, 'XC'],
  [50, 'L'],
  [40, 'XL'],
  [10, 'X'],
  [9, 'IX'],
  [5, 'V'],
  [4, 'IV'],
  [1, 'I'],
] as const

export function roman(value: number): string {
  let remaining = Math.max(1, Math.floor(value))
  let output = ''
  for (const [amount, numeral] of ROMAN) {
    while (remaining >= amount) {
      output += numeral
      remaining -= amount
    }
  }
  return output
}

export function stripMarkup(value: string | null | undefined): string {
  return (value ?? '').replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
}

export function truncateWords(value: string | null | undefined, words: number): string {
  const parts = stripMarkup(value).split(' ')
  if (parts.length <= words) return parts.join(' ')
  return `${parts.slice(0, words).join(' ')}…`
}

export function isRedundantSummary(title: string, summary: string | null | undefined): boolean {
  if (!summary) return true
  const normalise = (value: string) =>
    value.toLowerCase().replace(/[^a-z0-9 ]/g, '').replace(/\s+/g, ' ').trim()
  const a = normalise(title)
  const b = normalise(summary)
  if (!b) return true
  return a === b || (b.length < 80 && (a.includes(b) || b.includes(a)))
}


