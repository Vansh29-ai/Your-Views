import { describe, expect, it } from 'vitest'
import { coverageLabel, initials, relativeTime, spanLabel } from '@/lib/format'

describe('format helpers', () => {
  it('formats coverage labels without overclaiming', () => {
    expect(coverageLabel(0)).toBe('No coverage')
    expect(coverageLabel(1)).toBe('Single source')
    expect(coverageLabel(6)).toBe('6 publishers')
  })

  it('derives publisher initials', () => {
    expect(initials('BBC News')).toBe('BN')
    expect(initials('CNN')).toBe('CN')
    expect(initials('The Guardian')).toBe('TG')
  })

  it('labels coverage spans', () => {
    expect(spanLabel(0.4)).toBe('under an hour')
    expect(spanLabel(7)).toBe('7h span')
    expect(spanLabel(48)).toBe('2d span')
  })

  it('renders relative timestamps', () => {
    expect(relativeTime(new Date().toISOString())).toBe('just now')
    expect(relativeTime(null)).toBe('—')
  })
})
