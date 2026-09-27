# Aventra Agent Instructions

Repository-wide rules for any coding agent (Claude Code, Codex, Cursor, Copilot, etc.) working on Aventra.
Claude Code additionally follows [CLAUDE.md](CLAUDE.md), which adds a mandatory workflow on top of these rules.

Last verified against the repository: **2026-09-27**, after the full-system implementation pass (commit `3705a83` + uncommitted implementation; see §7).
If you find this file out of date with the repository, the repository wins — then fix this file (see §28).

---

## 1. Project identity

- **Name:** Aventra
- **Tagline:** *Detect Hidden Patterns. Understand Market Risk.*
- **Type:** B.Tech final-year research & development project, ABES Engineering College, Ghaziabad, India.
- **One-sentence definition (use consistently in code comments, README, UI copy, docs):**
  > Aventra is an explainable financial-intelligence pipeline that combines adaptive behavioural profiling, anomaly detection, financial-news sentiment and cross-source temporal correlation to contextualize unusual market behaviour.
- **Market scope in the current code:** any instrument in the Instrument Master (equities, ETFs, REITs, InvITs, bonds, indices, mutual funds, forex, crypto, rates), identified by canonical IDs such as `XNAS:AAPL`, `XNSE:RELIANCE`, `CRYPTO:BTC-USDT`. Analysis is claimed only where a permitted provider supplies real data (docs/06 §0).

## 2. Project purpose

Aventra detects unusual market behaviour for an asset, finds relevant financial news, measures its sentiment, correlates the signals in time, and produces a transparent risk signal with an evidence chain explaining **what happened, how unusual it was, what else happened at the same time, and why it was flagged**.

Aventra is **not**: a price predictor, trading bot, buy/sell recommender, portfolio manager, chatbot, fake-news detector, AI-generated-text detector, fraud detector, or market-manipulation detector. Do not add those features (see Final Implementation Plan §33 and ML Pipeline §64).

## 3. Technology stack

| Layer | Actually in the repo | Planned / not present |
|---|---|---|
| Frontend | React 19, TypeScript (strict), Vite 8, Tailwind CSS v4 via `@tailwindcss/vite`, `lucide-react`; dev: vitest 5, @testing-library/react, jsdom. `three` + `@types/three` are in `package.json` but **unused** (C14) | React Router, chart library (both deliberately not added — C9, C15) |
| Styling | `styles/index.css` (original) + `styles/intelligence.css` (dashboard, search, badges, states; same palette) | — |
| Backend | Python 3.12, Flask 3, Flask-Cors, requests, SQLAlchemy 2 (Core), Alembic, psycopg 3; gunicorn in Docker | Pydantic/Marshmallow (C16) |
| ML | pandas, NumPy (<2), scikit-learn (Isolation Forest, LOF), PyTorch (<2.5; FinBERT + experimental LSTM-AE), Transformers (<4.41), sentence-transformers (MiniLM), ruptures (PELT), exchange_calendars, NLTK | SHAP, LightGBM/XGBoost (no labelled risk data yet) |
| Data | Instrument Master (~68,600 instruments from permitted listings); providers in `ml/providers/` (Upstox, Alpha Vantage, Binance, CoinGecko, Frankfurter, ECB, FRED, AMFI, mfapi, OpenFIGI, SEC); PostgreSQL (Docker) or SQLite (local/tests); `data/reference/` seeds; synthetic `data/demo/` for tests only | Parquet feature store |
| Jobs | PostgreSQL/SQLite `jobs` table (`FOR UPDATE SKIP LOCKED`), `ml/jobs/worker.py` (worker + scheduler) | Redis/Celery (deliberately not used) |
| Deploy | Docker Compose (`postgres`, `backend`, `worker`, `frontend`), `docker/`, `frontend/vercel.json` | CI |

Do not add a dependency that duplicates one already listed (e.g., a second icon set, a second HTTP client, a second chart library).

## 4. Repository structure (actual, 2026-09-27)

```text
Aventra/
├── AGENTS.md, CLAUDE.md          agent instructions (this file + Claude-specific)
├── readme.md                     project README (lowercase filename; current)
├── .gitignore, .dockerignore, .env.example, docker-compose.yml
├── context/                      MASTER DOCUMENTS (read-only for agents unless asked) — untracked in git
├── docs/                         engineering docs (04 architecture, 05 ML, 06 providers, 14 API, 17 evaluation, 19 testing, 21 deployment, 25 limitations)
├── docker/                       backend.Dockerfile (API + worker image), frontend.Dockerfile, nginx.conf
├── scripts/                      verify_providers.py (Phase 0 evidence), generate_demo_data.py (synthetic TEST fixtures)
├── data/
│   ├── reference/                assets.json (seed + aliases), provider_verification.json (Phase 0 evidence)
│   ├── demo/                     SYNTHETIC fixtures for automated tests only (TEST:DEMO); not in the Docker image
│   └── aventra.sqlite3, processed/, raw/, external/   generated, git-ignored
├── artifacts/                    trained model artefacts (git-ignored)
├── experiments/results/          EXP-01 (v0.1, Yahoo-era), EXP-02, EXP-03 records (JSON + Markdown, committed)
├── ml/
│   ├── config.py                 thresholds/weights/windows (uncalibrated defaults), env reads
│   ├── instruments/              ids (canonical IDs), profiles (capabilities per class), master (search, seed, manual NSE import), sync (listing CLI)
│   ├── providers/                base, http (rate limit/retry/circuit/budget/log), registry (router), upstox, alpha_vantage, crypto, reference_rates, funds_and_reference, synthetic_test
│   ├── data/                     db (tables), store (upserts/reads), migrate (Alembic), market_data, validation, calendars, sessions, cache
│   ├── features/                 engineering (past-only), sets (feature sets + versions)
│   ├── fingerprint/, anomaly/, news/ (Alpha Vantage news, FinBERT, entity, events, ingest), correlation/, temporal/, risk/, evidence/
│   ├── pipelines/                intelligence (orchestrator), run, batch, artifacts
│   ├── jobs/                     queue, worker (handlers, scheduler, CLI)
│   ├── evaluation/               synthetic injection, run_experiments (EXP-03), finbert_phrasebank (EXP-02)
│   └── tests/                    73 unittest cases (1 PostgreSQL-only, skipped without AVENTRA_TEST_DATABASE_URL)
├── backend/
│   ├── app.py                    app factory; runs migrations; typed error handlers; /api/health
│   ├── routes/                   instrument_routes, market_routes, intelligence_routes, news_routes
│   ├── services/                 market_service, intelligence_service (job modes), news_analysis_service (re-export of ml.news.finbert)
│   ├── utils/responses.py        envelope, ApiError(code), instrument-ID/int/choice validation
│   ├── migrations/, alembic.ini  Alembic 0001–0004
│   ├── models/finbert/           FinBERT weights (438 MB, git-ignored)
│   └── tests/                    25 tests (news routes, API routes, jobs)
└── frontend/
    ├── vite.config.ts            dev proxy /api → AVENTRA_API_PROXY or 127.0.0.1:5000
    ├── vitest.config.ts, eslint.config.js
    └── src/
        ├── App.tsx               manual routing + per-route metadata
        ├── services/             apiClient (envelope, typed ApiError code/attempts), intelligenceApi (search, snapshots, watchlist, job polling), newsApi
        ├── types/api.ts          response types mirroring the backend
        ├── hooks/useApiResource.ts, utils/format.ts (currency/timezone/value-kind aware)
        ├── pages/                Home, IntelligencePage, CapabilityPage, NewsAnalysisPage, NotFoundPage (+ pages.test.tsx)
        ├── components/search/    GlobalSearch (+ test)
        ├── components/intelligence/  IntelligenceWorkspace, panels, LineChart, StateViews (DataUnavailableState)
        ├── components/home/      …, LiveMarketData (watchlist + snapshots), IntelligencePreview
        └── test/                 fetchMock, fixtures/intelligence-demo.json (TEST:DEMO pipeline output)
```

