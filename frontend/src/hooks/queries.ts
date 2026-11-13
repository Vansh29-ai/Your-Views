import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import type { EventQuery } from '@/types'

export const queryKeys = {
  overview: ['overview'] as const,
  timeline: (days: number) => ['timeline', days] as const,
  facets: ['facets'] as const,
  events: (query: EventQuery) => ['events', query] as const,
  event: (id: string) => ['event', id] as const,
  similar: (id: string) => ['event', id, 'similar'] as const,
  publishers: ['publishers'] as const,
  search: (q: string, category?: string, publisher?: string) =>
    ['search', q, category ?? '', publisher ?? ''] as const,
  ingestion: ['ingestion'] as const,
  health: ['health'] as const,
}

export function useOverview() {
  return useQuery({
    queryKey: queryKeys.overview,
    queryFn: api.overview,
    staleTime: 60_000,
  })
}

export function useTimeline(days = 14) {
  return useQuery({
    queryKey: queryKeys.timeline(days),
    queryFn: () => api.timeline(days),
    staleTime: 120_000,
  })
}

export function useFacets() {
  return useQuery({
    queryKey: queryKeys.facets,
    queryFn: api.facets,
    staleTime: 120_000,
  })
}

export function useEvents(query: EventQuery) {
  return useQuery({
    queryKey: queryKeys.events(query),
    queryFn: () => api.events(query),
    placeholderData: keepPreviousData,
    staleTime: 30_000,
  })
}

export function useEvent(identifier: string) {
  return useQuery({
    queryKey: queryKeys.event(identifier),
    queryFn: () => api.event(identifier),
    retry: false,
    staleTime: 60_000,
  })
}

export function useSimilarEvents(identifier: string) {
  return useQuery({
    queryKey: queryKeys.similar(identifier),
    queryFn: () => api.similar(identifier),
    retry: false,
    staleTime: 120_000,
  })
}

export function usePublishers() {
  return useQuery({
    queryKey: queryKeys.publishers,
    queryFn: api.publishers,
    staleTime: 120_000,
  })
}

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: api.health,
    staleTime: 60_000,
    retry: false,
  })
}

export function useSearch(q: string, category?: string, publisher?: string) {
  return useQuery({
    queryKey: queryKeys.search(q, category, publisher),
    queryFn: () => api.search(q, 8, category, publisher),
    enabled: q.trim().length >= 2,
    staleTime: 30_000,
  })
}

export function useIngestionStatus() {
  const query = useQuery({
    queryKey: queryKeys.ingestion,
    queryFn: api.ingestionStatus,
    refetchInterval: (state) => (state.state.data?.running ? 4000 : false),
    staleTime: 5_000,
  })
  return query
}

export function useTriggerIngestion() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.triggerIngestion,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.ingestion })
    },
  })
}

export function useRefreshAll() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries()
}
