import type { Intelligence } from '../../types/api'
import { fmtDateTime, fmtSigned } from '../../utils/format'
import { EmptyState } from './StateViews'

export function NewsPanel({ news, limit = 8 }: { news: Intelligence['news']; limit?: number }) {
  const summary = news.sentiment_summary
  return <section className="intel-panel" aria-labelledby="news-title">
    <header className="intel-panel-head"><div><p className="eyebrow">FINANCIAL NEWS · FINBERT</p><h2 id="news-title">News sentiment</h2></div>
      {summary.scored > 0 && <div className="sentiment-counts" aria-label="Sentiment label counts">{(['positive', 'neutral', 'negative'] as const).map((label) => <span key={label} className={`sentiment-${label}`}>{summary.labels[label]} {label}</span>)}</div>}</header>
    {news.status === 'unavailable' ? <p className="intel-state intel-error" role="alert">News context unavailable{news.message ? ` — ${news.message}` : '.'}</p>
      : news.items.length === 0 ? <EmptyState message="No news linked to this asset was found." />
      : <ul className="news-list">{news.items.slice(0, limit).map((item) => <li key={item.news_id}>
        <div className="news-meta"><span>{item.source ?? 'Unknown source'}</span><time dateTime={item.published_at}>{fmtDateTime(item.published_at)}</time></div>
        {item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.headline}</a> : <p>{item.headline}</p>}
        <div className="news-tags">{item.sentiment ? <span className={`sentiment-tag sentiment-${item.sentiment.label}`}>{item.sentiment.label} {fmtSigned(item.sentiment.sentiment_score)} · conf {item.sentiment.confidence.toFixed(2)}</span> : <span className="sentiment-tag">sentiment unavailable</span>}
          {item.entity && <span className="entity-tag">entity {item.entity.mapping_method.replace('_', ' ')} · {item.entity.entity_match_confidence.toFixed(2)}</span>}{item.is_demo && <span className="entity-tag">synthetic</span>}</div>
      </li>)}</ul>}
    {news.message && news.status !== 'unavailable' && <p className="intel-note">{news.message}</p>}
    <p className="intel-note">FinBERT classifies financial-text sentiment only; it does not verify accuracy or detect misinformation. Confidence is the mean softmax probability, not a calibrated probability.</p>
  </section>
}
