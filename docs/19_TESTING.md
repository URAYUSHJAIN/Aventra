# 19 — Testing

All automated suites run offline:
- Providers are mocked or replaced by the synthetic `TEST:DEMO` instrument. It exists only when `AVENTRA_ENABLE_SYNTHETIC_TEST_DATA=1`, which the tests set themselves.
- FinBERT is mocked or forced unavailable wherever a test does not need it.
- Each test uses a temporary SQLite database, migrated with Alembic.

| Suite | Command (repo root unless noted) | Covers |
|---|---|---|
| ML | `py -3.12 -m unittest discover -s ml/tests -t .` | See the ML coverage list below. |
| Backend API | `py -3.12 -m unittest discover -s backend/tests -t .` | See the backend coverage list below. |
| Frontend | `cd frontend && npm test` | See the frontend coverage list below. |
| Types / lint / build | `cd frontend && npm run typecheck && npm run lint && npm run build` | `vite build` does not type-check, so `typecheck` is the gate. |
| PostgreSQL (optional) | set `AVENTRA_TEST_DATABASE_URL=postgresql+psycopg://…` to a disposable database, then run the ML suite | duplicate-key upserts against real PostgreSQL (skipped otherwise) |

**ML suite covers:**
- **IDs:** canonical ID parsing and rejection of unsafe input.
- **Database and migrations:** Alembic migrations from scratch and from a v0.1 database (legacy import, demo data skipped); store round-trips; duplicate-key upserts.
- **Instrument Master:** search ranking, filters, pagination and SQL-injection input; manual NSE import (classification, rejected files).
- **Providers:** adapters with recorded responses; router fallback and typed states; rate limiter, retries, circuit breaker and budget.
- **Data:** capability-aware validation; calendars and sessions.
- **Features and ML:** hand-computed features; **leakage** (future rows cannot change past features or fingerprints); feature-set selection (including `ohlcv_continuous`); fingerprint guarded update; detectors and ensemble.
- **News to evidence:** news provider states and entity linking; correlation and risk decomposition; evidence provenance.
- **Evaluation and pipeline:** evaluation helpers; the end-to-end `TEST:DEMO` pipeline.

**Backend suite covers:**
- **Validation and errors:** health; invalid IDs (400); unknown instruments (404, never queued); typed data-availability states with provider attempts.
- **Endpoints:** search and instrument endpoints; snapshots with per-item states; every intelligence, anomaly, event, risk and evidence endpoint (sync mode); `/api/news/analyze` backward compatibility.
- **Job queue:** dedupe, exclusive claim, backoff, stale recovery, missing credentials not retried, unexpected errors stored as `INTERNAL_ERROR` without internals.
- **Asynchronous API:** 202 → job → result.

**Frontend suite covers:**
- **API client:** envelope handling; typed codes and attempts; no retry of typed states; backend unavailable plus retry.
- **Analysis polling:** job polling for queued analyses.
- **Search:** debounce, keyboard selection, class badges, empty, empty-master and error states.
- **Dashboard:** loading → every panel from the API; the search prompt when no ID is given; the "Data unavailable / insufficient source data" state with provider attempts; no retry for unknown instruments; backend unavailable → retry.
- **Other pages:** capability page; NewsAnalysis.
- **Formatting:** currency, yield and basis-point formatting.

## Results on 2026-09-27

- ML: 73 tests, OK (1 skipped: PostgreSQL variant).
- Backend: 25 tests, OK.
- Frontend: 23 tests, OK; typecheck, lint and build clean.
- PostgreSQL variant run against a disposable `postgres:16-alpine` container: OK.

## Manual and integration verification (2026-09-27)

- **Local stack.** Flask with SQLite and Vite, with the Instrument Master synced from live keyless listings (68,596 instruments). A headless browser checked:
  - `/intelligence?id=CRYPTO:BTC-USDT` (`ohlcv_continuous`), `MF-IN:135762` (NAV, "Volume n/a") and `FX:USDINR`;
  - `XNAS:AAPL` without a key: "Data unavailable / insufficient source data" with the Alpha Vantage `missing_credentials` attempt;
  - `XNAS:NOTREAL`: "Instrument not found", with no retry offered;
  - the homepage watchlist monitor, and search at 1280×900 and 390×844 (no horizontal overflow).
- **Docker stack** (`docker compose up --build`; postgres, backend, worker, frontend):
  - migrations applied on PostgreSQL;
  - the worker synced 68,606 instruments;
  - scheduled analyses of the watchlist completed for BTC-USDT, USDINR and MF-IN:122639;
  - AAPL returned 503 `PROVIDER_UNAVAILABLE` with its attempts;
  - the UI was served through nginx.
- **Bug found and fixed.** The first Docker run exposed a PostgreSQL-only upsert error (duplicate keys in one listing batch). It is fixed, with a regression test.
