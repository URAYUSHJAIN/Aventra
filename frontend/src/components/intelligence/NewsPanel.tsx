import type { Intelligence } from '../../types/api'
import { fmtDateTime, fmtSigned } from '../../utils/format'
import { Badge } from '../common/Badge'
import { Panel } from '../common/Panel'
import { EmptyState } from './StateViews'

const SENTIMENT_TONE = { positive: 'positive', neutral: 'neutral', negative: 'negative' } as const

export function NewsPanel({ news, limit = 8, timeZone, id }: { news: Intelligence['news']; limit?: number; timeZone?: string | null; id?: string }) {
  const summary = news.sentiment_summary
  return <Panel id={id} className="panel-news" eyebrow="NEWS INTELLIGENCE" titleId="news-title" title="News sentiment"
    aside={summary.scored > 0 && <div className="sentiment-counts" aria-label="Sentiment label counts">{(['positive', 'neutral', 'negative'] as const).map((label) => <Badge key={label} tone={SENTIMENT_TONE[label]}>{summary.labels[label]} {label}</Badge>)}</div>}>
    {news.status === 'unavailable' ? <p className="state-inline is-unavailable" role="status">{news.message && !/^news context unavailable/i.test(news.message) ? `News context unavailable: ${news.message}` : news.message ?? 'News context unavailable.'}</p>
      : news.items.length === 0 ? <EmptyState message={news.status === 'no_relevant_news' ? 'No relevant news found for this instrument in the provider feed.' : 'No news linked to this instrument was found.'} />
      : <ul className="news-list">{news.items.slice(0, limit).map((item) => <li key={item.news_id}>
        <div className="news-meta"><span>{item.source ?? 'Unknown source'}</span><time dateTime={item.published_at}>{fmtDateTime(item.published_at, timeZone)}</time></div>
        {item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.headline}</a> : <p>{item.headline}</p>}
        <div className="news-tags">{item.sentiment ? <Badge tone={SENTIMENT_TONE[item.sentiment.label]}>{item.sentiment.label} {fmtSigned(item.sentiment.sentiment_score)}</Badge> : <Badge>sentiment unavailable</Badge>}
          {item.entity && <span className="meta-tag">relevance {item.entity.entity_match_confidence.toFixed(2)} · {item.entity.mapping_method.replace(/_/g, ' ')}</span>}
          {item.sentiment && <span className="meta-tag">confidence {item.sentiment.confidence.toFixed(2)}</span>}{item.is_demo && <span className="meta-tag">synthetic</span>}</div>
      </li>)}</ul>}
    {news.message && news.status !== 'unavailable' && <p className="note">{news.message}</p>}
    <details className="disclosure"><summary>How sentiment is measured</summary>
      <p className="note">Headlines are classified by FinBERT, a financial-language sentiment model running on the Aventra server. It classifies financial-text sentiment only; it does not verify accuracy or detect misinformation. Confidence is the mean softmax probability, not a calibrated probability. Relevance is the entity-link confidence between the article and this instrument.</p></details>
  </Panel>
}
