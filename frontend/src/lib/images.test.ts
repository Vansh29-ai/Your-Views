import { describe, expect, it } from 'vitest'
import { enhanceImageUrl, imageQuality, pickBestImage } from '@/lib/images'

describe('newspaper image handling', () => {
  it('requests print-sized renditions from known CDNs', () => {
    expect(
      enhanceImageUrl('https://ichef.bbci.co.uk/ace/standard/240/cpsprodpb/x.jpg'),
    ).toBe('https://ichef.bbci.co.uk/ace/standard/976/cpsprodpb/x.jpg')

    expect(
      enhanceImageUrl('https://s.abcnews.com/images/Business/wirestory_123_4x3_384.jpg'),
    ).toBe('https://s.abcnews.com/images/Business/wirestory_123_4x3_992.jpg')
  })

  it('leaves signed Guardian renditions untouched', () => {
    const url =
      'https://i.guim.co.uk/img/media/abc/0_0_100_100/master/100.jpg?width=140&quality=85&auto=format&fit=max&s=signature'
    expect(enhanceImageUrl(url)).toBe(url)
  })

  it('prefers a high-resolution publisher over a thumbnail rendition', () => {
    const best = pickBestImage([
      { image_url: 'https://i.guim.co.uk/img/media/abc/master/100.jpg?width=140', published_at: '2026-11-13T10:00:00Z' },
      { image_url: 'https://ichef.bbci.co.uk/ace/standard/240/x.jpg', published_at: '2026-11-13T09:00:00Z' },
    ])
    expect(best?.image_url).toContain('ichef.bbci.co.uk')
    expect(imageQuality('https://ichef.bbci.co.uk/x.jpg')).toBeGreaterThan(
      imageQuality('https://i.guim.co.uk/x.jpg'),
    )
  })
})
