import { Link } from 'react-router-dom'
import { ArrowRight, CheckCircle2, XCircle } from 'lucide-react'
import { useOverview, usePublishers } from '@/hooks/queries'
import { formatNumber, relativeTime } from '@/lib/format'

const PIPELINE = [
  {
    numeral: 'I',
    title: 'Collect',
    body: 'Each registered publisher is fetched over HTTP with conditional requests and per-feed health. Failures stay with the feed that caused them; the edition keeps printing.',
  },
  {
    numeral: 'II',
    title: 'Clean',
    body: 'Markup, boilerplate and tracking parameters are removed. Timestamps are normalised to UTC and implausible items are rejected before they reach the archive.',
  },
  {
    numeral: 'III',
    title: 'Deduplicate',
    body: 'Canonical URLs, exact fingerprints and 64-bit SimHash catch repeats within a publication. Cross-publisher similarity is deliberately preserved: it is the story.',
  },
  {
    numeral: 'IV',
    title: 'Embed',
    body: 'Headline and summary are encoded with all-MiniLM-L6-v2 into a 384-dimensional vector, stored once and reused for every later comparison.',
  },
  {
    numeral: 'V',
    title: 'Match',
    body: 'Cosine similarity to event centroids is weighed with shared entities, shared keywords and time proximity. Weaker similarity needs corroboration; conflicting names raise the bar.',
  },
  {
    numeral: 'VI',
    title: 'Assemble',
    body: 'An event keeps its centroid, publisher roll, names, first and last timestamps, and a lead report. Aggregates are recomputed whenever the coverage changes.',
  },
]

const LIMITS = [
  {
    title: 'No bias score',
    body: 'Entity and keyword overlap describe what was mentioned. They do not measure framing quality, sentiment or factual accuracy, and no such score is presented.',
  },
  {
    title: 'Matching is probabilistic',
    body: 'Language models miss irony, metaphor and context. False merges and missed merges are possible; thresholds are configurable and the archive can be re-typeset.',
  },
  {
    title: 'Summaries belong to publishers',
    body: 'This edition does not write new summaries. It prints the publisher summary attached to the lead report; length and quality vary by newsroom.',
  },
  {
    title: 'RSS is a window',
    body: 'Feeds usually expose only recent items and truncated descriptions. The archive never claims to hold a publisher\'s complete output.',
  },
]

function hostname(url: string): string {
  if (!url) return '—'
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url.replace(/^https?:\/\//, '').replace(/\/.*$/, '')
  }
}

