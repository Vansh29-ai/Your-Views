import type { Emphasis } from '@/types'

export function EmphasisTable({ emphasis }: { emphasis: Emphasis }) {
  const entityKeys = new Set(emphasis.shared_entities.map((entity) => entity.toLowerCase()))
  const sharedKeywords = emphasis.shared_keywords.filter(
    (keyword) => !entityKeys.has(keyword.toLowerCase()),
  )

  return (
    <section className="mt-14">
      <div className="border-b-[3px] border-double border-rule pb-1.5">
        <p className="kicker">Framing Signals</p>
        <h2 className="section-title mt-1">What Each Paper Emphasised</h2>
      </div>
      <p className="mt-3 max-w-3xl font-body text-[14.5px] leading-relaxed text-ink-soft">
        The same event, as told by each newsroom. These are lexical and entity signals — what each
        publisher chose to name — not a measure of truth, bias or sentiment.
      </p>

      <div className="mt-6 grid gap-6 border-y border-rule/60 py-5 md:grid-cols-3">
        <div>
          <p className="kicker text-[8px]">Shared Frame</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {emphasis.shared_entities.length === 0 && sharedKeywords.length === 0 && (
              <span className="font-body text-[13px] italic text-ink-soft">No shared names detected.</span>
            )}
            {emphasis.shared_entities.map((entity) => (
              <span key={entity} className="border border-ink/50 px-1.5 py-0.5 font-typewriter text-[8.5px] uppercase tracking-[0.06em] text-ink">
                {entity}
              </span>
            ))}
            {sharedKeywords.map((keyword) => (
              <span key={keyword} className="border border-rule/60 px-1.5 py-0.5 font-typewriter text-[8.5px] uppercase tracking-[0.06em] text-ink-soft">
                {keyword}
              </span>
            ))}
          </div>
        </div>

        <div>
          <p className="kicker text-[8px]">Singular Details</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {emphasis.divergent_entities.length === 0 && (
              <span className="font-body text-[13px] italic text-ink-soft">No divergent names detected.</span>
            )}
            {emphasis.divergent_entities.slice(0, 12).map((entity) => (
              <span key={entity} className="border border-rule/50 px-1.5 py-0.5 font-typewriter text-[8.5px] uppercase tracking-[0.06em] text-ink-soft">
                {entity}
              </span>
            ))}
          </div>
        </div>

        <div>
          <p className="kicker text-[8px]">How to Read This</p>
          <p className="mt-2 font-body text-[13px] leading-relaxed text-ink-soft">{emphasis.method_note}</p>
        </div>
      </div>

      <div className="mt-5">
        <div className="hidden grid-cols-[1.2fr_2fr_1.6fr] gap-5 border-b border-rule pb-2 font-typewriter text-[8px] uppercase tracking-[0.14em] text-ink-soft md:grid">
          <span>Publication</span>
          <span>Latest Headline</span>
          <span>Names Unique to This Paper</span>
        </div>
        {emphasis.publishers.map((row) => (
          <div
            key={row.article_id}
            className="grid gap-2 border-b border-rule/40 py-3 md:grid-cols-[1.2fr_2fr_1.6fr] md:items-start md:gap-5"
          >
            <div>
              <p className="font-typewriter text-[9.5px] uppercase tracking-[0.12em] text-ink">
                {row.publisher.name}
              </p>
              <p className="mt-0.5 font-typewriter text-[8px] uppercase tracking-[0.08em] text-ink-soft">
                {row.article_count} report{row.article_count === 1 ? '' : 's'} · {row.word_count} words
              </p>
            </div>
            <p className="font-body text-[13.5px] leading-snug text-ink-soft">{row.headline}</p>
            <div className="flex flex-wrap gap-x-2 gap-y-1">
              {row.unique_entities.length === 0 ? (
                <span className="font-body text-[12px] italic text-ink-soft/70">—</span>
              ) : (
                row.unique_entities.slice(0, 5).map((entity) => (
                  <span key={entity} className="font-typewriter text-[8.5px] uppercase tracking-[0.04em] text-ink">
                    · {entity}
                  </span>
                ))
              )}
            </div>
          </div>
        ))}
      </div>
    </section>
  )
}
