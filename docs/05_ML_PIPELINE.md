# 05 — ML Pipeline (as implemented)

Authority for intent: `context/AVENTRA_MASTER_ML_PIPELINE.md`. This document describes what the code in `ml/` actually does, including where it deliberately differs from the master document.

```text
Market data (Yahoo chart API | synthetic demo) ──► validation/cleaning ──► temporal alignment (UTC, NSE sessions)
        │                                                                          │
        ▼                                                                          ▼
Feature engineering (past-only) ─► Behavioural fingerprint ─► Anomaly detection (statistical + fingerprint + Isolation Forest)
                                                                          │
News (Google News RSS | demo) ─► clean/dedupe ─► entity linking ─► FinBERT ┤
                                                                          ▼
                     Cross-source correlation ─► temporal analysis ─► risk score ─► evidence chain ─► Flask ─► React
```

Entry points: `ml.pipelines.intelligence.run_intelligence(symbol)`; CLI `py -3.12 -m ml.pipelines.run --symbol DEMO` and `ml.pipelines.batch`. All defaults live in `ml/config.py` and are **uncalibrated engineering defaults**.

## 1. Data (`ml/data`)

- **Providers** (`market_providers.py`): `YahooChartProvider` (unofficial endpoint, keyless, may rate-limit), `DemoMarketProvider` (`data/demo/market.csv`). `AVENTRA_DATA_MODE=demo` forces the demo provider. Live history is upserted into SQLite `prices`; if the provider later fails, stored prices are used and the result is marked `stale`. Nothing is ever invented.
- **Validation** (`validation.py`): parses types, sorts, removes duplicates, rows with missing/non-positive prices, impossible OHLC ranges and **provider holiday placeholders** (zero volume *and* O=H=L=C — found on 6 NSE holidays per asset). Extreme but valid moves are **kept** and listed in `large_moves_flagged` (> 35 % close-to-close) for review.
- **Sessions** (`sessions.py`): UTC everywhere; NSE regular session 09:15–15:30 IST. News is aligned to the first *observed* trading session whose close is at/after publication (holidays handled via the price calendar). An in-progress session is excluded from daily analytics.
- **Store** (`store.py`): SQLite tables `prices, news, news_links, news_sentiment, pipeline_runs, anomalies, events, risk_assessments, evidence`; parameterised SQL only.

## 2. Features (`ml/features/engineering.py`)

Daily bars. For bar *t* only bars ≤ *t* are used; baselines that bar *t* is compared against use bars < *t* (`shift(1)`), never centred windows. A unit test checks that altering future rows leaves past features unchanged.

`return_1, log_return, return_5, volatility_20, log_volume, volume_ratio, volume_zscore, gap_pct, range_pct, ma20_distance, rsi_14 (Wilder), relative_return (vs NIFTY 50; NaN without benchmark)`.

## 3. Behavioural fingerprint (`ml/fingerprint/baseline.py`)

Dimensions: `return_1, log_volume, volatility_20, range_pct, gap_pct, relative_return` (equal weights).

- Baseline at *t* = median and MAD×1.4826 of the previous **120** observations (min **60**, else `insufficient_history`).
- Robust z = (x − median) / scale; per-dimension deviation score = linear map of |z| from 2 (→0) to 6 (→1).
- **Guarded adaptive update:** an observation with |z| > 4 enters the history clipped to median ± 4·scale, so one extreme session cannot redefine normal behaviour while persistent shifts are still absorbed.
- `fingerprint_score` = weighted mean of available dimension scores; levels normal / mild / elevated / high.

## 4. Anomaly detection (`ml/anomaly`)

| Layer | Implementation | Role |
|---|---|---|
| Statistical | classic z-score vs previous 20 bars on `return_1, log_volume, range_pct`; max deviation score | baseline 1 |
| Behavioural | fingerprint score | layer 2 |
| ML | Isolation Forest (200 trees, seed 42) on 9–10 detector features, RobustScaler; fitted **only on bars before the scoring window** (last 250 sessions) | baseline 2 |
| Ensemble | 0.35·statistical + 0.35·fingerprint + 0.30·IF (renormalised if a component is missing) | production score |
| LOF | novelty LOF (k = 20), same protocol | evaluated in EXP-01 only |
| LSTM autoencoder | 20-step windows, 16 hidden units, 30 epochs, seed 42 | **experimental**, EXP-01 only |
| Change points | ruptures PELT (l2, penalty 12) on log return + log volume | **retrospective** context only (uses the whole window → not used for detection or risk) |

