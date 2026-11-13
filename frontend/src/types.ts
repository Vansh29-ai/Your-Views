export interface Publisher {
  id: string
  name: string
  short_name: string
  country: string | null
  tier: string | null
  accent: string | null
  access: string
  homepage: string
}

export interface FeedHealth {
  feed_id: string
  url: string
  category: string | null
  status: string
  http_status: number | null
  latency_ms: number | null
  last_checked_at: string | null
  last_success_at: string | null
  consecutive_failures: number
  error: string | null
  items_last_fetch: number
}

export interface PublisherDetail extends Publisher {
  feed_count: number
  enabled: boolean
  unavailable_reason: string | null
  article_count: number
  event_count: number
  last_published_at: string | null
  feeds: FeedHealth[]
}

export interface ArticleLite {
  id: number
  title: string
  url: string
  published_at: string
  category: string | null
  image_url: string | null
  publisher: Publisher
}

export interface Article extends ArticleLite {
  summary: string | null
  content: string | null
  author: string | null
  image_url: string | null
  entities: string[]
  keywords: string[]
  word_count: number
  event_id: number | null
  event_code: string | null
  match_score: number | null
  match_method: string | null
}

export interface EventListItem {
  id: number
  code: string
  title: string
  summary: string | null
  category: string | null
  article_count: number
  publisher_count: number
  publishers: Publisher[]
  first_published_at: string
  last_published_at: string
  lead_article: ArticleLite | null
  image_url: string | null
  image_credit: string | null
  keywords: string[]
  entities: string[]
  categories: string[]
  is_single_source: boolean
}

export interface TimelinePoint {
  article_id: number
  title: string
  published_at: string
  publisher: Publisher
}

export interface EmphasisPublisher {
  publisher: Publisher
  article_id: number
  headline: string
  published_at: string
  unique_entities: string[]
  shared_entities: string[]
  keywords: string[]
  word_count: number
  article_count: number
}

export interface Emphasis {
  shared_entities: string[]
  divergent_entities: string[]
  shared_keywords: string[]
  publishers: EmphasisPublisher[]
  method_note: string
}

export interface EventDetail extends EventListItem {
  articles: Article[]
  timeline: TimelinePoint[]
  emphasis: Emphasis
  stats: {
    article_count: number
    publisher_count: number
    span_hours: number
    first_published_at: string
    last_published_at: string
  }
}

export interface PaginatedEvents {
  items: EventListItem[]
  total: number
  page: number
  page_size: number
  pages: number
  sort: string
}

export interface FacetValue {
  value: string
  label: string
  count: number
}

export interface Facets {
  categories: FacetValue[]
  publishers: FacetValue[]
}

export interface SearchResults {
  query: string
  total: number
  took_ms: number
  events: EventListItem[]
  articles: ArticleLite[]
  publishers: Publisher[]
  suggestions: string[]
}

export interface Run {
  id: number
  trigger: string
  status: string
  started_at: string
  finished_at: string | null
  duration_ms: number | null
  feeds_total: number
  feeds_ok: number
  feeds_failed: number
  items_fetched: number
  items_new: number
  items_duplicate: number
  items_invalid: number
  events_created: number
  events_updated: number
  errors: { source: string; message: string }[]
}

export interface Embedder {
  model: string
  dim: number
  semantic: boolean
  backend: string
}

export interface Overview {
  events_total: number
  multi_source_events: number
  single_source_events: number
  articles_total: number
  publishers_total: number
  publishers_reporting: number
  events_last_24h: number
  articles_last_24h: number
  avg_publishers_per_event: number
  coverage_distribution: Record<string, number>
  categories: FacetValue[]
  embedder: Embedder
  latest_run: Run | null
  generated_at: string
}

export interface TimelineDay {
  date: string
  events: number
  articles: number
}

export interface Health {
  status: 'ok' | 'degraded'
  database: boolean
  fts: boolean
  embedder: Embedder
  feeds_total: number
  feeds_healthy: number
  last_run_status: string | null
  version: string
}

export interface IngestionStatus {
  running: boolean
  latest_run: Run | null
  feeds_total: number
  feeds_healthy: number
  publishers: number
  load_error: string | null
}

export type EventSort = 'latest' | 'coverage' | 'trending' | 'oldest' | 'relevance'

export interface EventQuery {
  page?: number
  page_size?: number
  category?: string
  publisher?: string
  q?: string
  sort?: EventSort
  min_publishers?: number
  window_hours?: number
  include_single?: boolean
}
