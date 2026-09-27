// Response types mirroring the Flask API (backend/routes, ml/pipelines/intelligence.py). Keep in sync with docs/14_API_SPECIFICATION.md.

export interface DataSource { provider: string; is_demo: boolean; stale?: boolean; fetched_at?: string | null; notes?: string[] }

export interface Asset { symbol: string; name: string; exchange: string; sector: string; is_demo: boolean }

export interface Quote {
  symbol: string; name: string; exchange?: string; currency: string | null; price: number; previous_close: number | null; change_pct: number | null
  volume: number | null; day_high: number | null; day_low: number | null; market_time: string | null
  intraday: Array<{ timestamp: string; close: number }>; interval: string; market_state: 'OPEN' | 'CLOSED' | 'DEMO'; data_source: DataSource
}
export interface BatchQuote { symbol: string; status: 'ok' | 'unavailable'; quote: Quote | null; error?: string }

export interface SentimentResult {
  label: 'positive' | 'neutral' | 'negative'; positive_probability: number; neutral_probability: number; negative_probability: number
  sentiment_score: number; confidence: number; model: string; model_version?: string | null
}
export interface EntityLink { symbol: string; entity_match_confidence: number; mapping_method: string }
export interface NewsItem { news_id: string; headline: string; source: string | null; url: string | null; published_at: string; is_demo: boolean; sentiment: SentimentResult | null; entity: EntityLink | null }

export interface ContributingFeature { feature: string; label: string; value: number; baseline_median: number; robust_z: number; direction: 'above' | 'below'; deviation_score: number; explanation: string }
export interface AnomalyResult {
  anomaly_id: string; trading_date: string; timestamp: string; anomaly_score: number; severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'; is_anomaly: boolean
  scores: { statistical: number | null; fingerprint: number | null; isolation_forest: number | null }; model_agreement: number
  contributing_features: ContributingFeature[]; explanation?: string[]
}

export interface CorrelationMatch {
  news_id: string; headline: string; source: string | null; url: string | null; published_at: string; sentiment: SentimentResult | null
  entity: { confidence: number; method: string }; category: { category: string; matched_keywords: string[]; method: string }
  relation: 'published_before_session' | 'published_during_session' | 'published_after_session_close'; hours_from_session: number
  components: { temporal_proximity: number; asset_match: number; sentiment_strength: number; anomaly_strength: number }
  correlation_score: number; semantic_relevance: number | null; sentiment_available: boolean
}
export interface Correlation {
  status: 'aligned_news_found' | 'no_aligned_news' | 'news_unavailable'; best_score: number; matches: CorrelationMatch[]
  window: { start: string | null; end: string | null; session_open: string; session_close: string }; interpretation?: string
}

export interface RiskComponent { name: string; description: string; value: number | null; weight: number; gate: number; contribution: number; available: boolean }
export interface RiskAssessment { score: number; level: 'LOW' | 'MODERATE' | 'ELEVATED' | 'HIGH'; basis: string; components: RiskComponent[]; method: string; disclaimer: string }

export interface EvidenceItem { timestamp: string; type: string; signal: string; description: string; value: number | null; source: string; url?: string | null; gap_minutes_from_previous: number | null }
export interface Explanation { what: string; when: string; how_unusual: string; signals: string[]; news: string; timing: string; why: string; caveat: string }

export interface Assessment {
  event_id: string; trading_date: string; anomaly: AnomalyResult; correlation: Correlation; risk: RiskAssessment
  fingerprint_score: number | null; evidence: EvidenceItem[]; explanation: Explanation
}

export interface FingerprintDimension { feature: string; label: string; unit: 'shares' | 'fraction'; value: number | null; baseline_median: number | null; p05: number | null; p95: number | null; robust_z: number | null; deviation_score: number | null; weight: number }
export interface FingerprintPoint { date: string; value: number | null; median: number | null; lower: number | null; upper: number | null; robust_z: number | null }
export interface Fingerprint {
  as_of: string; score: number | null; level: string; status: string; dimensions: FingerprintDimension[]; series: Record<string, FingerprintPoint[]>
  method: { baseline: string; window: number; min_history: number; guarded_update_z: number; score_mapping: string; weights: Record<string, number> }
}

export interface MarketPoint { date: string; open: number; high: number; low: number; close: number; volume: number | null; anomaly_score: number | null; is_anomaly: boolean; severity: string | null }

export interface Intelligence {
  run_id: string; symbol: string; asset: Asset; generated_at: string; pipeline_version: string
  data_source: { market: DataSource; benchmark: { symbol: string; name: string; status: string } | null; news: { provider: string; is_demo: boolean; status: string; message: string | null; sentiment_status?: string } }
  market: { latest: { trading_date: string; open: number; high: number; low: number; close: number; volume: number | null; return_1: number | null; volatility_20: number | null; volume_ratio: number | null }; series: MarketPoint[] }
  fingerprint: Fingerprint
  anomaly: { current: AnomalyResult; threshold: number; flagged_count: number; window: { start: string; end: string; bars: number }; change_points: { status: string; change_points: string[]; retrospective?: boolean } }
  news: { status: string; message: string | null; items: NewsItem[]; sentiment_summary: { count: number; scored: number; labels: Record<'positive' | 'neutral' | 'negative', number>; mean_score: number | null } }
  current_assessment: Assessment
  events: Assessment[]
  lead_lag: { status: string; days_with_news: number; required?: number; lags: Array<{ lag_days: number; correlation: number; n: number }> }
  models: Record<string, unknown>
  parameters: Record<string, unknown>
  disclaimer: string
}