ML scores are mapped to [0, 1] with the ECDF of *training* scores (0 below the 90th training percentile). Severity: ≥ 0.85 CRITICAL, ≥ 0.65 HIGH (= flag threshold), ≥ 0.40 MEDIUM. `model_agreement` = 1 − (max − min) of detector scores. Contributing features = fingerprint dimensions with |robust z| ≥ 2, with plain-language explanations.

Artefacts: `artifacts/models/<symbol>/isolation_forest.{joblib,json}` with `trained_through`, feature list, parameters, seed and a training-data hash; an artefact is reused only if it was trained strictly before the scoring window on identical data.

## 5. News and sentiment (`ml/news`)

Google News RSS search (headline, source, link, time — no article scraping) or demo headlines → HTML/whitespace/Unicode normalisation → de-duplication (URL, normalised headline) → **entity linking** (`data/reference/assets.json`: strong alias 0.95, weak alias 0.70 with exclusion phrases such as "Reliance Power", explicit metadata 1.0; links below 0.6 are dropped) → **FinBERT** (existing model, unchanged inference: sentences ≤ 64 tokens, probabilities averaged) → stored. If FinBERT is unavailable: demo mode uses cached real FinBERT outputs (`data/demo/sentiment.json`); live mode reports sentiment as unavailable. Event category: transparent keyword rules (Final Plan §14), with the matched keywords returned.

## 6. Cross-source correlation (`ml/correlation`) and temporal analysis (`ml/temporal`)

For a flagged session D, candidate news = same asset, published in [open(D) − 24 h, close(D) + 12 h].

`correlation_score = 0.30·temporal_proximity + 0.25·asset_match + 0.20·|sentiment| + 0.25·anomaly_score` (ML Pipeline §24 starting formula). Temporal proximity = 1 inside the session, decaying linearly to 0 at the window edges. Semantic relevance (all-MiniLM-L6-v2 cosine between an event description and the headline) is reported and used as a tie-breaker, not in the score. Every match states its relation (before open / during session / after close, with hours). Lead/lag: correlation of daily mean sentiment with returns at lags −3…+3 days, only with ≥ 20 news days (otherwise `insufficient_data`). Language is associative only.

## 7. Risk (`ml/risk/scoring.py`)

`risk = 100 × [0.25·anomaly + 0.20·fingerprint + anomaly × (0.15·|sentiment| + 0.20·correlation + 0.10·temporal + 0.10·agreement)]`

**Documented refinement of ML Pipeline §27 (anomaly gate).** The ungated six-term sum gave ordinary sessions (anomaly ≈ 0) risk ≈ 48 on real NSE data merely because news existed and detectors agreed the session was normal. Context terms are therefore scaled by the anomaly score. Contributions are reported per component (exact decomposition). Without news the basis is `market_only_no_aligned_news` or `market_only_news_unavailable`. Levels: ≥ 75 HIGH, ≥ 50 ELEVATED, ≥ 25 MODERATE. SHAP is **not** used: there is no trained risk model yet (no labels); see 26_FUTURE_WORK in limitations.

## 8. Evidence chain (`ml/evidence/chain.py`)

Time-ordered items (type, signal, description, value, source, URL, gap from previous) for: each contributing feature (source = market provider), the ensemble (detector scores + agreement), each aligned article, its FinBERT output, its correlation, any retrospective change point on that date, and the final risk. `explanation` answers what / when / how unusual / which signals / which news / timing / why, plus the non-causal caveat.

## 9. Reproducibility and leakage controls

- Seeds: 42 for Isolation Forest, LOF, LSTM, demo generator uses its own fixed seed.
- Chronological splits only; detectors never see the scored window; ECDF normalisers fitted on training scores.
- Every result records data provenance (`data_source`), validation report, model metadata and parameters; `pipeline_runs` stores full results.