Still absent: CI, LICENSE. `App.css`, `react.svg`, `vite.svg`, and the `.demo-visual`/`.neural-*` CSS rules are unused.

## 5. Source-of-truth documents and hierarchy

| Rank | Source | Authority over |
|---|---|---|
| 1 | **The actual repository state** (code, configs, git history) | What currently exists and works. |
| 2 | `context/Aventra_Final_Implementation_Plan.md` | Intended implementation direction, feature set, milestones, API list, scope control. |
| 3 | `context/AVENTRA_MASTER_ML_PIPELINE.md` | ML, data, feature engineering, evaluation, experimentation, reproducibility. |
| 4 | `context/Aventra_Design_Specification.md` | UI/UX, visual language, routes, homepage structure, motion, responsiveness. |
| 5 | `CLAUDE.md` | How Claude Code executes tasks. |
| 6 | `AGENTS.md` (this file) | General rules for all coding agents. |

Rules:
- Rank 1 answers "what exists". Ranks 2–4 answer "what should exist". Never describe planned things as existing.
- Within their own domain, rank 3 overrides rank 2 on ML/data details, and rank 4 overrides rank 2 on UI details.
- When documents contradict each other or the code, **do not silently pick one**. Check §32. If the conflict is not listed there, add it to §32 and ask the user before implementing anything that depends on the resolution.
- Treat `context/*.md` as read-only unless the user asks you to edit them.

## 6. Architecture overview

Target pipeline (conceptual order; each stage consumes the output of earlier stages):

```text
Market Data ─────────────────────────────┐        Financial News (parallel branch)
    ↓                                     │            ↓
Data Validation / Cleaning                │        Ingestion → Dedup → Entity/Ticker linking
    ↓                                     │            ↓
Temporal Alignment  ◄─────────────────────┼──────── FinBERT sentiment
    ↓                                     │
Feature Engineering                       │
    ↓                                     │
Behavioural Fingerprinting                │
    ↓                                     │
Anomaly Detection                         │
    ↓                                     │
Financial News Analysis (attach context) ◄┘
    ↓
Cross-Source Event Correlation (+ temporal / lead-lag analysis)
    ↓
Risk Scoring
    ↓
Evidence Chain / Explainability
    ↓
Flask API
    ↓
React + TypeScript Frontend
    ↓
Interactive Financial Intelligence Dashboard
```

News sentiment is computed on its own branch and joined at temporal alignment (as features) and at correlation (as context). Layer ownership (ML Pipeline §82):
- **ML package owns the intelligence.** Features, fingerprints, detectors, correlation, risk and evidence logic live in the ML package, not in Flask routes.
- **Flask is orchestration/API only.** Validation, calling services, serialising responses.
- **React is presentation only.** It never calls a market/news provider directly and never contains model logic.

## 7. Current implementation status

Legend: **REAL** = working code exists · **PARTIAL** = works only in some conditions or covers part of the scope · **KEY-GATED** = implemented, needs a provider key to return data · **EXPERIMENTAL** = evaluation only · **PLANNED** = nothing in the repo.

