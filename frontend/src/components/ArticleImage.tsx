import { useMemo, useState } from 'react'
import { enhanceImageUrl, imageHost } from '@/lib/images'
import { cn } from '@/lib/format'

type Ratio = '16/9' | '16/7' | '4/3' | '3/2' | '1/1' | '5/4'

const RATIO_CLASS: Record<Ratio, string> = {
  '16/9': 'aspect-[16/9]',
  '16/7': 'aspect-[16/7]',
  '4/3': 'aspect-[4/3]',
  '3/2': 'aspect-[3/2]',
  '1/1': 'aspect-square',
  '5/4': 'aspect-[5/4]',
}

interface ArticleImageProps {
  src?: string | null
  alt: string
  ratio?: Ratio
  priority?: boolean
  className?: string
  caption?: string | null
  credit?: string | null
  hideCaption?: boolean
  compact?: boolean
}

function hashText(value: string): number {
  let hash = 0
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) % 100000
  }
  return hash
}

function EngravingPlate({ label, seed }: { label: string; seed: number }) {
  const motif = seed % 3
  const initial = (label.trim()[0] ?? 'Y').toUpperCase()
  const ruleLines = Array.from({ length: 24 }, (_, index) => 26 + index * 18)

  return (
    <svg
      viewBox="0 0 800 500"
      className="h-full w-full bg-paper-deep text-ink"
      role="img"
      aria-label={`${label} — decorative newspaper plate`}
      preserveAspectRatio="xMidYMid slice"
    >
      <rect x="10" y="10" width="780" height="480" fill="none" stroke="currentColor" strokeWidth="2" opacity="0.7" />
      <rect x="19" y="19" width="762" height="462" fill="none" stroke="currentColor" strokeWidth="0.7" opacity="0.55" />

      <g opacity="0.18" stroke="currentColor" strokeWidth="0.6">
        {ruleLines.map((y) => (
          <line key={y} x1="26" y1={y} x2="774" y2={y} />
        ))}
      </g>

      <text
        x="400"
        y="330"
        textAnchor="middle"
        fontFamily="UnifrakturCook, serif"
        fontSize="300"
        fill="currentColor"
        opacity="0.08"
      >
        {initial}
      </text>

      <g stroke="currentColor" fill="none" opacity="0.78" strokeLinecap="round" strokeLinejoin="round">
        {motif === 0 && (
          <>
            <circle cx="400" cy="205" r="64" strokeWidth="1.4" />
            {Array.from({ length: 16 }, (_, index) => {
              const angle = (index / 16) * Math.PI * 2
              return (
                <line
                  key={index}
                  x1={400 + Math.cos(angle) * 76}
                  y1={205 + Math.sin(angle) * 76}
                  x2={400 + Math.cos(angle) * 104}
                  y2={205 + Math.sin(angle) * 104}
                  strokeWidth="0.9"
                />
              )
            })}
            <path d="M270 350 V270 h26 V350 M320 350 V250 h26 V350 M454 350 V250 h26 V350 M504 350 V270 h26 V350" strokeWidth="1.2" />
            <rect x="246" y="350" width="308" height="10" strokeWidth="1.2" />
            <path d="M246 270 h308 M270 250 h260" strokeWidth="0.8" opacity="0.7" />
          </>
        )}
        {motif === 1 && (
          <>
            <circle cx="400" cy="215" r="96" strokeWidth="1.4" />
            <ellipse cx="400" cy="215" rx="42" ry="96" strokeWidth="0.9" />
            <ellipse cx="400" cy="215" rx="78" ry="96" strokeWidth="0.7" opacity="0.7" />
            <path d="M304 215 H496 M318 168 H482 M318 262 H482" strokeWidth="0.7" opacity="0.7" />
            <path d="M330 330 h140 v24 h-140 z M362 354 v18 M438 354 v18" strokeWidth="1" />
            <path d="M250 390 H550" strokeWidth="1.2" />
          </>
        )}
        {motif === 2 && (
          <>
            <path d="M300 350 V230 Q400 140 500 230 V350" strokeWidth="1.4" />
            <path d="M330 350 V244 Q400 178 470 244 V350" strokeWidth="0.8" opacity="0.7" />
            <path d="M285 350 h230 M280 362 h240 M300 350 v-112 M500 350 v-112" strokeWidth="1" />
            <path d="M368 350 v-64 h64 v64" strokeWidth="0.9" />
            <path d="M240 394 H560 M270 406 H530 M300 418 H500" strokeWidth="0.8" opacity="0.7" />
          </>
        )}
      </g>

      <text
        x="400"
        y="446"
        textAnchor="middle"
        fontFamily="UnifrakturCook, serif"
        fontSize="25"
        fill="currentColor"
        opacity="0.78"
      >
        Your Views
      </text>
      <text
        x="400"
        y="466"
        textAnchor="middle"
        fontFamily="Special Elite, monospace"
        fontSize="7.5"
        letterSpacing="2.4"
        fill="currentColor"
        opacity="0.6"
      >
        DECORATIVE PLATE · NO PHOTOGRAPH SUPPLIED
      </text>
    </svg>
  )
}

export function ArticleImage({
  src,
  alt,
  ratio = '16/9',
  priority = false,
  className,
  caption,
  credit,
  hideCaption = false,
  compact = false,
}: ArticleImageProps) {
  const [failed, setFailed] = useState(false)
  const [loaded, setLoaded] = useState(false)
  const enhanced = useMemo(() => enhanceImageUrl(src), [src])
  const seed = useMemo(() => hashText(`${alt}-${src ?? ''}`), [alt, src])
  const showImage = Boolean(enhanced) && !failed

  return (
    <figure className={cn('group/image', className)}>
      <div className={cn('image-frame', compact && 'p-[3px]')}>
        <div className={cn('relative overflow-hidden', RATIO_CLASS[ratio])}>
          {showImage ? (
            <>
              <img
                src={enhanced}
                alt={alt}
                loading={priority ? 'eager' : 'lazy'}
                decoding="async"
                fetchPriority={priority ? 'high' : 'auto'}
                referrerPolicy="no-referrer"
                onLoad={() => setLoaded(true)}
                onError={() => setFailed(true)}
                className={cn(
                  'h-full w-full object-cover',
                  loaded ? 'animate-image-in' : 'opacity-0',
                )}
                data-newspaper-image="publisher"
              />
              {!loaded && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-paper-deep">
                  <span className="font-display text-[30px] leading-none text-ink/20">❦</span>
                  <span className="mt-2 font-typewriter text-[7.5px] uppercase tracking-[0.18em] text-ink-soft">
                    Plate in preparation
                  </span>
                </div>
              )}
            </>
          ) : (
            <EngravingPlate label={alt} seed={seed} />
          )}
          <span className="halftone" aria-hidden="true" />
        </div>
      </div>

      {!hideCaption && (
        <figcaption className="plate-caption">
          <span className="max-w-[80%]">
            {showImage
              ? caption || 'Photograph supplied by the publisher.'
              : 'Decorative plate · no photograph supplied for this dispatch.'}
          </span>
          <span className="shrink-0 text-right">
            {showImage ? credit || imageHost(enhanced) || 'The Wire' : 'Your Views Engraving Dept.'}
          </span>
        </figcaption>
      )}
    </figure>
  )
}
