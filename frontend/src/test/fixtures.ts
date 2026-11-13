import type { EventListItem, Publisher } from '@/types'

export const bbc: Publisher = {
  id: 'bbc',
  name: 'BBC News',
  short_name: 'BBC',
  country: 'GB',
  tier: 'public_service',
  accent: '#B80000',
  access: 'rss',
  homepage: 'https://www.bbc.com/news',
}

export const cnn: Publisher = {
  id: 'cnn',
  name: 'CNN',
  short_name: 'CNN',
  country: 'US',
  tier: 'commercial',
  accent: '#CC0000',
  access: 'rss',
  homepage: 'https://edition.cnn.com',
}

export const guardian: Publisher = {
  id: 'guardian',
  name: 'The Guardian',
  short_name: 'Guardian',
  country: 'GB',
  tier: 'commercial',
  accent: '#005689',
  access: 'rss',
  homepage: 'https://www.theguardian.com',
}

export const event: EventListItem = {
  id: 1,
  code: 'EVT_00001',
  title: 'Central bank raises interest rates for the third time this year',
  summary:
    'Policymakers voted to increase the benchmark rate by 25 basis points, citing persistent inflation.',
  category: 'Business',
  article_count: 5,
  publisher_count: 3,
  publishers: [bbc, cnn, guardian],
  first_published_at: '2026-11-13T06:00:00Z',
  last_published_at: '2026-11-13T09:30:00Z',
  lead_article: {
    id: 10,
    title: 'Central bank raises interest rates for the third time this year',
    url: 'https://www.bbc.co.uk/news/business-1',
    published_at: '2026-11-13T06:00:00Z',
    category: 'Business',
    image_url: null,
    publisher: bbc,
  },
  image_url: null,
  image_credit: null,
  keywords: ['interest', 'rates', 'inflation', 'bank'],
  entities: ['Bank of England', 'Andrew Bailey'],
  categories: ['Business'],
  is_single_source: false,
}
