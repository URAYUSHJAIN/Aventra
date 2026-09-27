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
- **Market focus in the current code:** Indian equities on NSE (`RELIANCE`, `TCS`, `INFY`, `HDFCBANK`, `ICICIBANK`, Yahoo suffix `.NS`). The master docs' `AAPL`/`MSFT` examples are illustrative only.

## 2. Project purpose

Aventra detects unusual market behaviour for an asset, finds relevant financial news, measures its sentiment, correlates the signals in time, and produces a transparent risk signal with an evidence chain explaining **what happened, how unusual it was, what else happened at the same time, and why it was flagged**.

Aventra is **not**: a price predictor, trading bot, buy/sell recommender, portfolio manager, chatbot, fake-news detector, AI-generated-text detector, fraud detector, or market-manipulation detector. Do not add those features (see Final Implementation Plan §33 and ML Pipeline §64).

## 3. Technology stack

| Layer | Actually in the repo | Planned / not present |
|---|---|---|
| Frontend | React 19, TypeScript (strict), Vite 8, Tailwind CSS v4 via `@tailwindcss/vite`, `lucide-react`; dev: vitest 5, @testing-library/react, jsdom. `three` + `@types/three` are in `package.json` but **unused** (C14) | React Router, chart library (both deliberately not added — C9, C15) |
| Styling | `styles/index.css` (original) + `styles/intelligence.css` (dashboard/capability/preview, same palette) | — |
| Backend | Python 3.12, Flask 3, Flask-Cors, requests; gunicorn in Docker | Pydantic/Marshmallow (C16), PostgreSQL, scheduler |
| ML | pandas, NumPy (<2), scikit-learn (Isolation Forest, LOF), PyTorch (<2.5; FinBERT + experimental LSTM-AE), Transformers (<4.41), sentence-transformers (MiniLM), ruptures (PELT), NLTK | SHAP, LightGBM/XGBoost (no labelled risk data yet) |
| Data | Yahoo Finance chart API (server-side), Google News RSS, SQLite (`data/aventra.sqlite3`), synthetic `data/demo/`, `data/reference/assets.json` | Parquet feature store |
| Deploy | Docker Compose (`backend`, `frontend`; SQLite on a volume), `docker/`, `frontend/vercel.json` | Separate DB container |

Do not add a dependency that duplicates one already listed (e.g., a second icon set, a second HTTP client, a second chart library).

## 4. Repository structure (actual, 2026-09-27)

