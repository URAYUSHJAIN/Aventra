import { useState } from 'react'
import { ArrowRight, BarChart3, Minus, TrendingDown, TrendingUp } from 'lucide-react'
import { analyzeNews, type NewsAnalysisResult } from '../../services/newsApi'

const probabilityRows: Array<[keyof Pick<NewsAnalysisResult, 'positive_probability' | 'neutral_probability' | 'negative_probability'>, string]> = [
  ['positive_probability', 'Positive'], ['neutral_probability', 'Neutral'], ['negative_probability', 'Negative'],
]
const LABEL_ICON = { positive: TrendingUp, neutral: Minus, negative: TrendingDown }
const LABEL_TONE = { positive: 'positive', neutral: 'neutral', negative: 'negative' }

export function NewsAnalysis() {
  const [text, setText] = useState(''); const [result, setResult] = useState<NewsAnalysisResult>(); const [error, setError] = useState(''); const [loading, setLoading] = useState(false)
  const submit = async (event: React.FormEvent) => { event.preventDefault(); if (!text.trim()) { setError('Enter financial news to begin analysis.'); setResult(undefined); return } setLoading(true); setError(''); try { setResult(await analyzeNews({ text })) } catch (reason) { setResult(undefined); setError(reason instanceof Error ? reason.message : 'Unable to analyse the text. Please try again.') } finally { setLoading(false) } }
  const Icon = result ? LABEL_ICON[result.label] : null
  return <section className="news-tool" id="news-analysis" aria-labelledby="news-tool-title"><div className="wrap news-tool-grid">
    <div className="news-tool-copy">
      <p className="eyebrow">NEWS INTELLIGENCE · TEXT SENTIMENT</p>
      <h1 id="news-tool-title" className="display-title">Read financial language <em>in context.</em></h1>
      <p className="section-intro">Paste a headline, an article or a filing excerpt and see whether its financial language reads as positive, neutral or negative. Sentiment is a contextual signal, not a market prediction or financial advice.</p>
      <p className="section-intro">For instrument-linked news with timing and relevance, open an instrument in <a className="text-link" href="/intelligence">Intelligence</a>.</p>
      <details className="disclosure"><summary>Model details</summary><p className="note">Text is classified on the Aventra server by FinBERT (ProsusAI), a BERT model fine-tuned for financial sentiment. Long text is split into sentences of up to 64 tokens and the class probabilities are averaged. English only. Confidence is the highest averaged probability; it is not calibrated.</p></details>
    </div>
    <div className="news-tool-card">
      <form onSubmit={submit}><label htmlFor="news-text">Financial news or text</label><textarea id="news-text" value={text} onChange={(event) => setText(event.target.value)} maxLength={12000} placeholder="e.g. The company reported quarterly revenue below expectations and cut its guidance…" aria-describedby="news-text-count" />
        <div className="news-form-footer"><span id="news-text-count">{text.length.toLocaleString()} / 12,000</span><button className="button button-primary" disabled={loading}>{loading ? 'Analysing…' : <>Analyze News <ArrowRight size={15} aria-hidden="true" /></>}</button></div></form>
      {!result && !error && !loading && <p className="analysis-state" aria-live="polite">Enter financial news to begin analysis.</p>}
      {loading && <p className="analysis-state" role="status"><BarChart3 size={15} className="spinning" aria-hidden="true" /> Analysing financial text…</p>}
      {error && <p className="state-inline is-error" role="alert">{error}</p>}
      {result && Icon && <div className="sentiment-result" aria-live="polite">
        <div className="result-heading"><span className="eyebrow">RESULT</span><strong className={`result-label text-${LABEL_TONE[result.label]}`}><Icon size={20} aria-hidden="true" />{result.label}</strong></div>
        <div className="result-summary"><div><span>Confidence</span><strong>{Math.round(Math.max(result.positive_probability, result.neutral_probability, result.negative_probability) * 100)}%</strong></div><div><span>Sentiment score</span><strong>{result.sentiment_score >= 0 ? '+' : ''}{result.sentiment_score.toFixed(2)}</strong></div></div>
        <div className="probabilities">{probabilityRows.map(([key, label]) => <div className="probability" key={key}><div><span>{label}</span><b>{Math.round(result[key] * 100)}%</b></div><i aria-hidden="true"><b className={`bar-${label.toLowerCase()}`} style={{ width: `${Math.max(0, Math.min(100, result[key] * 100))}%` }} /></i></div>)}</div>
      </div>}
    </div>
  </div></section>
}
