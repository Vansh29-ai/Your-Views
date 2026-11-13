export function enhanceImageUrl(url: string | null | undefined): string {
  if (!url) return ''
  if (isPlaceholderImage(url)) return ''
  if (url.includes('ichef.bbci.co.uk')) {
    return url
      .replace('/standard/240/', '/standard/976/')
      .replace('/images/ic/240x135/', '/images/ic/976x549/')
  }
  if (url.includes('s.abcnews.com')) {
    return url.replace(/_(4x3|16x9)_\d+(\.(jpg|jpeg|png|webp))/i, '_$1_992$2')
  }
  if (url.includes('s.france24.com')) {
    return url.replace(/w:\d+/, 'w:1024')
  }
  if (url.startsWith('http://')) {
    return url.replace('http://', 'https://')
  }
  return url
}

export function isPlaceholderImage(url: string | null | undefined): boolean {
  if (!url) return false
  return /abc_news_default|placeholder|no[-_]?image|fallback[-_]?image|default[-_]?social/i.test(url)
}

export function imageQuality(url: string | null | undefined): number {
  if (!url) return 0
  if (isPlaceholderImage(url)) return 0
  if (
    url.includes('ichef.bbci.co.uk') ||
    url.includes('abcnews') ||
    url.includes('thgim.com') ||
    url.includes('france24.com') ||
    url.includes('cnn.com')
  ) {
    return 3
  }
  if (url.includes('guim.co.uk')) return 1
  return 2
}

export function pickBestImage<T extends { image_url?: string | null; published_at?: string }>(
  articles: T[],
): T | undefined {
  const candidates = articles.filter((article) => Boolean(article.image_url))
  if (candidates.length === 0) return undefined
  return candidates.sort((left, right) => {
    const quality = imageQuality(right.image_url) - imageQuality(left.image_url)
    if (quality !== 0) return quality
    return (right.published_at ?? '').localeCompare(left.published_at ?? '')
  })[0]
}

export function imageHost(url: string | null | undefined): string {
  if (!url) return ''
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}