```text
Aventra/
├── AGENTS.md, CLAUDE.md          agent instructions (this file + Claude-specific)
├── readme.md                     project README (lowercase filename; current)
├── .gitignore, .dockerignore, .env.example, docker-compose.yml
├── context/                      MASTER DOCUMENTS (read-only for agents unless asked) — untracked in git
├── docs/                         engineering docs (04 architecture, 05 ML pipeline, 14 API, 17 evaluation, 19 testing, 21 deployment, 25 limitations)
├── docker/                       backend.Dockerfile, frontend.Dockerfile, nginx.conf
├── scripts/generate_demo_data.py deterministic synthetic demo dataset (+ cached FinBERT outputs)
├── data/
│   ├── reference/assets.json     analysed asset universe + entity aliases (committed)
│   ├── demo/                     SYNTHETIC demo dataset: market.csv, news.json, sentiment.json, manifest.json (committed)
│   └── aventra.sqlite3, processed/, raw/, external/   generated, git-ignored
├── artifacts/                    trained model artefacts (git-ignored)
├── experiments/results/          EXP-01, EXP-02 records (JSON + Markdown, committed)
├── ml/                           the intelligence package (owns all model/data logic)
│   ├── config.py                 every threshold/weight/window (uncalibrated defaults)
│   ├── data/                     assets, market_providers, validation, sessions, store (SQLite), cache
│   ├── features/engineering.py   past-only features + FEATURE_DEFINITIONS
│   ├── fingerprint/baseline.py   rolling median/MAD robust baseline, guarded update
│   ├── anomaly/                  statistical, detectors (IF, LOF), ensemble, changepoint, explain, lstm_autoencoder (experimental)
│   ├── news/                     finbert (moved from backend), providers, preprocessing, entity, events, ingest
│   ├── correlation/, temporal/, risk/, evidence/
│   ├── pipelines/                intelligence (orchestrator), run, batch (CLIs), artifacts
│   ├── evaluation/               synthetic (EXP-01), run_experiments, finbert_phrasebank (EXP-02)
│   └── tests/                    35 unittest cases incl. leakage + offline end-to-end demo
├── backend/
│   ├── app.py                    app factory; blueprints; JSON error handlers; /api/health
│   ├── routes/                   news_routes (analyze + GET news), market_routes, intelligence_routes
│   ├── services/                 market_service, intelligence_service, news_analysis_service (re-export of ml.news.finbert)
│   ├── utils/responses.py        envelope, ApiError, symbol/int validation
│   ├── models/finbert/           FinBERT weights (438 MB, git-ignored)
│   └── tests/                    test_news_routes (original 4) + test_api_routes (14)
└── frontend/
    ├── vite.config.ts            dev proxy /api → AVENTRA_API_PROXY or 127.0.0.1:5000 (old /market-api Yahoo proxy removed)
    ├── vitest.config.ts          jsdom test runner; `npm test`, `npm run typecheck`
    ├── eslint.config.js          NOTE: lints only **/*.{js,jsx} — TS files are NOT linted
    └── src/
        ├── App.tsx               manual routing + per-route metadata (/, /news-analysis, /intelligence, 4 capability routes)
        ├── services/             apiClient (envelope, timeout, GET retry, typed errors), marketApi, newsApi, intelligenceApi
        ├── types/api.ts          response types mirroring the backend
        ├── hooks/useApiResource.ts   loading/success/error + abort + reload
        ├── utils/format.ts       number/date formatting (UTC → IST display)
        ├── pages/                Home, IntelligencePage, CapabilityPage, NewsAnalysisPage, NotFoundPage (+ pages.test.tsx)
        ├── components/intelligence/  IntelligenceWorkspace, Anomaly/Fingerprint/News/Correlation/Risk/Evidence panels, LineChart, StateViews
        ├── components/home/      …, LiveMarketData (real batch quotes + linked news), IntelligencePreview
        ├── styles/               index.css, intelligence.css
        └── test/                 fetchMock, fixtures/intelligence-demo.json (real pipeline output, trimmed)
```

Still absent: CI, LICENSE, a PostgreSQL container, a scheduler, a cloned `finBERT/` repository (not needed). `App.css`, `react.svg`, `vite.svg`, and the `.demo-visual`/`.neural-*` CSS rules are unused.

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

Legend: **REAL** = working code exists · **PARTIAL** = works only in some conditions or covers part of the scope · **PLACEHOLDER** = UI with hard-coded/illustrative values · **EXPERIMENTAL** = uncommitted/unreviewed · **PLANNED** = nothing in the repo.

