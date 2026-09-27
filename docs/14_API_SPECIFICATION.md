# 14 — API Specification

Flask API served by `backend/app.py` (`create_app()`), prefix `/api`. All responses use one envelope:

```json
{ "success": true,  "data": { ... } }
{ "success": false, "error": "Human-readable message", "code": "PROVIDER_UNAVAILABLE", "attempts": [ ... ] }
```

- Timestamps are ISO-8601 **UTC**. Trading dates are `YYYY-MM-DD` in the instrument's exchange time; 24/7 markets use the UTC date.
- Stack traces and internal details are never returned.

## Instrument IDs

Every instrument path parameter is a **canonical ID** `NAMESPACE:CODE`, for example:
- `XNAS:AAPL`, `XNSE:RELIANCE`, `XBOM:500325`;
- `CRYPTO:BTC-USDT`, `CRYPTO:CG-solana`;
- `FX:USDINR`, `MF-IN:122639`, `IDX:NSE-NIFTY`, `RATE:DGS10`.

Rules:
- IDs are validated with a strict pattern (letters, digits, `& - . ^ _`; no spaces, slashes or `..`). An invalid ID gives 400 `INVALID_INSTRUMENT_ID`.
- A bare v0.1 symbol (`RELIANCE`) is accepted and resolves to `XNSE:RELIANCE`.
- URL-encoding the colon (`%3A`) is optional.

## Status codes and data-availability states

Typed states mean "Data unavailable / insufficient source data"; `attempts[]` lists `{provider, status, reason, detail}` for each provider tried.

| HTTP | `code` | Meaning |
|---|---|---|
| 200 | — | Success |
| 202 | — | Analysis queued/running: `data = {status, job, previous_result, message}` |
| 400 | `INVALID_INSTRUMENT_ID`, `HTTP_ERROR` | Invalid input |
| 404 | `INSTRUMENT_NOT_FOUND` | Not in the Instrument Master (search first) / unknown anomaly or event ID |
| 413 | `HTTP_ERROR` | News text longer than 12,000 characters |
| 422 | `NO_PROVIDER_FOR_ASSET` | No permitted provider supports this instrument (listing only) |
| 422 | `INSUFFICIENT_HISTORY`, `INSUFFICIENT_SOURCE_DATA` | Too few valid observations / provider data failed validation |
| 503 | `PROVIDER_UNAVAILABLE`, `RATE_LIMITED` | Provider not configured (missing key), unreachable or rate-limited |
| 502 | `PROVIDER_UNAVAILABLE` | Unexpected provider error outside the router |
| 503 | — | Local model (FinBERT) unavailable (`/api/news/analyze`) |
| 500 | `INTERNAL_ERROR` | Unexpected error (details only in server logs) |

## Health, providers, instruments

| Method & path | Returns |
|---|---|
| `GET /api/health` | `status`, `database` (`ok`), `database_backend` (`postgresql`/`sqlite`), `instrument_master_size`, `job_mode`, `finbert_model_files`, `synthetic_test_data` (true only in tests), `pipeline_version` |
| `GET /api/providers` | Capability matrix: per provider `asset_classes, exchanges, fields, intervals, history, listing, search, credential_env, configured, rate_limit_per_minute, daily_budget, max_history_days, terms, health {circuit, last_hour}` |
| `GET /api/instruments/search?q=&asset_class=&exchange=&country=&limit=&cursor=` | `items[]` (InstrumentSummary), `next_cursor`, `query`, `master_size`, `master_status`. The query is ≤ 64 characters, limit 1–50, and `asset_class` is one of the 11 classes. Ranking: exact symbol → alias → name prefix → contains, then popularity. |
| `GET /api/instruments/<id>` | InstrumentSummary + `aliases`, `providers`, `data_providers[] {provider, provider_symbol, configured, reason}` |
| `POST /api/instruments/resolve` body `{"query": "..."}` | Creates master rows from providers that can search outside the listings (FRED series when `FRED_API_KEY` is set): `existing[]`, `created[]`, `providers[]` (unavailable reasons) |

InstrumentSummary = `{instrument_id, symbol, name, asset_class, exchange, country, currency, timezone, status, isin, capabilities {has_ohlc, has_volume, value_kind, minimum_history}, class_source, class_confidence}`.

## Market data (provider → database → Flask; the browser never calls a provider)

| Method & path | Returns |
|---|---|
| `GET /api/market/<id>` | Snapshot: `instrument, as_of, value_kind, last, previous, change_pct` (null for yields), `change_bp` (yields only), `volume` (null when not provided), `series[] {timestamp, close}` (last 60 daily observations), `interval, data_source, quality {stale, age_days, rows_out}` |
| `GET /api/market/snapshots?ids=A,B` | `items[] {instrument_id, status: ok or a typed state, snapshot or null, error?, attempts?}` — up to 25 IDs, fetched concurrently; one failure never fails the batch |
| `GET /api/market/<id>/history?limit=250` | Validated daily observations `bars[] {timestamp, open, high, low, close, volume}` (null where the provider has no such field), `validation`, `data_source` |
| `GET /api/watchlists/default` | `{name, items[] {instrument_id, symbol, name, asset_class, exchange, currency} or {instrument_id, status: not_in_master}, configured_by: "AVENTRA_DEFAULT_WATCHLIST"}` — empty unless configured |