| Component | Status | Evidence in repo |
|---|---|---|
| Landing page, Navbar (with global search), Footer | REAL | `frontend/src/components/**` |
| Instrument Master + search (`/api/instruments/search`) | REAL | ~68,600 instruments synced from permitted listings; ranking, filters, cursor pagination |
| Canonical IDs + capability profiles | REAL | `ml/instruments/ids.py`, `profiles.py` (11 classes) |
| Provider registry / router / rate limits / circuit breaker / budget | REAL | `ml/providers/`; `GET /api/providers` |
| Market data: crypto, forex, Indian mutual funds | REAL (keyless) | Binance, CoinGecko, Frankfurter/ECB, AMFI + mfapi |
| Market data: US/BSE equities & ETFs, NSE equities/ETFs/REITs/InvITs/bonds/indices, rates | KEY-GATED | Alpha Vantage, Upstox, FRED; without keys → `PROVIDER_UNAVAILABLE` with attempts |
| Yahoo Finance, Google News RSS, automated NSE downloads | REMOVED | terms / robots.txt (docs/06, C22, C23); manual NSE import only |
| Validation, calendars, UTC alignment | REAL | `ml/data/validation.py` (capability-aware), `calendars.py` (XBOM = NSE proxy) |
| Feature sets + versions | REAL | `ml/features/sets.py` (`ohlcv`, `ohlcv_continuous`, `close_volume`, `close`, `yield`) |
| Behavioural fingerprint | REAL | `ml/fingerprint/baseline.py` |
| Anomaly detection | REAL (statistical + fingerprint + IF ensemble); EXPERIMENTAL (LOF, LSTM-AE); retrospective PELT | `ml/anomaly/` |
| News + FinBERT + entity linking | KEY-GATED (Alpha Vantage NEWS_SENTIMENT: US tickers, crypto, forex); Indian instruments: no permitted source → `unavailable` | `ml/news/` |
| Correlation, temporal analysis, risk, evidence (with provenance) | REAL (uncalibrated weights) | `ml/correlation/`, `ml/temporal/`, `ml/risk/`, `ml/evidence/` |
| Database + migrations | REAL | PostgreSQL (Docker, verified) / SQLite; Alembic 0001–0004 (incl. v0.1 legacy import) |
| Background jobs (queue, worker, scheduler, async API 202 + polling) | REAL | `ml/jobs/`, `intelligence_service.py`, verified in Docker |
| Intelligence dashboard, capability pages, homepage monitor + preview | REAL | search-driven, `?id=`; typed unavailable states; dynamic currency/timezone |
| FinBERT text analysis `POST /api/news/analyze` + `/news-analysis` | REAL | unchanged contract; EXP-02 |
| Evaluation | PARTIAL | EXP-03 (13 real keyless instruments, per class), EXP-01 (v0.1 Yahoo-era record), EXP-02. Equities, known-event benchmark, correlation quality, risk calibration: PLANNED |
| Docker / Compose | REAL | Verified 2026-09-27: postgres + backend + worker + frontend; migrations, listing sync, scheduled analyses, nginx |
| Tests | REAL | ML 73 (1 PostgreSQL-only skipped by default), backend 25, frontend 23. CI: PLANNED |
| Synthetic data | TEST-ONLY | `TEST:DEMO` only with `AVENTRA_ENABLE_SYNTHETIC_TEST_DATA=1`; never a production fallback |
| Contact form | PARTIAL | `mailto:` only if `VITE_CONTACT_EMAIL` is set |

## 8. Core ML pipeline (target) — build order

Follow the Final Implementation Plan §29 order together with ML Pipeline §78. Do not start a later stage before the earlier one works on real (or demo) data and has tests:

1. Market provider adapter + validation + preprocessing + **deterministic demo dataset** (`data/demo/market.csv`, `news.json`, `sentiment.json`).
2. News provider adapter + dedup + entity/ticker mapping (store `entity_match_confidence`, `mapping_method`).
3. Reuse existing FinBERT for news sentiment (do **not** retrain first; do **not** reinstall or clone a second copy).
4. Feature engineering (price, volume, volatility, news, cross-source), **past-only windows**.
5. Behavioural fingerprint: rolling median/MAD + robust z-score → deviation score → guarded adaptive update (ML §18).
6. Anomaly detection: statistical baseline → Isolation Forest → LOF → change points (ruptures/PELT) → LSTM autoencoder (only after baselines work) → normalised ensemble.
7. Cross-source correlation: time window + ticker/entity match + semantic similarity (`all-MiniLM-L6-v2`) + event category (rules/zero-shot).
8. Temporal / lead-lag metadata (language: "temporally aligned", never "caused").
9. Transparent weighted risk score (configurable weights) → later trained model + SHAP.
10. Evidence chain (timestamp, signal, source, value, explanation, linked article).
11. `python -m ml.pipelines.run --symbol <SYM>` CLI and batch CLI (ML §54–55).

Required baselines for research comparison (ML §46): statistical → Isolation Forest → fingerprint+anomaly → fingerprint+anomaly+news correlation. Ablations per ML §47.

## 9. Backend architecture

Existing conventions (keep them):
- App factory `backend/app.py::create_app(test_config=None)`; blueprints registered with `url_prefix="/api/<area>"`.
- Absolute imports from the package root: `from backend.services... import ...`. Commands run **from the repo root**, e.g. `py -3.12 -m backend.app`.
- One blueprint per area in `backend/routes/<area>_routes.py`; business logic in `backend/services/<area>_service.py`.
- Heavy models are lazy-loaded once per process behind a lock (pattern in `news_analysis_service.py`). Reuse this pattern for any new model.
- Domain exceptions (e.g. `FinBertUnavailable`, `InvalidNewsText`) are raised by services and mapped to HTTP codes in routes.
- Config via `app.config` + environment variables (`CORS_ORIGINS`, `FINBERT_MODEL_PATH`, `MAX_NEWS_TEXT_LENGTH`).

When extending:
- Add new areas as new blueprints (`market_routes.py`, `fingerprint_routes.py`, …). Do **not** restructure into `backend/app/` + `run.py` (ML Pipeline §5) without explicit approval — see conflict C3.
- Put ML logic in the ML package (see C1); backend services call it. Never duplicate an algorithm in both places.
- Do not name ORM modules `backend/models/…` — that directory holds model weights. Use `backend/database/` for DB code (Final Plan §23 lists `database/` and `schemas/`).
- Centralise constants (windows, thresholds, weights) in one config module (ML §60). No magic numbers in routes/services.
- Add a caching layer (in-memory first) before calling external providers repeatedly (ML §40). No Redis until needed.

## 10. Frontend architecture

Existing conventions (keep them):
- Components are function components exporting a named function (`export function Hero()`), except `App` (default export).
- Network calls live only in `frontend/src/services/*.ts`. Components import typed functions (`analyzeNews`, `getMarketData`). Never put `fetch()` in a component.
- API base URL: `import.meta.env.VITE_API_BASE_URL ?? ''` (empty → Vite `/api` proxy in dev).
- Section components live in `components/home/`; shared primitives in `components/common/`; static content in `data/`.
- Page metadata (title/description/og tags) is set in `App.tsx` per path.
- Global styles live in `styles/index.css`. Match the existing class-based styling. Use Tailwind utilities only where the surrounding code already does.

When extending:
- Add feature folders per the Final Plan §21 (`components/dashboard/`, `fingerprint/`, `anomaly/`, `correlation/`, `risk/`, `market/`) and `types/`, `hooks/`, `utils/` **only when you add real content to them**.
- Put shared API response types in `frontend/src/types/` and mirror the backend JSON exactly. No `any`.
- Every API-driven component needs **loading, success, empty and error** states (ML §38). No blank panels.
- When real endpoints exist, replace placeholder visuals in `CapabilityDemoPage.tsx` with API-backed components. Keep the existing routes working (see C9).
- Introducing React Router is planned (both docs). When you do, keep every existing URL (`/news-analysis`, `/behavioural-fingerprint`, `/anomaly-detection`, `/event-correlation`, `/risk-evidence`, `/#section` anchors) working or redirecting, and keep the per-route metadata behaviour.
- Lazy-load heavy visual dependencies (`three`) with `React.lazy`/dynamic import so they don't block the first paint.