| Pipeline stage / component | Status | Evidence in repo |
|---|---|---|
| Landing page (Hero, About, Services, WhyAventra, Contact, Footer, Navbar) | REAL | `frontend/src/components/**`; Navbar/Footer link to `/intelligence` |
| `GET /api/health` | REAL | `backend/app.py` (adds data mode, FinBERT file presence, demo dataset presence) |
| FinBERT sentiment `POST /api/news/analyze` + `/news-analysis` page | REAL | `ml/news/finbert.py` (moved; `backend/services/news_analysis_service.py` re-exports). Response fields only added. EXP-02 run. |
| Market data | REAL | `ml/data/market_providers.py` (Yahoo chart, server-side, cached, SQLite fallback marked `stale`) → `/api/market/*` → `marketApi.ts`. Works in Docker; on Vercel only with `VITE_API_BASE_URL` + a hosted backend. |
| Market heat map / "Market News" panel | REAL | Batch quotes for all 20 cells (grey = unavailable, never invented); news panel = `/api/news` with FinBERT labels |
| Capability pages (fingerprint / anomaly / correlation / risk) | REAL | `CapabilityPage.tsx` (replaced `CapabilityDemoPage.tsx`), API-backed panels, same URLs |
| Intelligence dashboard `/intelligence` + homepage preview | REAL | `IntelligencePage.tsx`, `IntelligencePreview.tsx` |
| Data validation / cleaning | REAL | `ml/data/validation.py` (incl. holiday placeholder removal) |
| Temporal alignment | REAL | `ml/data/sessions.py` (UTC, NSE sessions, news → session) |
| Feature engineering | REAL | `ml/features/engineering.py` (past-only; leakage test) |
| Behavioural fingerprinting | REAL | `ml/fingerprint/baseline.py` (median/MAD, guarded update). LSTM embedding fingerprint: PLANNED |
| Anomaly detection | REAL (statistical + fingerprint + Isolation Forest ensemble); EXPERIMENTAL (LOF, LSTM-AE: EXP-01 only); REAL-retrospective (PELT change points, context only) | `ml/anomaly/` |
| News ingestion, dedup, entity linking, sentiment storage | REAL | `ml/news/` (Google News RSS; alias-based linking; SQLite) |
| Cross-source correlation, temporal/lead-lag analysis | REAL | `ml/correlation/`, `ml/temporal/` (lead/lag usually `insufficient_data` with RSS coverage) |
| Risk scoring, evidence chain | REAL (uncalibrated weights) | `ml/risk/scoring.py` (anomaly-gated), `ml/evidence/chain.py`. SHAP: PLANNED (needs a trained risk model) |
| Database / persistence | REAL | SQLite via `ml/data/store.py` |
| Demo dataset `data/demo/` | REAL (synthetic, labelled) | `scripts/generate_demo_data.py` |
| Evaluation / experiments | PARTIAL | EXP-01 (synthetic injection, baselines + ablations) and EXP-02 (FinBERT/PhraseBank, overlap disclosed) in `experiments/results/`. Known-event benchmark, correlation-quality and risk-calibration evaluations: PLANNED. Only quote numbers from those files. |
| Docker / Compose | REAL | Verified 2026-09-27: both images built; backend healthy; UI, `/api/*` via nginx, DEMO and live RELIANCE analyses and FinBERT all worked in containers (see §20, docs/21_DEPLOYMENT.md) |
| Tests | REAL | ML 35, backend 18, frontend 15 (vitest). CI: PLANNED |
| Contact form | PARTIAL | Opens `mailto:` only if `VITE_CONTACT_EMAIL` is set; otherwise shows "not configured". |
| 3D "Neural Pipeline" | REMOVED by user | Leftovers: unused `three` deps and `.neural-*` CSS (C14). |

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

Current: no persistence. Target (Final Plan §18, ML §58): SQLite first (migration-friendly for PostgreSQL later), tables `assets, prices, news, news_sentiment, features, fingerprints, anomalies, events, risk_scores, evidence`, plus Parquet/JSON for experiment artefacts.

Directory intent (create only when content exists):
- `data/raw/` — immutable provider downloads, with provenance (source, fetch time, parameters).
- `data/interim/`, `data/processed/`, `data/features/` — derived; must be reproducible from raw via code.
- `data/demo/` — deterministic, clearly labelled demo scenario (ML §56–57). Demo data must never be shown as live data.
- Large/raw data files are git-ignored. Commit small demo fixtures only.

For **every** data or ML change, explicitly check and handle:

