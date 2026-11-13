import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { StoryCard } from '@/components/StoryCard'
import { event } from '@/test/fixtures'

describe('StoryCard', () => {
  it('sets an event as a printable newspaper story linked to its coverage page', () => {
    render(
      <MemoryRouter>
        <StoryCard event={event} variant="column" />
      </MemoryRouter>,
    )

    const links = screen.getAllByRole('link')
    expect(links[0]).toHaveAttribute('href', '/events/EVT_00001')
    expect(screen.getByText(event.title)).toBeInTheDocument()
    expect(screen.getByText(/3 publishers/i)).toBeInTheDocument()
  })

  it('falls back to a decorative engraving when no publisher photograph exists', () => {
    render(
      <MemoryRouter>
        <StoryCard event={event} variant="feature" />
      </MemoryRouter>,
    )

    expect(
      screen.getByRole('img', { name: /decorative newspaper plate/i }),
    ).toBeInTheDocument()
  })

  it('renders the lead treatment with a coverage line', () => {
    render(
      <MemoryRouter>
        <StoryCard event={event} variant="lead" />
      </MemoryRouter>,
    )

    expect(screen.getByText(/reported by bbc/i)).toBeInTheDocument()
    expect(screen.getByText(/read the full coverage/i)).toBeInTheDocument()
  })
})
