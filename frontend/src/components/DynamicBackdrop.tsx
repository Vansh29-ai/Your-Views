import { enhanceImageUrl } from '@/lib/images'

export function DynamicBackdrop({ image, label }: { image?: string | null; label?: string }) {
  const src = enhanceImageUrl(image)

  return (
    <div
      aria-hidden="true"
      data-dynamic-backdrop="true"
      data-backdrop-image={src ? 'present' : 'parchment'}
      className="pointer-events-none fixed inset-0 z-0 overflow-hidden"
    >
      {src && (
        <div
          className="absolute inset-[-3%] bg-cover bg-center opacity-[0.14] blur-[2px]"
          style={{ backgroundImage: `url("${src}")` }}
        />
      )}
      <div className="absolute inset-0 bg-gradient-to-b from-paper/60 via-paper/[0.88] to-paper" />
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            'radial-gradient(ellipse at 50% 20%, transparent 35%, rgb(var(--paper-shade) / 0.35) 100%)',
        }}
      />
      {label && (
        <span className="vertical-rl absolute right-3 top-32 hidden font-typewriter text-[8px] uppercase tracking-[0.34em] text-ink-soft/50 lg:block">
          {label}
        </span>
      )}
    </div>
  )
}