`data_source` = `{provider, provider_symbol, fetched_at, stale, currency, value_kind, adjusted, notes[], attribution?}`.

## Intelligence (asynchronous)

| Method & path | Returns |
|---|---|
| `GET /api/intelligence/<id>` | 200 full payload (a stored run younger than 15 min); **202** `{status, job, previous_result, message}` while an analysis is queued/running; a typed error if the last job failed within 10 min. `?refresh=1` queues a new run. |
| `POST /api/intelligence/<id>/runs` | 202 `{job}` — queue a fresh analysis (deduplicated per instrument) |
| `GET /api/jobs/<job_id>` | `{id, type, instrument_id, status: queued/running/done/failed, attempts, max_attempts, error, result, created_at, updated_at, run_after}` |
| `GET /api/fingerprint/<id>` | `score, level, status, as_of, version, dimensions[], series{dim: [...]}, method` |
| `GET /api/anomaly/<id>` | `current, threshold, flagged_count, window, change_points, flagged[], series[], models` |
| `POST /api/anomaly/detect` body `{"instrument_id": "..."}` (legacy `symbol` accepted) | Anomaly view after a forced run (sync mode) or 202 with a job |
| `GET /api/anomalies?instrument=&limit=` | Stored flagged anomalies (one instrument or all) |
| `GET /api/anomalies/<anomaly_id>` | One stored anomaly (`AN-<key>-<YYYYMMDD>`) |
| `GET /api/events?instrument=&limit=` | Stored correlated events |
| `GET /api/events/<event_id or instrument id>` | One event (`EV-<key>-<YYYYMMDD>`) or an instrument's events |
| `GET /api/risk/<id>` | `current` risk, `latest_flagged_event` risk, disclaimer |
| `GET /api/evidence/<anomaly_id or event_id>` | `evidence[]` (with `provenance`), `explanation`, `risk` |

### `GET /api/intelligence/<id>` payload

```text
run_id, instrument_id, symbol, generated_at, pipeline_version, disclaimer
asset          {instrument_id, symbol, name, asset_class, exchange, country, currency, timezone, calendar, is_demo}
capabilities   {has_ohlc, has_volume, value_kind, minimum_history, calendar, timezone, currency}
feature_set    ohlcv | ohlcv_continuous | close_volume | close | yield
versions       {feature_set, fingerprint, model, thresholds, pipeline}
feature_definitions, validation, timings_ms, models, parameters
data_source    {market, benchmark {instrument_id, name, status, reason?} | null, news {provider, status, message, sentiment_status}}
market         latest {trading_date, open, high, low, close, volume, return_1, volatility_20, volume_ratio, change_bp}; series[] over the scoring window
fingerprint    score, level, status, version, dimensions[] {feature, label, unit (fraction|shares|bp), value, baseline_median, p05, p95, robust_z, deviation_score, weight}, series, method
anomaly        current, threshold, flagged_count, window {start, end, bars}, change_points (retrospective)
news           status (ok | no_relevant_news | unavailable | stale_cache), message, items[], sentiment_summary
current_assessment, events[]   Assessment (below)
lead_lag       status, days_with_news, lags[]
```

**Assessment** = `{event_id, trading_date, fingerprint_score, anomaly, correlation, risk, evidence[], explanation}`:

- `anomaly`:
  - `anomaly_id, trading_date, timestamp, anomaly_score (0–1), severity, is_anomaly`;
  - `scores {statistical, fingerprint, isolation_forest}, model_agreement`;
  - `contributing_features[]`.
- `correlation`:
  - `status (aligned_news_found | no_aligned_news | news_unavailable), window, best_score, interpretation`;
  - `matches[] {headline, source, url, published_at, sentiment, entity, category, relation, hours_from_session, components, correlation_score, semantic_relevance}`.
- `risk`: `score (0–100), level, basis, components[] {name, value, weight, gate, contribution, available}, method, disclaimer`.
- `evidence[]`: `{timestamp, type, signal, description, value, source, url?, gap_minutes_from_previous, provenance}`.
- `explanation`: `what, when, how_unusual, signals[], news, timing, why, caveat`.

## News and sentiment

| Method & path | Returns |
|---|---|
| `POST /api/news/analyze` body `{"text": "..."}` | FinBERT result. **Original fields (unchanged):** `label, positive_probability, neutral_probability, negative_probability, sentiment_score`. **Added:** `sentiment, confidence` (uncalibrated), `model, model_version, timestamp, source: "user_input", text` |
| `GET /api/news?instrument=<id>&limit=20` (legacy `symbol=`) | `instrument_id, items[] {news_id, headline, source, url, published_at, is_demo, sentiment, entity {instrument_id, entity_match_confidence, mapping_method}}, data_source {provider, status, message, sentiment_status}` |
| `GET /api/news/<id>` | Same as above |

Frontend types: `frontend/src/types/api.ts` (keep in sync).
