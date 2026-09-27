# 04 — System Architecture (as implemented)

```text
Browser (React 19 + TS + Vite)
   │  services/apiClient.ts → /api/*       (never calls a data provider directly)
   ▼
nginx (Docker) or the Vite dev proxy
   ▼
Flask API  backend/app.py
   routes/{instrument,market,intelligence,news}_routes.py → services/{market,intelligence}_service.py
   input validation (canonical IDs), envelope, typed data-availability states → HTTP status
   │ enqueue                                   │ read results
   ▼                                           ▼
Job queue (jobs table) ◄── worker (ml.jobs.worker: claim → run → complete/fail; scheduler)
   ▼
ML package  ml/
   instruments/  canonical IDs · Instrument Master (search, seed, sync, manual NSE import) · capability profiles
   providers/    registry + capability matrix · router (legitimate fallback only) · http (rate limit, retry, circuit breaker, budget, call log)
                 upstox · alpha_vantage · binance · coingecko · frankfurter · ecb · fred · mfapi · amfi · openfigi · sec · synthetic_test (tests only)
   data/         db (SQLAlchemy Core tables) · store (portable upserts) · migrate (Alembic) · market_data (cache → provider → stale fallback)
                 validation (capability-aware) · calendars (exchange_calendars, 24/7, 24/5)
   features/ · fingerprint/ · anomaly/ · news/ (Alpha Vantage news, entity linking, FinBERT) · correlation/ · temporal/ · risk/ · evidence/
   pipelines/ intelligence · run · batch          jobs/ queue · worker          evaluation/ synthetic injection · FinBERT PhraseBank
   ▼
PostgreSQL 16 (Docker) or SQLite (local/tests) · FinBERT weights · MiniLM cache · model artefacts
```

## Layer rules

- **React = presentation.** All HTTP goes through `frontend/src/services/` (`apiClient`, `intelligenceApi`, `newsApi`); response types are in `frontend/src/types/api.ts`. Currency, timezone and value kind come from the API. The UI has no hard-coded instruments, prices or fallback values.
- **Flask = orchestration.** No model logic in routes. Every error has a machine-readable `code`; data-availability states (`INSTRUMENT_NOT_FOUND`, `NO_PROVIDER_FOR_ASSET`, `PROVIDER_UNAVAILABLE`, `RATE_LIMITED`, `INSUFFICIENT_HISTORY`, `INSUFFICIENT_SOURCE_DATA`) carry the provider `attempts`.
- **ML = intelligence, provider-agnostic.** Pipelines take a canonical instrument ID. Provider symbols exist only in `ml/providers/` and the `provider_symbols` table.

## Identity

Canonical ID = `NAMESPACE:CODE` (`ml/instruments/ids.py`, validated with a strict pattern; unsafe input is rejected with `INVALID_INSTRUMENT_ID`).

- Namespaces are exchange MICs (`XNSE`, `XBOM`, `XNAS`, `XNYS`, `ARCX`, `XASE`, `BATS`, `OTCM`) plus `IDX`, `FX`, `CRYPTO`, `MF-IN`, `RATE`, `CMDTY`, and `TEST` (tests only).
- A bare v0.1 symbol (`RELIANCE`) resolves to `XNSE:RELIANCE`.

## Request flow — `GET /api/intelligence/CRYPTO:BTC-USDT`

1. `intelligence_service.get_intelligence` checks the ID is in the Instrument Master (404 otherwise, so unknown IDs are never queued).
2. It then returns one of three things:
   - a stored run younger than 15 minutes;
   - a typed failure, if the last analysis job failed within 10 minutes;
   - `202 {status, job, previous_result}` after enqueueing `analyze` (deduplicated per instrument).
3. The worker (`AVENTRA_JOB_MODE=external`; in-process threads when `inline`) runs `run_intelligence`:
   - **Data:** resolve the instrument → capability profile → `load_series` (6-hour database cache → router → provider → stale stored data on failure) → validation → benchmark.
   - **Detection:** feature set chosen from capabilities → features → fingerprint → detectors (Isolation Forest artefact reused when still valid) → ensemble → change points.
   - **News:** news ingest (a permitted provider or `unavailable` with the reason).
   - **Per flagged observation:** correlation → risk → evidence → explanation.
   - The result is persisted: `analysis_runs`, `fingerprints`, `anomalies`, `events`, `risks`, `evidence`.
4. The UI polls `GET /api/jobs/<id>` every 2 s (for up to 180 s), then fetches the result.

Measured cold analyses in Docker on 2026-09-27: 2–4 s for Binance, Frankfurter and mfapi instruments, excluding the one-off model load.

## Storage

The schema is in `ml/data/db.py`; migrations are in `backend/migrations/versions/0001–0004`, applied on API start.

| Group | Tables |
|---|---|
| Instruments | `instruments` (search text, popularity), `instrument_aliases`, `provider_symbols`, `listing_snapshots` |
| Provider log | `provider_calls` (budget and health) |
| Market data | `prices` (keyed by instrument, interval, timestamp and provider; each row keeps currency, timezone, adjustment, quality and retrieval time) |
| News | `news`, `news_links`, `sentiment` |
| Results | `analysis_runs`, `fingerprints`, `anomalies`, `events`, `risks`, `evidence` (with provenance JSON) |
| Operations | `jobs`, `watchlists` |

Migration `0001` renames v0.1 tables to `legacy_*`. `0003` imports their prices, news and sentiment under `XNSE:` IDs, marking prices `quality='legacy'` and skipping the synthetic DEMO data. Rows from removed providers (Yahoo, Google News RSS) are excluded from production reads.

## Background processing

- The queue is a PostgreSQL table: `FOR UPDATE SKIP LOCKED` on Postgres, a single-writer claim on SQLite. There is no Redis.
- Jobs support dedupe keys, priorities, exponential-backoff retries, a maximum number of attempts and recovery of stale running jobs.
- Missing credentials and typed "not found / insufficient" states are not retried. A failed job stores its typed code and provider attempts. An unexpected error is stored as `INTERNAL_ERROR` without internals; the detail goes to the worker log.
- The scheduler, every 10 minutes:
  - syncs listings when older than 24 h;
  - enqueues one daily analysis for each watchlist instrument and each instrument analysed in the last 7 days.

## Frontend routes (manual router in `App.tsx`)

- `/`: landing page with the watchlist market monitor and the intelligence preview.
- `/intelligence?id=<canonical id>`: the dashboard. It accepts `?symbol=` for v0.1 links and shows a search prompt when no ID is given.
- `/behavioural-fingerprint`, `/anomaly-detection`, `/event-correlation`, `/risk-evidence`: capability pages.
- `/news-analysis`: FinBERT text analysis.

The global search is in the navbar, the workspace and the empty states.

## Key decisions (full list in AGENTS.md §32)

- Daily observations for analytics. Timestamps are stored in UTC.
- Session logic uses exchange_calendars. There is no XNSE calendar, so NSE uses XBOM as a proxy. Historical sessions come from observed bars.
- A feature set per capability profile: `ohlcv`, `ohlcv_continuous` (24/7 and 24/5, no opening gap), `close_volume`, `close`, `yield`. Versions for the feature set, fingerprint and thresholds are recorded in each result.
- Production ensemble = statistical + fingerprint + Isolation Forest. LOF, the LSTM autoencoder and change points are experimental or annotation only.
- No production synthetic data. `TEST:DEMO` exists only when `AVENTRA_ENABLE_SYNTHETIC_TEST_DATA=1`.