export function About() {
  const overview = useOverview()
  const publishers = usePublishers()
  const embedder = overview.data?.embedder
  const latestRun = overview.data?.latest_run

  return (
    <div className="container-paper pb-10 pt-6">
      <header className="grid gap-8 border-b-[3px] border-double border-rule pb-8 pt-4 lg:grid-cols-12">
        <div className="lg:col-span-8">
          <p className="kicker">About This Edition</p>
          <h1 className="mt-3 max-w-3xl font-display text-[clamp(2.4rem,5vw,4.2rem)] font-extrabold leading-[0.95] tracking-[-0.02em] text-ink">
            News is event-shaped. Most news products are article-shaped.
          </h1>
          <p className="mt-4 max-w-2xl font-body text-[17px] leading-[1.65] text-ink-soft">
            Your Views is a daily edition organised around real-world events rather than feeds. It
            collects reporting from multiple publishers, decides which reports describe the same
            occurrence, and prints the coverage side by side.
          </p>
        </div>

        <aside className="lg:col-span-4 lg:border-l lg:border-rule/60 lg:pl-7">
          <p className="kicker">The Edition Desk</p>
          <dl className="mt-3 space-y-2.5">
            <div className="flex justify-between gap-3 border-b border-rule/40 pb-2">
              <dt className="dateline">Events</dt>
              <dd className="font-display text-[20px] font-extrabold leading-none tabular">
                {formatNumber(overview.data?.events_total ?? 0)}
              </dd>
            </div>
            <div className="flex justify-between gap-3 border-b border-rule/40 pb-2">
              <dt className="dateline">Dispatches</dt>
              <dd className="font-display text-[20px] font-extrabold leading-none tabular">
                {formatNumber(overview.data?.articles_total ?? 0)}
              </dd>
            </div>
            <div className="flex justify-between gap-3 border-b border-rule/40 pb-2">
              <dt className="dateline">Multi-Source</dt>
              <dd className="font-display text-[20px] font-extrabold leading-none tabular text-oxblood">
                {formatNumber(overview.data?.multi_source_events ?? 0)}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="dateline">Last Press Run</dt>
              <dd className="font-typewriter text-[9px] uppercase tracking-[0.08em] text-ink">
                {latestRun ? relativeTime(latestRun.started_at) : 'Not yet'}
              </dd>
            </div>
          </dl>
        </aside>
      </header>

      <section className="grid gap-8 border-b border-rule/60 py-8 md:grid-cols-3 md:divide-x md:divide-rule/50">
        {[
          ['The Problem', 'Fragmented by design', 'The same event arrives as six headlines, six ledes and six sets of sources. Comparing them means holding six versions in your head.'],
          ['The Approach', 'Cluster the event, not the topic', 'Two articles about elections are not necessarily about the same election. Matching weighs names and time, not just wording.'],
          ['The Boundary', 'Compare, do not adjudicate', 'The edition shows what each publisher mentions and links to the original. Judgement stays with the reader.'],
        ].map(([kicker, title, body], index) => (
          <div key={title} className={index > 0 ? 'md:pl-8' : ''}>
            <p className="kicker">{kicker}</p>
            <h2 className="mt-2 font-display text-[24px] font-extrabold leading-tight text-ink">{title}</h2>
            <p className="mt-2 font-body text-[14px] leading-relaxed text-ink-soft">{body}</p>
          </div>
        ))}
      </section>

      <section className="mt-12">
        <div className="border-b-[3px] border-double border-rule pb-1.5">
          <p className="kicker">The Method</p>
          <h2 className="section-title mt-1">How an Article Becomes an Event</h2>
        </div>

        <div className="mt-5 grid gap-8 lg:grid-cols-12">
          <div className="lg:col-span-5">
            <p className="dropcap body-copy">
              Every morning the wire delivers more reporting than any reader can hold. The edition
              begins by asking a narrower question than a search engine would: not “what mentions
              this topic?” but “which reports describe the same occurrence?” That distinction is the
              whole product. Topic similarity is cheap. Event identity is not.
            </p>
            <p className="mt-4 body-copy">
              Reports are embedded, compared against existing event centroids, and admitted only
              when the evidence is strong — or medium-strength but corroborated by specific names.
              When two reports carry substantive but disjoint casts of characters, the threshold
              rises. Two different elections stay two events.
            </p>
            <blockquote className="pull-quote mt-6">
              “Two articles about elections are not necessarily about the same election.”
            </blockquote>
          </div>

          <div className="lg:col-span-7">
            <div className="grid gap-x-8 gap-y-5 sm:grid-cols-2">
              {PIPELINE.map((stage) => (
                <div key={stage.numeral} className="border-t border-rule/50 pt-3">
                  <div className="flex items-baseline gap-2">
                    <span className="font-typewriter text-[10px] uppercase tracking-[0.12em] text-oxblood">
                      {stage.numeral}
                    </span>
                    <h3 className="font-display text-[20px] font-extrabold leading-none">{stage.title}</h3>
                  </div>
                  <p className="mt-2 font-body text-[13px] leading-relaxed text-ink-soft">{stage.body}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      <section className="mt-14 grid gap-8 lg:grid-cols-12">
        <div className="lg:col-span-7">
          <div className="border-b-[3px] border-double border-rule pb-1.5">
            <p className="kicker">Matching, Concretely</p>
            <h2 className="section-title mt-1">Thresholds &amp; Signals</h2>
          </div>
          <ul className="mt-4 space-y-3">
            {[
              ['Strong semantic match', 'Cosine similarity of 0.70 or more to the event centroid.'],
              ['Corroborated match', 'Similarity of 0.58 or more, plus two shared named entities and keyword overlap (or one entity with stronger overlap).'],
              ['Conflict guard', 'If both reports carry two or more substantive names and share none, the strong threshold rises by 0.08 and corroboration is refused.'],
              ['Time window', 'New reports are compared against events from the last 96 hours; batch clustering splits groups that span more than 72 hours.'],
            ].map(([title, body]) => (
              <li key={title} className="flex gap-3 border-b border-rule/40 pb-3 last:border-0">
                <CheckCircle2 size={14} className="mt-1 shrink-0 text-oxblood" />
                <p className="font-body text-[13.5px] leading-relaxed text-ink-soft">
                  <span className="font-semibold text-ink">{title}.</span> {body}
                </p>
              </li>
            ))}
          </ul>
        </div>

        <div className="lg:col-span-5 lg:border-l lg:border-rule/60 lg:pl-7">
          <p className="kicker">Running in This Edition</p>
          <dl className="mt-3 space-y-3 font-body text-[13px]">
            <div>
              <dt className="dateline">Embedding Model</dt>
              <dd className="mt-0.5 break-all text-ink">{embedder?.model ?? '—'}</dd>
            </div>
            <div>
              <dt className="dateline">Backend</dt>
              <dd className="mt-0.5 text-ink">
                {embedder?.backend ?? '—'} · {embedder?.dim ?? '—'} dimensions
              </dd>
              {embedder && !embedder.semantic && (
                <p className="mt-1 font-body text-[11.5px] italic text-oxblood">
                  Lexical fallback active — install the sentence-transformer model for full semantic matching.
                </p>
              )}
            </div>
            <div>
              <dt className="dateline">Search Index</dt>
              <dd className="mt-0.5 text-ink">SQLite FTS5 · bm25 ranking</dd>
            </div>
            <div>
              <dt className="dateline">Storage</dt>
              <dd className="mt-0.5 text-ink">SQLAlchemy · event centroids stored as 384-d vectors</dd>
            </div>
          </dl>
          <a href="/api/docs" target="_blank" rel="noreferrer" className="underline-link mt-4">
            Inspect the API <ArrowRight size={11} />
          </a>
        </div>
      </section>

      <section id="sources" className="mt-16 scroll-mt-8">
        <div className="border-b-[3px] border-double border-rule pb-1.5">
          <p className="kicker">The Publisher Registry</p>
          <h2 className="section-title mt-1">Where the Coverage Comes From</h2>
        </div>
        <p className="mt-2 max-w-2xl font-body text-[14px] italic text-ink-soft">
          One JSON registry. A source is added by adding an entry — no pipeline changes.
        </p>

        <div className="mt-4 overflow-hidden border border-rule/70">
          <div className="hidden grid-cols-[1.5fr_0.6fr_0.8fr_0.9fr_0.6fr] gap-3 border-b border-rule bg-paper-deep/50 px-4 py-2 font-typewriter text-[8px] uppercase tracking-[0.12em] text-ink-soft md:grid">
            <span>Publication</span>
            <span>Country</span>
            <span>Access</span>
            <span>Feeds</span>
            <span className="text-right">Reports</span>
          </div>
          {(publishers.data ?? []).map((publisher) => {
            const healthy = publisher.feeds.filter((feed) => feed.status === 'ok').length
            const unavailable = !publisher.enabled || publisher.feed_count === 0
            return (
              <div key={publisher.id} className="border-b border-rule/40 last:border-0">
                <div className="grid gap-1 px-4 py-3 md:grid-cols-[1.5fr_0.6fr_0.8fr_0.9fr_0.6fr] md:items-center md:gap-3">
                  <div>
                    <p className="font-display text-[16px] font-bold leading-tight text-ink">{publisher.name}</p>
                    <a
                      href={publisher.homepage || '#'}
                      target="_blank"
                      rel="noreferrer"
                      className="font-typewriter text-[8px] uppercase tracking-[0.1em] text-ink-soft hover:text-oxblood"
                    >
                      {hostname(publisher.homepage)}
                    </a>
                  </div>
                  <p className="font-typewriter text-[9px] uppercase tracking-[0.1em] text-ink-soft">
                    {publisher.country ?? '—'}
                  </p>
                  <p className="font-typewriter text-[9px] uppercase tracking-[0.1em] text-ink-soft">
                    {publisher.access.replace('_', ' ')}
                  </p>
                  <p className="flex items-center gap-1.5 font-typewriter text-[9px] uppercase tracking-[0.08em] text-ink-soft">
                    {unavailable ? (
                      <>
                        <XCircle size={10} className="text-oxblood" /> unavailable
                      </>
                    ) : (
                      <>
                        <CheckCircle2 size={10} className="text-oxblood" /> {healthy}/{publisher.feed_count} live
                      </>
                    )}
                  </p>
                  <p className="text-right font-typewriter text-[10px] tabular text-ink">
                    {formatNumber(publisher.article_count)}
                  </p>
                </div>
                {publisher.unavailable_reason && (
                  <p className="border-t border-rule/30 px-4 py-2 font-body text-[11.5px] italic leading-relaxed text-ink-soft">
                    {publisher.unavailable_reason}
                  </p>
                )}
              </div>
            )
          })}
        </div>
        <p className="mt-2 font-body text-[11.5px] italic leading-relaxed text-ink-soft">
          Reuters retired public RSS; machine access requires a licensed API subscription, so the
          source is registered but inactive rather than scraped. All other publications expose
          public feeds.
        </p>
      </section>

      <section id="limits" className="mt-16 scroll-mt-8">
        <div className="border-b-[3px] border-double border-rule pb-1.5">
          <p className="kicker">Honest Limits</p>
          <h2 className="section-title mt-1">What This Edition Does Not Do</h2>
        </div>
        <div className="mt-4 grid gap-x-8 gap-y-5 sm:grid-cols-2">
          {LIMITS.map((limit) => (
            <div key={limit.title} className="border-t border-rule/50 pt-3">
              <h3 className="font-display text-[19px] font-extrabold text-ink">{limit.title}</h3>
              <p className="mt-1.5 font-body text-[13px] leading-relaxed text-ink-soft">{limit.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-14 border-y-[3px] border-double border-rule py-8">
        <div className="flex flex-wrap items-center justify-between gap-6">
          <div className="max-w-xl">
            <p className="kicker">Colophon</p>
            <h2 className="mt-2 font-display text-[clamp(1.6rem,2.6vw,2.2rem)] font-extrabold leading-tight">
              FastAPI · Sentence Transformers · scikit-learn · React
            </h2>
            <p className="mt-2 font-body text-[13px] leading-relaxed text-ink-soft">
              Set in UnifrakturCook, Playfair Display, IM Fell English, Libre Baskerville and
              Special Elite. Engraved plates are original decorative illustrations. Built as a
              single-node press: Python 3.12, SQLite FTS5, React 19 and Vite.
            </p>
          </div>
          <Link to="/dashboard" className="paper-button-solid">
            Explore the archive <ArrowRight size={12} />
          </Link>
        </div>
      </section>
    </div>
  )
}