## 11. Data architecture

Current: SQLAlchemy Core schema in `ml/data/db.py` on PostgreSQL (Docker) or SQLite (local/tests), migrated with Alembic (`backend/migrations/`). Tables: `instruments, instrument_aliases, provider_symbols, listing_snapshots, provider_calls, prices, news, news_links, sentiment, analysis_runs, fingerprints, anomalies, events, risks, evidence, jobs, watchlists` (docs/04). Every price row records provider, currency, timezone, adjustment, quality and retrieval time. Identity is the canonical instrument ID, never a provider symbol.

Directory intent (create only when content exists):
- `data/raw/` — immutable provider downloads, with provenance (source, fetch time, parameters).
- `data/interim/`, `data/processed/`, `data/features/` — derived; must be reproducible from raw via code.
- `data/demo/` — deterministic, clearly labelled demo scenario (ML §56–57). Demo data must never be shown as live data.
- Large/raw data files are git-ignored. Commit small demo fixtures only.

For **every** data or ML change, explicitly check and handle:

| Concern | Rule |
|---|---|
| Missing values | Detect and report counts. Impute only with past data. Never forward-fill across a gap longer than the configured limit. |
| Duplicates | Deduplicate on `(instrument_id, interval, timestamp, provider)` for prices and on URL/normalised headline for news. Log how many were removed. |
| Outliers | Do **not** blindly delete. Distinguish a data error (negative price, high < low, zero volume on a trading bar) from a real market anomaly. A real extreme move is the thing Aventra detects. |
| Timestamps | Store in UTC with timezone awareness. Convert to the instrument's exchange timezone only for display/session logic. |
| Market sessions | Use the instrument's calendar (`ml/data/calendars.py`: exchange_calendars, XBOM as the NSE proxy, 24/7, 24/5). Historical sessions come from observed bars. Align news outside the session to the next session, and record that you did. |
| Leakage | Features at time *t* use only data < *t* (or ≤ *t* for the current bar's own value). No centred rolling windows. Scalers/detectors are fit on the training split only. |
| Inference availability | Use a feature only if it is available at inference time with the same definition. Training and inference share one feature function. |
| Splits | Chronological train/validation/test (e.g. 70/15/15). Never shuffle across time. |
| Class imbalance | Anomalies are rare. Report precision/recall/PR-AUC, not accuracy alone. |
| Provenance | Every stored row records its source and fetch time. Every model output records `model_name` and `model_version`. |

**Never fabricate financial data, news, sentiment or ML results.** If data is unavailable, return an explicit unavailable state (ML §66) — e.g. "News context unavailable", `status = insufficient_history` (ML §67).

## 12. API conventions

Existing contract (preserve it):
- Success: `200 {"success": true, "data": {...}}`
- Failure: `4xx/5xx {"success": false, "error": "<human-readable message>", "code": "<TYPED_CODE>", "attempts"?: [...]}` (docs/14)
- `POST /api/news/analyze` body `{"text": string}` (max 12,000 chars) → `data = {label, positive_probability, neutral_probability, negative_probability, sentiment_score}`. Consumer: `frontend/src/services/newsApi.ts` → `NewsAnalysis.tsx`.

Rules:
- Before changing any existing endpoint, `grep` the frontend for every consumer (`services/*.ts`, types, components). Only add fields. Do not rename, remove or retype fields without explicit approval. If a breaking change is approved, update the consumers in the same change.
- New endpoints follow the Final Plan §19 list, prefixed `/api/`. For path shapes that differ between the docs, see C5.
- Status codes: 400 invalid input/ID, 404 unknown resource/instrument, 413 payload too large, 422 no provider / insufficient history or data, 503 provider unavailable or rate-limited / local model unavailable, 202 analysis queued, 500 unexpected. Never return stack traces, SQL or internal paths.
- Validate every input at the route boundary: type, presence, length, canonical instrument ID (`require_instrument_id`).
- Timestamps in responses are ISO-8601 UTC strings.
- Every ML-derived value in a response carries its model name/version, plus a confidence value if the model produces a meaningful one. Label uncalibrated scores as "score", not "probability".
- Add an API test for every endpoint: valid request, missing input, invalid input, upstream/model failure.

## 13. ML / model conventions

Priorities, in order: **reproducibility, no leakage, temporal correctness, explainability, baseline comparison, suitable metrics, versioning, train/inference feature consistency, robust error handling, local execution.**

- Keep experiments (`notebooks/`, `experiments/`) separate from production inference code (ML package). Notebooks must not be imported by the app.
- Seeds: `random_state=42` (or a configured seed) wherever supported. Record it.
- Every experiment records: ID, objective, dataset + date range, features, model, parameters, seed, split boundaries, metrics, interpretation, limitations (ML §41, §61). Save the results to disk. Do not keep them only in chat.
- Save trained artefacts with metadata: `model_name, model_version, training_date, dataset_version, parameters, feature_list` (ML §59). Gitignore the binaries.
- Normalise all detector scores to a documented range before combining. Ensemble weights and severity/risk bands are **configurable defaults, not validated thresholds** until calibrated on validation data. Say so in code comments and UI copy.
- Add deep models (LSTM-AE, etc.) only after the statistical and Isolation Forest baselines work and are evaluated. Advanced models are experiments. Never replace a working baseline without evidence.
- FinBERT:
  - Reuse `ml/news/finbert.py` (`get_news_analysis_service()`, also re-exported from `backend/services/news_analysis_service.py`) and `backend/models/finbert/`. Do not download or clone a second copy.
  - The label order is positive=0, negative=1, neutral=2 (verified in `config.json`).
  - Inputs are truncated at 64 tokens per sentence. This is a known limitation.
  - It is a **sentiment** model only (Final Plan §8).
  - The ProsusAI FinBERT was fine-tuned on Financial PhraseBank. Evaluating it on PhraseBank therefore overlaps with its training data, and any report must state this (see §29).
- Language: never "predicts", "will fall", "caused", "guaranteed", "100% accurate". Use "associated with", "temporally aligned", "unusual", "elevated risk signal" (ML §68–69).

## 14. Testing requirements

Current commands:
- ML (from repo root): `py -3.12 -m unittest discover -s ml/tests -t .` (offline; includes leakage tests and an end-to-end demo run).
- Backend (from repo root): `py -3.12 -m unittest discover -s backend/tests -t .`. New modules follow `backend/tests/test_<area>.py`. Providers and FinBERT are mocked.
- Frontend (from `frontend/`): `npm test` (vitest + jsdom), `npm run typecheck`, `npm run lint`, `npm run build`. **`build` does not type-check.** `npm run lint` ignores `.ts/.tsx` (C12), so a passing lint is not evidence of TS quality.
- Optional PostgreSQL check: set `AVENTRA_TEST_DATABASE_URL` to a disposable database before running the ML suite.
- Experiments (not tests; they write `experiments/results/`): `py -3.12 -m ml.evaluation.run_experiments --instruments ...`, `py -3.12 -m ml.evaluation.finbert_phrasebank`.

Required for every change:
- **Backend:** tests for valid input, empty/missing input, invalid JSON/type, model-loading failure, inference failure and upstream-provider failure (Final Plan §24).
- **ML:** unit tests for each feature calculation (use hand-computed expected values on small fixtures), fingerprint deviation, detector score normalisation, ensemble, correlation scoring, risk calculation and evidence construction. Add a **leakage test**: shifting or removing future rows must not change a past feature value.
- **Integration:** data → ML → Flask (test client) with the demo dataset, no network.
- **Frontend:** once a test runner is added, cover loading, success, empty, API-error and backend-unavailable states. Until then, verify these manually and report that you did it manually.
- Tests must not call live external APIs. Mock the providers or use the synthetic `TEST:DEMO` instrument (tests set `AVENTRA_ENABLE_SYNTHETIC_TEST_DATA=1` themselves).
- Never delete, skip or weaken a test to make it pass. Never mock the thing under test.

## 15. Security requirements

- No secrets in code, tests, docs or commits. Read them from `.env` (git-ignored); document every variable in the matching `.env.example`.
- `VITE_*` variables are public (they ship in the browser bundle). Never put API keys in them. Provider keys stay server-side in Flask.
- Keep `CORS_ORIGINS` explicit in any deployed environment. `*` is for local development only.
- Validate and length-limit all inputs. Treat news text/HTML as untrusted: strip HTML server-side and never render it with `dangerouslySetInnerHTML`.
- Do not expose model paths, file-system paths, DB URLs or stack traces in API responses.
- `app.run(debug=True)` in `backend/app.py` is for local development only. Deployments must use a WSGI server (e.g. gunicorn) with debug off.
- Respect provider terms/rate limits. Do not add brittle scraping unless the user explicitly asks for it (ML §7).

## 16. Performance requirements

- Load FinBERT (and any other model) once per process, lazily, thread-safe. Never load a model per request.
- Batch inference where possible (the existing service already batches sentences).
- Cache provider responses. Do not poll external providers more often than their data updates. The existing UI polls quotes every 60 s — do not lower that.
- Frontend: keep the initial bundle small. Lazy-load `three` and chart libraries. Cancel `requestAnimationFrame` loops and intervals on unmount. Pause decorative animation when off-screen or when `prefers-reduced-motion` is set.
- Measure and record ML inference time and API latency when adding ML endpoints (ML §48). Do not claim performance numbers you did not measure.

## 17. Error-handling requirements

- Every failure scenario in ML §66 must be handled explicitly: no market data, no news, FinBERT unavailable, invalid symbol, missing timestamps, duplicate news, provider timeout, rate limit, model failure, empty feature set, insufficient history.
- Partial degradation is fine and must be visible. If news fails, still return the market anomaly with `news: {status: "unavailable"}`, and the UI must say "News context unavailable".
- Never substitute fabricated or random data on failure. Return a typed state ("Data unavailable / insufficient source data" + `code` + provider `attempts`). Synthetic data is never a production fallback.
- Services raise typed domain exceptions. Routes map them to status codes (see §12). Unexpected exceptions are logged with `logger.exception` and returned as a generic 500 message.
- Frontend service functions throw `Error` with a user-readable message. Components render it in a `role="alert"` element.

## 18. Logging requirements

- Backend uses the `logging` module (`logger = logging.getLogger(__name__)`). No `print` in application code.
- Each pipeline stage logs: module, symbol, operation, status, duration and error if any (ML §51).
- Never log secrets, full article bodies, request bodies with user text, or credentials. Log counts and IDs instead.
- Log data-quality events: rows dropped, duplicates removed, gaps found.
- No leftover `console.log` in committed frontend code.

## 19. Environment-variable rules

All backend variables are listed, with comments, in the root `.env.example` (the single reference). Summary:

| Variable | Where | Purpose |
|---|---|---|
| `ALPHAVANTAGE_API_KEY`, `UPSTOX_ACCESS_TOKEN`, `FRED_API_KEY` | backend | Provider credentials (optional; missing → `PROVIDER_UNAVAILABLE`) |
| `COINGECKO_DEMO_API_KEY`, `OPENFIGI_API_KEY` | backend | Optional higher limits |
| `AVENTRA_ALPHAVANTAGE_DAILY_BUDGET` | backend | Alpha Vantage daily request budget (default 25) |
| `AVENTRA_SEC_USER_AGENT` | backend | SEC fair-access User-Agent with a real contact |
| `AVENTRA_DATABASE_URL` / `AVENTRA_DB_PATH` | backend | PostgreSQL URL, else SQLite file |
| `AVENTRA_JOB_MODE`, `AVENTRA_INLINE_JOB_THREADS`, `AVENTRA_WORKER_POLL_SECONDS` | backend | `inline` (default, local) / `external` (Docker worker) / `sync` (tests) |
| `AVENTRA_DEFAULT_WATCHLIST` | backend | Canonical IDs for the home page and scheduled analysis (empty by default) |
| `AVENTRA_ENABLE_SYNTHETIC_TEST_DATA` | backend | Tests only; enables `TEST:DEMO` |
| `FINBERT_MODEL_PATH`, `CORS_ORIGINS`, `AVENTRA_ARTIFACT_DIR`, `AVENTRA_DATA_DIR`, `AVENTRA_ANOMALY_THRESHOLD`, `AVENTRA_SEMANTIC_MODEL`, `PORT`, `FLASK_DEBUG` | backend | Paths, CORS, pipeline settings, dev server |
| `POSTGRES_PASSWORD` (required), `POSTGRES_USER`, `POSTGRES_DB`, `FRONTEND_PORT`, `BACKEND_PORT`, `FINBERT_HOST_PATH` | Docker Compose | Stack configuration |
| `VITE_API_BASE_URL`, `VITE_CONTACT_EMAIL` | frontend | Public build-time values (never secrets) |
| `AVENTRA_API_PROXY` | frontend dev server | Vite `/api` proxy target |

Rules:
- Every new variable goes into the relevant `.env.example` with a comment and a safe default, in the same change.
- Read env vars in one config module per side where possible. Do not scatter `os.getenv` or `import.meta.env` calls.
- The app must start with no `.env` present (sensible defaults, or a clear error for truly required values such as `POSTGRES_PASSWORD` in Compose).

## 20. Docker / deployment rules

- Implemented and verified (2026-09-27): `docker compose up --build` starts:
  - `postgres` (16-alpine, no host port, volume `aventra-pg`);
  - `backend` (Flask + ML, gunicorn **1 worker** × 8 threads because FinBERT lives in the process; applies migrations on start; `AVENTRA_JOB_MODE=external`);
  - `worker` (same image, `python -m ml.jobs.worker`; listing sync + scheduled watchlist analysis);
  - `frontend` (nginx + Vite build, proxies `/api`).
- Artefacts and the Hugging Face cache live on `aventra-state`. Do not create one container per model or other microservices. Files: `docker/`, `docker-compose.yml`, `.dockerignore`.
- `POSTGRES_PASSWORD` has no committed default; Compose refuses to start without it.
- The backend image does not contain `data/demo` (synthetic fixtures are test-only).
- Do not bake the 438 MB FinBERT weights into git or the image. Mount them and point `FINBERT_MODEL_PATH` at them.
- Vercel serves only the static frontend; it needs `VITE_API_BASE_URL` and a hosted backend + database + worker. Keep `vercel.json` working.
- The Docker setup must run on a clean machine with only documented steps. Verify this before calling Docker work done.

## 21. UI/UX rules

Authority: `context/Aventra_Design_Specification.md`.
- Product feel: "a serious financial intelligence product that happens to use AI". Dark financial terminal, restrained 3D depth.
- Colour roles: **orange** = primary actions and highlights, **cyan** = technical labels and active states, **white** = main content, **grey** = secondary content. Existing tokens in `index.css`: bg `#101B20`, surface `#1B2A30`, text `#F5F7F8`/`#AAB4B8`, cyan `#62D6D0`/`#72E6E0`, orange `#F5A623`/`#FFB52E`, border `#304148`. The spec proposes a slightly different palette (C10). Do not mass-recolour without approval.
- Fonts: Manrope (UI) + DM Mono (technical labels), already loaded. Do not add fonts.
- Avoid generic AI/robot imagery, excess neon/glow, particle backgrounds, heavy glassmorphism, random decorative animation, overcrowded cards and stock imagery.
- Motion: fade, slide, small scale, subtle parallax, slow 3D hover. No bouncing, spinning cards, scroll hijacking or constant background animation. Honour `prefers-reduced-motion: reduce` for every decorative animation.
- Every visible link and button must lead to a real destination. No dead `#` links.
- Do not redesign or replace working components for stylistic preference. Implement design-spec changes only when a task asks for them. Change the named component and keep the rest intact.
- UI copy must not claim live data, detection or scores that the backend doesn't produce. Label illustrative visuals as illustrative.

## 22. Responsive-design rules

- Primary desktop test sizes: 1440×900, 1366×768, 1280×720. Also check tablet (~768–900 px) and mobile (360–420 px); the existing CSS breakpoints are 900, 800, 700, 600, 560 and 420 px.
- Sections use `min-height: 100svh`. Never clip content to force one screen. Hero CTAs must stay above the fold on 1280×720.
- No horizontal page scroll at any width (the root uses `overflow-x: clip`; do not rely on it to hide overflowing components).
- Mobile: single column, smaller type, reduced 3D depth, vertical timelines, hero order heading → description → CTA → visual.
- The existing CSS softens scroll-snap on mobile (`proximity`). Keep that.

## 23. Accessibility expectations

- Semantic landmarks (`nav`, `main`, `section`, `footer`), one `h1` per page, logical heading order.
- All interactive elements are real `<button>`/`<a>` with a visible `:focus-visible` style (existing pattern: 2px cyan outline).
- Icon-only buttons have `aria-label`. Decorative images use `alt=""`. Meaningful images have a descriptive `alt`.
- Form fields have labels. Errors use `role="alert"`, async status uses `role="status"` / `aria-live` (see `NewsAnalysis.tsx`).
- Charts need a text alternative (`role="img"` + `aria-label`, or a visually hidden summary/table).
- Do not convey gain/loss by colour alone. Keep the `+`/`−` sign.
- Contrast: body text ≥ 4.5:1 against its background.
- Canvas/3D content (three.js) is decorative. Provide the same information as accessible text.

## 24. Git / change-management rules

- Default branch `main`; multi-asset work is on `feat/multi-asset-platform`. **Create a feature branch before committing** (`feat/…`, `fix/…`, `docs/…`).
- Commit or push only when the user asks. Never force-push. Never rewrite history on `main`.
- One logical change per commit. Commit messages use the existing style `feat: …`, `fix: …`, `docs: …`.
- Do not commit: `.env`, model weights (`backend/models/finbert/`), `node_modules/`, `frontend/dist/`, `__pycache__/`, raw data dumps, or experiment binaries.
- The working tree may contain the user's uncommitted work (currently `three`/`@types/three` in `package.json` + lock, `.neural-*` CSS in `index.css`, the untracked `context/` folder, and `AGENTS.md`/`CLAUDE.md`; run `git status` for the live list). Never discard, stash, reset or overwrite it without asking.
- If `package.json` changes, update `package-lock.json` in the same change via `npm install`, never by hand.

## 25. Rules for modifying existing code

1. Read the whole file and all its callers first (`Grep` the symbol across `frontend/src` and `backend/`).
2. Assume existing code is intentional and working until you have shown otherwise. "Cleaner architecture in the docs" is not enough reason to rewrite it.
3. Make the smallest change that meets the requirement. Do not reformat, rename or restructure unrelated code in the same change.
4. Match the local style. Many existing frontend files are dense one-line components — edit them in the same style, and do not reflow a whole file to make a small edit.
5. Keep public contracts stable: API JSON shapes, exported component names/props, URLs and env-var names.
6. Before removing code, confirm it has no consumers. State why it is being removed in the change report. Known dead code: `App.css`, `react.svg`, `vite.svg`. Only remove these when asked.
7. Replacing placeholders with real data is expected work. Keep the visual design, swap the data source, and add loading, empty and error states.

## 26. Rules for adding new features

1. Check whether it already exists. Search routes, services, components, `data/` and `services/`, and read §7. Extend the existing code if it does.
2. Check that it is in scope (§2, Final Plan §33). If it is out of scope, stop and ask.
3. Locate it in the pipeline (§6) and confirm the stages it depends on exist. If they don't, build those first or use the demo dataset. Never fake an upstream stage.
4. Define the contract first: backend response schema, then TS type, then service function, then component.
5. Put logic in the right layer (ML package / Flask / React).
6. Put constants in config and new variables in `.env.example`.
7. Add tests at the same time as the code.
8. Update docs and the status table in §7.

## 27. Rules for debugging

1. Reproduce first. Record the exact command, input, and observed vs expected output.
2. Find the failing layer by checking each boundary in turn: provider → service → route (Flask test client / curl) → `services/*.ts` → component.
3. Read logs and actual error messages before forming a hypothesis. Fix the root cause.
4. Never "fix" a bug by swallowing exceptions, disabling validation, loosening types to `any`, hard-coding expected outputs, or skipping tests.
5. Add a regression test that fails before the fix and passes after it.
6. Known pitfalls:
   - Vite proxies only exist in `npm run dev`.
   - Backend imports need the repo root as the working directory.
   - FinBERT needs the local weights folder.
   - NLTK `punkt` may be missing; the code falls back to a regex splitter.
   - Providers without credentials report `PROVIDER_UNAVAILABLE` by design; check `/api/providers` before debugging "missing" data.
   - Behaviour that passes on SQLite can fail on PostgreSQL (e.g. duplicate conflict keys in one upsert). Run the PostgreSQL test variant for store changes.

## 28. Rules for documentation

- Engineering docs live in `docs/` (see docs/README.md). Candidate additional files: ML §77.
- Update docs in the same change as the code when you change architecture, endpoints, env vars, setup steps, data schema or model behaviour.
- Keep §7 of this file accurate. When a component changes status, update its row.
- `readme.md` is current (2026-09-27). Do not rename it to `README.md` without asking, because the case-only rename is fragile on Windows/OneDrive.
- In documentation, clearly separate: *implemented*, *planned*, *assumption* and *experimental result*.

## 29. Academic / research integrity requirements

Aventra is assessed academic work. Everything written must keep these categories distinct and labelled: **existing literature · existing implementation · proposed methodology · experimental results · assumptions · future work**.

Never invent, estimate or "fill in":
- accuracy, precision, recall, F1, AUC, PR-AUC, latency or any other metric
- dataset sizes, date ranges or counts
- research results or benchmark comparisons
- citations, papers, authors, DOIs or URLs you have not verified
- patent claims, patent numbers or patent status

Additional rules:
- Report only metrics produced by code in this repo, with the command, config, seed and data version that produced them.
- Do not call a feature "novel" or "first" without a documented prior-art/literature analysis. Combining existing models is not a novelty claim by itself (Final Plan §37.10).
- Do not claim causation from temporal correlation.
- Report failures and negative results. Do not cherry-pick successful events for performance claims (Final Plan §27).
- Keep synthetic-anomaly evaluation separate from real-world evaluation (Final Plan §28).
- Disclose that FinBERT evaluation on Financial PhraseBank overlaps with its fine-tuning data.
- Patent and legal scope require professional review. Do not change patent/disclosure wording for implementation convenience (ML §63).
- The UI and docs must state that Aventra provides analytical signals, not financial advice or guaranteed predictions.

## 30. Definition of Done

A feature is done only when it is **implemented → integrated → tested → verified → documented**. "It compiles" is not done.

| Area | Done means |
|---|---|
| Code | Logic is in the correct layer (§6). No duplicated implementation. Constants are in config. No `any`, no dead code added. Matches local style. |
| API | Endpoint validates input, uses the `{success, data \| error}` envelope and correct status codes. Existing consumers are unaffected or updated. The endpoint is documented. |
| ML | Past-only features. Chronological split. Seed recorded. Artefact saved with version metadata. Baseline comparison exists. Metrics come from real runs and are saved to disk. Limitations are written down. |
| Data | Provenance recorded. Missing values, duplicates, outliers, timezones and session handling are explicit. No fabricated rows. Demo data is clearly separated. |
| Frontend | Real data flows through `services/*.ts`. Loading, empty, error and success states exist. Responsive at the §22 sizes. Accessible (§23). Reduced-motion respected. No placeholder presented as real. |
| Testing | New unit/API tests pass. Existing tests still pass. `npx tsc --noEmit` and `npm run build` pass. Leakage test for ML features. No tests skipped or weakened. |
| Integration | Verified end to end: backend running, frontend calling it (dev proxy or `VITE_API_BASE_URL`), real response rendered. With demo data, it works without the network. |
| Documentation | §7 status updated. `.env.example` updated. Relevant `docs/` or README section updated. Conflicts recorded in §32. |
| Deployment | When Docker exists: `docker compose up --build` from a clean checkout serves the feature. Vercel frontend build still succeeds. |

## 31. Known limitations (current code)

Full list: docs/25_LIMITATIONS.md. The ones agents trip over most:

- Without keys, only crypto, forex and Indian mutual funds return data. Equities, ETFs, indices, rates and all news are KEY-GATED. That is correct behaviour, not a bug.
- Indian equities have no permitted news source. Alpha Vantage news timestamps are assumed to be UTC.
- NSE uses the XBOM calendar as a proxy (no XNSE calendar).
- All thresholds and weights are uncalibrated defaults. In EXP-03 the ensemble is not uniformly best (LOF and ablations win on crypto) and it misses most single-day volume/volatility spikes. Do not describe the ensemble as better. EXP-01 is a v0.1 Yahoo-era record.
- Classification is rule-based (listing fields, name rules). OpenFIGI refinement has not run over the whole master.
- FinBERT: 64-token sentence inputs, unweighted sentence mean, English only, about 2 GB RAM together with MiniLM. The PhraseBank result overlaps with its training data.
- TypeScript is not linted (C12). Routing is manual, so every navigation is a full page load.
- Port 5000 may already be taken on a developer machine. Use `PORT` / `AVENTRA_API_PROXY` (docs/21_DEPLOYMENT.md).
- A global `pip install -r backend/requirements.txt` upgraded `packaging`, which conflicts with an unrelated Streamlit install on the development machine. Use a virtual environment.
- Unused leftovers: `three`/`@types/three`, `.neural-*` and `.demo-visual` CSS, `App.css`, `react.svg`, `vite.svg`.

## 32. Known conflicts and open questions

Record new conflicts here. On 2026-09-27 the user authorised autonomous decisions for ordinary implementation questions ("stop and ask only for a genuine architectural conflict"). The decisions below were taken under that authorisation. Any of them can be revisited, and each is documented where it is implemented.

| ID | Conflict | Status / decision |
|---|---|---|
| C1 | Empty `ML/` vs the docs' `ml/` package | **Resolved 2026-09-27:** the empty `ML/` was removed and `ml/` created (lowercase, importable as `ml.*`). |
| C2 | Empty `doc/` vs `docs/`; `/doc` is a UI route | **Resolved 2026-09-27:** the empty `doc/` was removed; engineering docs live in `docs/`. The `/doc` UI route is not built (see C11). |
| C3 | Flat backend vs `backend/app/` + `run.py` | **Resolved:** the flat layout was kept (`routes/`, `services/`, `utils/`). There is no `backend/database/`: storage lives in `ml/data/store.py` because the ML CLIs also persist results. |
| C4 | FinBERT weights location | **Resolved:** kept `backend/models/finbert/` (`FINBERT_MODEL_PATH`). New artefacts go in `artifacts/`. No finBERT clone. |
| C5 | API paths differ between the docs | **Resolved:** both path styles are served; an `AN-`/`EV-` prefix marks an ID. See docs/14_API_SPECIFICATION.md. |
| C6 | Market data through Flask | **Resolved:** `/api/market/*` (snapshots by canonical ID). `marketApi.ts` was removed in Phase 10; market calls live in `intelligenceApi.ts`. |
| C7 | Anomaly scope and scale | **Resolved:** the production ensemble is statistical + fingerprint + Isolation Forest, scored 0–1 with LOW/MEDIUM/HIGH/CRITICAL. LOF and LSTM-AE appear in EXP-01 only. PELT change points are retrospective context only (they use later bars within the window). |
| C8 | Risk formula | **Resolved:** the ML Pipeline's six components plus a documented **anomaly gate** (context terms × anomaly score), added after the ungated sum gave ordinary sessions risk ≈ 48 on real data. The Final Plan's price/volume/event-severity/change-point terms are not used. |
| C9 | Routes / React Router | **Open (design task):** manual routing kept; `/intelligence` added. The design-spec routes (`/about`, `/services`, `/doc`, `/services/*`) are not built. |
| C10 | Palette | **Open:** the existing palette is kept. `intelligence.css` introduces `--av-*` custom properties with the existing values, which is the first step if a migration is approved. |
| C11 | Homepage structure vs Design Spec | **Open (design task):** only the Market Intelligence preview was added (after LiveMarketData). WhyAventra, the contact form and CTA labels are unchanged. |
| C12 | ESLint ignores TS | **Open:** `npm run typecheck` is the gate; `typescript-eslint` not added. |
| C13 | Asset universe | **Superseded (Phases 1–12):** the universe is the Instrument Master synced from permitted listings. Support is claimed only where a legitimate provider supplies data (docs/06 §0). The v0.1 five-name registry remains only as a seed. |
| C14 | Leftover `three` deps / `.neural-*` CSS | **Open, user decision:** still present and unused. |
| C15 | Chart library | **Resolved:** no library. The dependency-free SVG `LineChart` component follows the existing hand-drawn SVG approach. |
| C16 | Validation library | **Resolved:** manual validation via `backend/utils/responses.py`; no Pydantic/Marshmallow. |
| C17 | Sentiment output shape | **Resolved:** additive fields only (`sentiment`, `confidence`, `model`, `model_version`, `timestamp`, `source`, `text`); `label` is unchanged. |
| C18 | ±15 min window vs available data | **Resolved:** daily observations for analytics. The correlation window is session-based ([open − 24 h, close + 12 h], configurable). No intraday data is used. |
| C19 | Vercel vs Docker | **Resolved:** both are supported (docs/21_DEPLOYMENT.md). |
| C20 | Research/patent cards without documents | **Open:** not built; no placeholder patent/paper content. |
| C22 | **Provider terms (Phase 0, 2026-09-27):** Yahoo's Terms of Service §2.4(i) prohibit automated data collection without permission, and the NSE Terms of Use prohibit automated collection from the NSE website. | **Resolved by the user (master implementation instruction):** Yahoo removed from production (no fallback); legacy Yahoo rows excluded from reads. NSE: no automated download; manual import only (`ml.instruments.sync --import-nse`). |
| C23 | Google News RSS (v0.1 news source) vs robots.txt: `news.google.com/robots.txt` disallows `/rss/search` | **Resolved 2026-09-27:** removed. News comes only from Alpha Vantage `NEWS_SENTIMENT` (key; US tickers, crypto, forex). Indian equities have no permitted news source and report `unavailable`. Legacy RSS rows are excluded from production reads. |
| C24 | NSE calendar | **Resolved:** exchange_calendars has no XNSE; XBOM is the proxy for session logic, historical sessions come from observed bars (docs/06 §3). |
| C21 | ML Pipeline §77 lists 26 doc files | **Open:** 8 docs with real content exist. The others are added when their subject has content, with no placeholder documents (Final Plan §23). |
