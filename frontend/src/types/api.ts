// Response types mirroring the Flask API (backend/routes, ml/pipelines/intelligence.py). Keep in sync with docs/14_API_SPECIFICATION.md.

export type AssetClass = 'equity' | 'etf' | 'reit' | 'invit' | 'bond' | 'index' | 'mutual_fund' | 'forex' | 'crypto' | 'rate' | 'commodity'
export type ValueKind = 'price' | 'nav' | 'reference_rate' | 'yield' | 'index_level'

// Data-availability states surfaced by the API ("Data unavailable / insufficient source data").
export type DataState = 'INSTRUMENT_NOT_FOUND' | 'INVALID_INSTRUMENT_ID' | 'NO_PROVIDER_FOR_ASSET' | 'PROVIDER_UNAVAILABLE' | 'RATE_LIMITED'
  | 'INSUFFICIENT_HISTORY' | 'INSUFFICIENT_SOURCE_DATA' | 'ANALYSIS_FAILED'

export interface ProviderAttempt { provider: string; status: string; reason?: string | null; detail?: string | null }

export interface Capabilities { has_ohlc: boolean; has_volume: boolean; value_kind: ValueKind; minimum_history?: number; calendar?: string | null; timezone?: string | null; currency?: string | null }

export interface InstrumentSummary {
  instrument_id: string; symbol: string; name: string; asset_class: AssetClass; exchange: string | null; country: string | null
  currency: string | null; timezone: string | null; status: string; capabilities: Capabilities | null; class_source?: string | null; class_confidence?: number | null
}
export interface SearchResult { items: InstrumentSummary[]; next_cursor: string | null; query: string; master_size: number; master_status: string }

export interface DataSource {
  provider: string; provider_symbol?: string | null; is_demo: boolean; stale?: boolean; fetched_at?: string | null; notes?: string[]
  currency?: string | null; value_kind?: ValueKind; adjusted?: boolean; attribution?: string; attempts?: ProviderAttempt[]
}

export interface Snapshot {
  instrument: Pick<InstrumentSummary, 'instrument_id' | 'symbol' | 'name' | 'asset_class' | 'exchange' | 'country' | 'currency' | 'timezone' | 'capabilities'>
  as_of: string; value_kind: ValueKind; last: number; previous: number | null; change_pct: number | null; change_bp: number | null; volume: number | null
  series: Array<{ timestamp: string; close: number }>; interval: string; data_source: DataSource; quality: { stale: boolean; age_days: number; rows_out: number }
}
export interface SnapshotItem { instrument_id: string; status: 'ok' | DataState; snapshot: Snapshot | null; error?: string; attempts?: ProviderAttempt[] }
export interface Watchlist { name: string; items: Array<{ instrument_id: string; symbol?: string; name?: string; asset_class?: AssetClass; status?: string }> }

export interface Job { id: number; type: string; instrument_id: string | null; status: 'queued' | 'running' | 'done' | 'failed'; attempts: number; error: string | null; updated_at: string | null }

export interface SentimentResult {
  label: 'positive' | 'neutral' | 'negative'; positive_probability: number; neutral_probability: number; negative_probability: number
  sentiment_score: number; confidence: number; model: string; model_version?: string | null
}
export interface EntityLink { instrument_id: string; entity_match_confidence: number; mapping_method: string }
export interface NewsItem { news_id: string; headline: string; source: string | null; url: string | null; published_at: string; is_demo: boolean; sentiment: SentimentResult | null; entity: EntityLink | null }

export interface ContributingFeature { feature: string; label: string; value: number; baseline_median: number; robust_z: number; direction: 'above' | 'below'; deviation_score: number; explanation: string }
export interface AnomalyResult {
  anomaly_id: string; trading_date: string; timestamp: string; anomaly_score: number; severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'; is_anomaly: boolean
  scores: { statistical: number | null; fingerprint: number | null; isolation_forest: number | null }; model_agreement: number
  contributing_features: ContributingFeature[]; explanation?: string[]; score_semantics?: string
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

export interface EvidenceItem { timestamp: string; type: string; signal: string; description: string; value: number | null; source: string; url?: string | null; gap_minutes_from_previous: number | null; provenance?: Record<string, unknown> }
export interface Explanation { what: string; when: string; how_unusual: string; signals: string[]; news: string; timing: string; why: string; caveat: string }

export interface Assessment {
  event_id: string; trading_date: string; anomaly: AnomalyResult; correlation: Correlation; risk: RiskAssessment
  fingerprint_score: number | null; evidence: EvidenceItem[]; explanation: Explanation
}

export type DimensionUnit = 'shares' | 'fraction' | 'bp'
export interface FingerprintDimension { feature: string; label: string; unit: DimensionUnit; value: number | null; baseline_median: number | null; p05: number | null; p95: number | null; robust_z: number | null; deviation_score: number | null; weight: number }
export interface FingerprintPoint { date: string; value: number | null; median: number | null; lower: number | null; upper: number | null; robust_z: number | null }
export interface Fingerprint {
  as_of: string; score: number | null; level: string; status: string; version?: string; dimensions: FingerprintDimension[]; series: Record<string, FingerprintPoint[]>
  method: { baseline: string; window: number; min_history: number; guarded_update_z: number; score_mapping: string; weights: Record<string, number>; weights_status?: string }
}

export interface MarketPoint { date: string; open: number | null; high: number | null; low: number | null; close: number; volume: number | null; anomaly_score: number | null; is_anomaly: boolean; severity: string | null }

export interface IntelligenceAsset { instrument_id: string; symbol: string; name: string; asset_class: AssetClass; exchange: string | null; country: string | null; currency: string | null; timezone: string | null; calendar: string | null; is_demo: boolean }

export interface Intelligence {
  run_id: string; instrument_id: string; symbol: string; asset: IntelligenceAsset; capabilities: Capabilities; feature_set: string
  versions: Record<string, string | null>; generated_at: string; pipeline_version: string
  data_source: { market: DataSource; benchmark: { instrument_id?: string; name?: string; status: string; reason?: string } | null; news: { provider: string | null; is_demo: boolean; status: string; message: string | null; sentiment_status?: string } }
  market: { latest: { trading_date: string; open: number | null; high: number | null; low: number | null; close: number; volume: number | null; return_1: number | null; volatility_20: number | null; volume_ratio: number | null; change_bp: number | null }; series: MarketPoint[] }
  fingerprint: Fingerprint
  anomaly: { current: AnomalyResult; threshold: number; flagged_count: number; window: { start: string; end: string; bars: number }; change_points: { status: string; change_points: string[]; retrospective?: boolean } }
  news: { status: 'ok' | 'no_relevant_news' | 'unavailable' | 'stale_cache'; message: string | null; items: NewsItem[]; sentiment_summary: { count: number; scored: number; labels: Record<'positive' | 'neutral' | 'negative', number>; mean_score: number | null } }
  current_assessment: Assessment
  events: Assessment[]
  lead_lag: { status: string; days_with_news: number; required?: number; lags: Array<{ lag_days: number; correlation: number; n: number }> }
  models: Record<string, unknown>
  parameters: Record<string, unknown>
  disclaimer: string
}

// 202 body of GET /api/intelligence/<id> while an analysis job is queued/running.
export interface AnalysisPending { status: 'queued' | 'running'; job: Job; previous_result: Intelligence | null; message: string }
