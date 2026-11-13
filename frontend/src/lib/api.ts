import type {
  EventDetail,
  EventListItem,
  EventQuery,
  Facets,
  Health,
  IngestionStatus,
  Overview,
  PaginatedEvents,
  PublisherDetail,
  Run,
  SearchResults,
  TimelineDay,
} from '@/types'

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? ''

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type Params = Record<string, string | number | boolean | null | undefined>

function buildUrl(path: string, params?: Params): string {
  const url = new URL(`${API_BASE}/api${path}`, window.location.origin)
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      if (value === undefined || value === null || value === '') continue
      url.searchParams.set(key, String(value))
    }
  }
  return url.pathname + url.search
}

async function request<T>(path: string, options: RequestInit & { params?: Params } = {}): Promise<T> {
  const { params, headers, ...rest } = options
  const url = buildUrl(path, params)
  let response: Response
  try {
    response = await fetch(url, {
      ...rest,
      headers: {
        Accept: 'application/json',
        ...(rest.body ? { 'Content-Type': 'application/json' } : {}),
        ...headers,
      },
    })
  } catch (error) {
    if ((error as Error).name === 'AbortError') throw error
    throw new ApiError('The API is unreachable. Is the backend running on port 8000?', 0)
  }
  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (typeof body?.detail === 'string') detail = body.detail
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, response.status)
  }
  return (await response.json()) as T
}

export const api = {
  health: () => request<Health>('/health'),
  overview: () => request<Overview>('/stats/overview'),
  timeline: (days = 14) => request<TimelineDay[]>('/stats/timeline', { params: { days } }),
  facets: () => request<Facets>('/stats/facets'),
  events: (query: EventQuery = {}) =>
    request<PaginatedEvents>('/events', { params: query as Params }),
  event: (identifier: string) => request<EventDetail>(`/events/${encodeURIComponent(identifier)}`),
  similar: (identifier: string, limit = 4) =>
    request<EventListItem[]>(`/events/${encodeURIComponent(identifier)}/similar`, {
      params: { limit },
    }),
  publishers: () => request<PublisherDetail[]>('/publishers'),
  search: (q: string, limit = 8, category?: string, publisher?: string) =>
    request<SearchResults>('/search', { params: { q, limit, category, publisher } }),
  ingestionStatus: () => request<IngestionStatus>('/admin/status'),
  triggerIngestion: () =>
    request<{ started: boolean; message: string }>('/admin/ingest', { method: 'POST' }),
  runs: (limit = 5) => request<Run[]>('/admin/runs', { params: { limit } }),
}
