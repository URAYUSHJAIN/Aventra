# 19 — Testing

All suites run offline: providers are mocked or replaced by the synthetic demo dataset, and FinBERT is mocked or forced unavailable where a test does not need it.

| Suite | Command (repo root unless noted) | Covers |
|---|---|---|
| ML unit + integration | `py -3.12 -m unittest discover -s ml/tests -t .` | validation (duplicates, invalid OHLC, holiday placeholders, extreme moves kept), sessions/UTC alignment, hand-computed features, **leakage** (future rows cannot change past features/fingerprints), robust baseline + guarded update, ECDF normalisation, Isolation Forest determinism, LOF, ensemble renormalisation/severity, entity linking exclusions, event rules, correlation window/scoring, risk decomposition and anomaly gate, news-unavailable basis, evaluation helpers, **end-to-end demo pipeline** (scenario flagged, evidence complete, no causal wording, persisted) |
| Backend API | `py -3.12 -m unittest discover -s backend/tests -t .` | health, input validation (400), unknown asset/route (404), provider failure (502, no internal details), provider not-found (404), batch partial failures, demo labelling, every intelligence/anomaly/event/risk/evidence endpoint, news endpoint, `/api/news/analyze` backward compatibility + new fields, 413 limit, FinBERT unavailable (503) |
| Frontend | `cd frontend && npm test` | API client (envelope, client errors, backend unavailable + retry), market mapping (no invented values, demo label), news service messages, dashboard loading → success with every panel, error + retry, capability page, NewsAnalysis validation and result |
| Types / build | `cd frontend && npm run typecheck && npm run build` | `vite build` does not type-check, so `typecheck` is the gate. `npm run lint` only covers `.js/.jsx` (AGENTS.md C12). |

Results on 2026-09-27: ML 35/35, backend 18/18, frontend 15/15 passing; typecheck and build clean.

Manual/integration verification performed: Flask + Vite dev proxy against live providers (all pages 200, every endpoint returned the envelope), headless-browser render of `/intelligence?symbol=DEMO` at 1440×900 and 390×844 (no console errors, no horizontal overflow) and of the homepage market and preview sections.
