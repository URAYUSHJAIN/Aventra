# 04 — System Architecture (as implemented)

```text
Browser (React 19 + TS + Vite)
   │  services/apiClient.ts → /api/*          (never calls market/news providers directly)
   ▼
nginx (Docker) or Vite dev proxy
   ▼
Flask API  backend/app.py  ── routes/{market,news,intelligence}_routes.py ── services/{market,intelligence}_service.py
   │  orchestration, validation, caching, error mapping
   ▼
ML package  ml/  (owns all intelligence)
   data/ providers · validation · sessions · store (SQLite) · cache
   features/ · fingerprint/ · anomaly/ · news/ (FinBERT, entity, events, ingest) · correlation/ · temporal/ · risk/ · evidence/
   pipelines/ intelligence · run · batch · artifacts        evaluation/ synthetic · finbert_phrasebank
   ▼
External: Yahoo Finance chart API (prices, keyless), Google News RSS (headlines) · Local: FinBERT weights, MiniLM cache, SQLite
```

## Layer rules

- **React = presentation.** All HTTP goes through `frontend/src/services/` (`apiClient`, `marketApi`, `newsApi`, `intelligenceApi`); response types in `frontend/src/types/api.ts`.
- **Flask = orchestration/API.** No model logic in routes; one envelope; domain exceptions mapped to status codes in `backend/app.py`.
- **ML package = intelligence.** FinBERT moved from `backend/services/news_analysis_service.py` to `ml/news/finbert.py`; the old module re-exports the same names so existing imports and tests keep working.

## Request flow — `GET /api/intelligence/RELIANCE`

1. `intelligence_service.get_intelligence` — per-symbol lock; 15-minute in-memory cache.
2. `run_intelligence` — market history (provider → SQLite; stored fallback) + NIFTY benchmark → validation → features → fingerprint → statistical / Isolation Forest (fit before the scoring window, artefact reused when valid) → ensemble → change points → news ingest (RSS → dedupe → entity links → FinBERT → SQLite) → per flagged session: correlation → risk → evidence → explanation.
3. The result is saved to `pipeline_runs` (+ anomalies, events, risk_assessments, evidence) and returned.

Cold run: 9–30 s (model loading, provider calls); cached: milliseconds.

## Storage

SQLite (`data/aventra.sqlite3`, or `/app/state` in Docker) — tables listed in 05_ML_PIPELINE §1. Schema uses portable SQL types for a later PostgreSQL move. Model artefacts in `artifacts/`; experiment records in `experiments/results/` (committed); demo data in `data/demo/` (committed, synthetic).

## Frontend routes (manual router in `App.tsx`)

`/` (landing, includes live market panel and Market Intelligence preview) · `/intelligence?symbol=` (dashboard) · `/behavioural-fingerprint` · `/anomaly-detection` · `/event-correlation` · `/risk-evidence` (capability pages, real API data) · `/news-analysis` (FinBERT text analysis). React Router was not introduced (no new dependency; existing routing works).

## Key decisions (see AGENTS.md §32 for the full list)

- Daily bars for analytics (multi-year history available); 5-minute bars only for the live quote chart.
- Production ensemble = statistical + fingerprint + Isolation Forest (ML Pipeline MVP); LOF, LSTM-AE, change points evaluated/annotated only.
- Risk formula: ML Pipeline components with an anomaly gate (05_ML_PIPELINE §7).
- API serves both documents' path styles.
