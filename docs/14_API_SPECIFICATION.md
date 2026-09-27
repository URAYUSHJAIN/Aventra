# 14 — API Specification

Flask API served by `backend/app.py` (`create_app()`), prefix `/api`. All responses use one envelope:

```json
{ "success": true,  "data": { ... } }
{ "success": false, "error": "Human-readable message" }
```

Timestamps are ISO-8601 **UTC** (`2026-06-15T03:45:00Z`); trading dates are `YYYY-MM-DD` in exchange time (IST). Stack traces are never returned.

| Status | Meaning |
|---|---|
| 400 | Invalid input (bad symbol format, missing body, non-integer query parameter) |
| 404 | Unknown asset / ID / route, or the provider has no data for the symbol |
| 413 | News text longer than 12,000 characters |
| 422 | `insufficient_history` — too few sessions for a reliable fingerprint |
| 502 | Upstream market provider unavailable, rate-limited or returned unusable data |
| 503 | Local model (FinBERT) unavailable |
| 500 | Unexpected error (details only in server logs) |

Symbols: letters, digits, `& - . ^`, ≤ 20 chars; a `.NS` suffix is stripped. "Analysed" endpoints accept only assets in `data/reference/assets.json` (RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK, DEMO). Quote endpoints accept any NSE symbol.

Where the Final Implementation Plan and the ML Pipeline name paths differently, **both** are served (decision recorded in AGENTS.md §32, C5). A path segment starting with `AN-` / `EV-` is an ID; anything else is a symbol.

## Health and assets

| Method & path | Returns |
|---|---|
| `GET /api/health` | `status`, `data_mode` (`live`/`demo`), `finbert_model_files` (`present`/`missing`), `demo_dataset`, `pipeline_version` |
| `GET /api/assets` | `assets[]` `{symbol, name, exchange, sector, is_demo}`, `benchmark` |

## Market data (provider → Flask; the browser never calls the provider)

| Method & path | Returns |
|---|---|
| `GET /api/market/<symbol>` | Quote: `price, previous_close, change_pct, volume, day_high, day_low, market_time, market_state (OPEN/CLOSED/DEMO), intraday[] {timestamp, close}, interval, data_source` |
| `GET /api/market/quotes?symbols=A,B` | `quotes[]` `{symbol, status: ok|unavailable, quote|null, error?}` — max 25 symbols, fetched concurrently |
| `GET /api/market/<symbol>/history?limit=250` | Validated daily bars `bars[] {timestamp, open, high, low, close, volume}`, `validation` report, `data_source` (analysed assets) |
| `GET /api/market/search?q=infy` | `results[] {symbol, name, exchange, analysed}` (2–40 chars) |

`data_source` = `{provider, is_demo, stale, fetched_at, notes?}`. `stale: true` means the live provider failed and previously stored prices were used.

## News and sentiment

| Method & path | Returns |
|---|---|
| `POST /api/news/analyze` body `{"text": "..."}` | FinBERT result. **Original fields (unchanged):** `label, positive_probability, neutral_probability, negative_probability, sentiment_score`. **Added:** `sentiment` (= label), `confidence` (mean softmax probability of the winning class — not calibrated), `model`, `model_version`, `timestamp`, `source: "user_input"`, `text` |
| `GET /api/news?symbol=RELIANCE&limit=20` | Asset-linked news `items[] {news_id, headline, source, url, published_at, is_demo, sentiment|null, entity {symbol, entity_match_confidence, mapping_method}}` and `data_source {provider, status: ok|stale_cache|unavailable, sentiment_status, message}` |
| `GET /api/news/<symbol>` | Same as above (ML Pipeline path) |

## Intelligence (runs / reuses the pipeline; add `?refresh=1` to force a new run)

| Method & path | Returns |
|---|---|
| `GET /api/intelligence/<symbol>` | Full consolidated payload (below) |
| `GET /api/fingerprint/<symbol>` | `score, level, status, as_of, dimensions[], series{dim: [...]}, method` |
| `GET /api/anomaly/<symbol>` | `current` anomaly, `threshold, flagged_count, window, change_points, flagged[], series[], models` |
| `POST /api/anomaly/detect` body `{"symbol": "TCS"}` | Same as above after a forced re-run |
| `GET /api/anomalies?symbol=&limit=` | Flagged anomalies (for one symbol, or all stored) |
| `GET /api/anomalies/<anomaly_id>` | One stored anomaly (`AN-<SYMBOL>-<YYYYMMDD>`) |
| `GET /api/events?symbol=&limit=` | Correlated events (assessments of flagged sessions) |
| `GET /api/events/<event_id or symbol>` | One event (`EV-<SYMBOL>-<YYYYMMDD>`) or the events of a symbol |
| `GET /api/risk/<symbol>` | `current` risk (latest session), `latest_flagged_event` risk, disclaimer |
| `GET /api/evidence/<anomaly_id or event_id>` | `evidence[]`, `explanation`, `risk` of a stored event |

### `GET /api/intelligence/<symbol>` payload

```text
run_id, symbol, asset, generated_at, pipeline_version, disclaimer
data_source   { market, benchmark, news }                       provenance of every input
validation    rows_in/out, duplicates_removed, invalid_rows_removed, holiday_placeholders_removed, large_moves_flagged, ...
market        latest {trading_date, close, volume, return_1, volatility_20, volume_ratio}; series[] over the scoring window
fingerprint   score (0–1), level, dimensions[] {feature, value, baseline_median, p05, p95, robust_z, deviation_score, weight}, series, method
anomaly       current (see Assessment.anomaly), threshold, flagged_count, window {start, end, bars}, change_points (retrospective)
news          status, items[], sentiment_summary {count, scored, labels, mean_score}
current_assessment   Assessment for the latest session
events[]             Assessment for each flagged session (newest first)
lead_lag      status (ok | insufficient_data), lags[] {lag_days, correlation, n}
models        isolation_forest metadata (version, trained_through, n_train, features), finbert status, semantic model status
parameters    thresholds, weights, windows, seed, calibration_status
timings_ms    per-stage durations
```

**Assessment** = `{event_id, trading_date, fingerprint_score, anomaly, correlation, risk, evidence[], explanation}`:

- `anomaly` — `anomaly_id, trading_date, timestamp (session open UTC), anomaly_score (0–1), severity (LOW/MEDIUM/HIGH/CRITICAL), is_anomaly, scores {statistical, fingerprint, isolation_forest}, model_agreement, contributing_features[] {feature, label, value, baseline_median, robust_z, direction, deviation_score, explanation}`
- `correlation` — `status (aligned_news_found | no_aligned_news | news_unavailable), window, best_score, matches[] {headline, source, url, published_at, sentiment, entity, category, relation, hours_from_session, components, correlation_score, semantic_relevance}, interpretation`
- `risk` — `score (0–100), level (LOW/MODERATE/ELEVATED/HIGH), basis, components[] {name, value, weight, gate, contribution, available}, method, disclaimer`
- `evidence[]` — `{timestamp, type, signal, description, value, source, url?, gap_minutes_from_previous}` ordered by time
- `explanation` — `what, when, how_unusual, signals[], news, timing, why, caveat`

Frontend types: `frontend/src/types/api.ts` (keep in sync).