| Concern | Rule |
|---|---|
| Missing values | Detect and report counts. Impute only with past data. Never forward-fill across a gap longer than the configured limit. |
| Duplicates | Deduplicate on `(symbol, timestamp)` for prices and on URL/normalised headline for news. Log how many were removed. |
| Outliers | Do **not** blindly delete. Distinguish a data error (negative price, high < low, zero volume on a trading bar) from a real market anomaly. A real extreme move is the thing Aventra detects. |
| Timestamps | Store in UTC with timezone awareness. Convert to `Asia/Kolkata` only for display/session logic. |
| Market sessions | NSE regular session 09:15–15:30 IST. Handle holidays, half days, pre-open. Align news published outside the session to the next session open, and record that you did. |
| Leakage | Features at time *t* use only data < *t* (or ≤ *t* for the current bar's own value). No centred rolling windows. Scalers/detectors are fit on the training split only. |
| Inference availability | Use a feature only if it is available at inference time with the same definition. Training and inference share one feature function. |
| Splits | Chronological train/validation/test (e.g. 70/15/15). Never shuffle across time. |
| Class imbalance | Anomalies are rare. Report precision/recall/PR-AUC, not accuracy alone. |
| Provenance | Every stored row records its source and fetch time. Every model output records `model_name` and `model_version`. |

**Never fabricate financial data, news, sentiment or ML results.** If data is unavailable, return an explicit unavailable state (ML §66) — e.g. "News context unavailable", `status = insufficient_history` (ML §67).

## 12. API conventions

Existing contract (preserve it):
- Success: `200 {"success": true, "data": {...}}`
- Failure: `4xx/5xx {"success": false, "error": "<human-readable message>"}`
- `POST /api/news/analyze` body `{"text": string}` (max 12,000 chars) → `data = {label, positive_probability, neutral_probability, negative_probability, sentiment_score}`. Consumer: `frontend/src/services/newsApi.ts` → `NewsAnalysis.tsx`.

Rules:
- Before changing any existing endpoint, `grep` the frontend for every consumer (`services/*.ts`, types, components). Only add fields. Do not rename, remove or retype fields without explicit approval. If a breaking change is approved, update the consumers in the same change.
- New endpoints follow the Final Plan §19 list, prefixed `/api/`. For path shapes that differ between the docs, see C5.
- Status codes: 400 invalid input/symbol, 404 unknown resource, 413 payload too large, 502 upstream provider failure, 503 local model/service unavailable, 500 unexpected. Never return stack traces or internal paths.
- Validate every input at the route boundary: type, presence, length, symbol format (whitelist or regex).
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
- Frontend (from `frontend/`): `npm test` (vitest + jsdom), `npm run typecheck`, `npm run build`. **`build` does not type-check.** `npm run lint` ignores `.ts/.tsx` (C12), so a passing lint is not evidence of TS quality.
- Experiments (not tests; they write `experiments/results/`): `py -3.12 -m ml.evaluation.run_experiments`, `py -3.12 -m ml.evaluation.finbert_phrasebank`.

Required for every change:
- **Backend:** tests for valid input, empty/missing input, invalid JSON/type, model-loading failure, inference failure and upstream-provider failure (Final Plan §24).
- **ML:** unit tests for each feature calculation (use hand-computed expected values on small fixtures), fingerprint deviation, detector score normalisation, ensemble, correlation scoring, risk calculation and evidence construction. Add a **leakage test**: shifting or removing future rows must not change a past feature value.
- **Integration:** data → ML → Flask (test client) with the demo dataset, no network.
- **Frontend:** once a test runner is added, cover loading, success, empty, API-error and backend-unavailable states. Until then, verify these manually and report that you did it manually.
- Tests must not call live external APIs. Mock the providers or use `data/demo/`.
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
- Never substitute fabricated or random data on failure. (Existing `fallback()` in `marketApi.ts` returns placeholder chart points while labelled "MARKET DATA UNAVAILABLE". Do not extend this pattern to numeric metrics.)
- Services raise typed domain exceptions. Routes map them to status codes (see §12). Unexpected exceptions are logged with `logger.exception` and returned as a generic 500 message.
- Frontend service functions throw `Error` with a user-readable message. Components render it in a `role="alert"` element.

## 18. Logging requirements

- Backend uses the `logging` module (`logger = logging.getLogger(__name__)`). No `print` in application code.
- Each pipeline stage logs: module, symbol, operation, status, duration and error if any (ML §51).
- Never log secrets, full article bodies, request bodies with user text, or credentials. Log counts and IDs instead.
- Log data-quality events: rows dropped, duplicates removed, gaps found.
- No leftover `console.log` in committed frontend code.

## 19. Environment-variable rules

Existing variables:

| Variable | Where | Purpose |
|---|---|---|
| `FINBERT_MODEL_PATH` | backend | Override FinBERT directory (default `backend/models/finbert`) |
| `CORS_ORIGINS` | backend | Comma-separated allowed origins (default `*`) |
| `VITE_API_BASE_URL` | frontend | Flask origin when not same-origin (empty → `/api` proxy) |
| `VITE_CONTACT_EMAIL` | frontend | Contact form `mailto:` target |
| `AVENTRA_DATA_MODE` | backend | `live` (default) or `demo` (only `data/demo`, offline) |
| `AVENTRA_DB_PATH`, `AVENTRA_ARTIFACT_DIR`, `AVENTRA_DATA_DIR`, `AVENTRA_HISTORY_RANGE`, `AVENTRA_ANOMALY_THRESHOLD`, `AVENTRA_SEMANTIC_MODEL` | backend | Read in `ml/config.py` |
| `PORT`, `FLASK_DEBUG` | backend | Local dev server only |
| `AVENTRA_API_PROXY` | frontend dev server | Vite `/api` proxy target (default `http://127.0.0.1:5000`) |
| `FRONTEND_PORT`, `BACKEND_PORT`, `FINBERT_HOST_PATH` | Docker Compose | See root `.env.example` |

Rules:
- Every new variable goes into the relevant `.env.example` with a comment and a safe default, in the same change.
- Read env vars in one config module per side. Do not scatter `os.getenv` or `import.meta.env` calls.
- The app must start with no `.env` present (sensible defaults, or a clear error for truly required values).

## 20. Docker / deployment rules

- Implemented: `docker compose up --build` starts `backend` (Flask + ML pipeline, gunicorn **1 worker** × 8 threads, because the models and cache live in the process) and `frontend` (nginx + Vite build, proxies `/api`). SQLite, artefacts and the HF cache live on the `aventra-state` volume. There is no DB container until PostgreSQL is justified. ML runs inside the backend container. Do not create one container per model or other microservices. Files: `docker/`, `docker-compose.yml`, `.dockerignore`.
- Do not bake the 438 MB FinBERT weights into git. Provide them through a mounted volume, or a documented download step, and point `FINBERT_MODEL_PATH` at them.
- The current Vercel deployment serves only the static frontend. Production news analysis and market data will not work until a backend is deployed and `VITE_API_BASE_URL` is set (C6). Keep `vercel.json` working when making changes.
- The Docker setup must run on a clean machine with only documented steps. Verify this before calling the Docker work done.

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

- Current branch `main`. **Create a feature branch before committing** (`feat/…`, `fix/…`, `docs/…`).
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
   - Yahoo can rate-limit or change its unofficial API without notice.

## 28. Rules for documentation

- Engineering docs go in a repo `docs/` folder, which is planned (see C2 for the `doc/` vs `docs/` question). Candidate file list: ML §77, and the Final Plan §6 deliverable `docs/current-architecture.md`.
- Update docs in the same change as the code when you change architecture, endpoints, env vars, setup steps, data schema or model behaviour.
- Keep §7 of this file accurate. When a component changes status, update its row.
- `readme.md` is currently stale (it says there is no Flask API). Fix it when a task touches setup or status. Do not rename it to `README.md` without asking, because the case-only rename is fragile on Windows/OneDrive.
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

- Yahoo's chart endpoint is unofficial and may rate-limit. Stored prices are used on failure and marked `stale`.
- Google News RSS only covers about 30 days of headlines, so older flagged sessions usually show `no_aligned_news`.
- All thresholds and weights are uncalibrated defaults. EXP-01 shows the ensemble does not beat the statistical baseline on synthetic single-bar anomalies. Do not describe the ensemble as better.
- FinBERT: 64-token sentence inputs, unweighted sentence mean, English only, about 2 GB RAM together with MiniLM. The PhraseBank result overlaps with its training data.
- Cold pipeline runs take 9–30 s (up to about 40 s on the first Docker run while MiniLM downloads). The cache is per process, so gunicorn must stay at 1 worker.
- TypeScript is not linted (C12). Routing is manual, so every navigation is a full page load.
- Port 5000 may already be taken on a developer machine. Use `PORT` / `AVENTRA_API_PROXY` (docs/21_DEPLOYMENT.md).
- Unused leftovers: `three`/`@types/three`, `.neural-*` and `.demo-visual` CSS, `App.css`, `react.svg`, `vite.svg`. If a three.js visual returns, it must cancel its `requestAnimationFrame` loop on unmount, honour reduced motion, use the palette and be lazy-loaded.

## 32. Known conflicts and open questions

Record new conflicts here. On 2026-09-27 the user authorised autonomous decisions for ordinary implementation questions ("stop and ask only for a genuine architectural conflict"). The decisions below were taken under that authorisation. Any of them can be revisited, and each is documented where it is implemented.

| ID | Conflict | Status / decision |
|---|---|---|
| C1 | Empty `ML/` vs the docs' `ml/` package | **Resolved 2026-09-27:** the empty `ML/` was removed and `ml/` created (lowercase, importable as `ml.*`). |
| C2 | Empty `doc/` vs `docs/`; `/doc` is a UI route | **Resolved 2026-09-27:** the empty `doc/` was removed; engineering docs live in `docs/`. The `/doc` UI route is not built (see C11). |
| C3 | Flat backend vs `backend/app/` + `run.py` | **Resolved:** the flat layout was kept (`routes/`, `services/`, `utils/`). There is no `backend/database/`: storage lives in `ml/data/store.py` because the ML CLIs also persist results. |
| C4 | FinBERT weights location | **Resolved:** kept `backend/models/finbert/` (`FINBERT_MODEL_PATH`). New artefacts go in `artifacts/`. No finBERT clone. |
| C5 | API paths differ between the docs | **Resolved:** both path styles are served; an `AN-`/`EV-` prefix marks an ID. See docs/14_API_SPECIFICATION.md. |
| C6 | Market data through Flask | **Resolved:** `/api/market/*`. `marketApi.ts` keeps its exports; the `/market-api` Yahoo proxy was removed. |
| C7 | Anomaly scope and scale | **Resolved:** the production ensemble is statistical + fingerprint + Isolation Forest, scored 0–1 with LOW/MEDIUM/HIGH/CRITICAL. LOF and LSTM-AE appear in EXP-01 only. PELT change points are retrospective context only (they use later bars within the window). |
| C8 | Risk formula | **Resolved:** the ML Pipeline's six components plus a documented **anomaly gate** (context terms × anomaly score), added after the ungated sum gave ordinary sessions risk ≈ 48 on real data. The Final Plan's price/volume/event-severity/change-point terms are not used. |
| C9 | Routes / React Router | **Open (design task):** manual routing kept; `/intelligence` added. The design-spec routes (`/about`, `/services`, `/doc`, `/services/*`) are not built. |
| C10 | Palette | **Open:** the existing palette is kept. `intelligence.css` introduces `--av-*` custom properties with the existing values, which is the first step if a migration is approved. |
| C11 | Homepage structure vs Design Spec | **Open (design task):** only the Market Intelligence preview was added (after LiveMarketData). WhyAventra, the contact form and CTA labels are unchanged. |
| C12 | ESLint ignores TS | **Open:** `npm run typecheck` is the gate; `typescript-eslint` not added. |
| C13 | Asset universe | **Resolved:** the five NSE names plus the synthetic DEMO asset. TATAMOTORS.NS returned "No data found, symbol may be delisted" on 2026-09-27 and was not added. |
| C14 | Leftover `three` deps / `.neural-*` CSS | **Open, user decision:** still present and unused. |
| C15 | Chart library | **Resolved:** no library. The dependency-free SVG `LineChart` component follows the existing hand-drawn SVG approach. |
| C16 | Validation library | **Resolved:** manual validation via `backend/utils/responses.py`; no Pydantic/Marshmallow. |
| C17 | Sentiment output shape | **Resolved:** additive fields only (`sentiment`, `confidence`, `model`, `model_version`, `timestamp`, `source`, `text`); `label` is unchanged. |
| C18 | ±15 min window vs available data | **Resolved:** daily bars for analytics (5 years available). The correlation window is session-based ([open − 24 h, close + 12 h], configurable). 5-minute bars are used only for the live quote chart. |
| C19 | Vercel vs Docker | **Resolved:** both are supported (docs/21_DEPLOYMENT.md). |
| C20 | Research/patent cards without documents | **Open:** not built; no placeholder patent/paper content. |
| C22 | **Provider terms (Phase 0, 2026-09-27):** Yahoo's Terms of Service §2.4(i) prohibit automated data collection without permission, and the NSE Terms of Use prohibit automated collection from the NSE website. The shipped pipeline uses Yahoo for prices and search. | **Open — user decision:** see docs/06_DATA_SOURCES_AND_PROVIDERS.md §5. Do not add new Yahoo or NSE-website dependencies until decided. Never schedule NSE website downloads. |
| C21 | ML Pipeline §77 lists 26 doc files | **Open:** 7 docs with real content exist. The others are added when their subject has content, with no placeholder documents (Final Plan §23). |
