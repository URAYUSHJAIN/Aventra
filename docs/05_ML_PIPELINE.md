# 05 — ML Pipeline (as implemented)

Authority for intent: `context/AVENTRA_MASTER_ML_PIPELINE.md`. This document describes what the code in `ml/` actually does, including where it deliberately differs from the master document.

```text
Canonical instrument ID ─► Instrument Master (asset class, exchange, currency, timezone, calendar, capabilities)
        ▼
Provider router (legitimate fallback only) ─► database cache ─► validation (capability-aware) ─► UTC / calendar alignment
        ▼
Feature set chosen from the capability profile ─► past-only features ─► behavioural fingerprint
        ▼
Anomaly detection (statistical + fingerprint + Isolation Forest) ──────────────┐
News (permitted provider) ─► clean/dedupe ─► entity linking ─► FinBERT ────────┤
                                                                               ▼
          Cross-source correlation ─► temporal analysis ─► risk score ─► evidence chain (with provenance) ─► API ─► React
```

Entry points:
- `ml.pipelines.intelligence.run_intelligence(instrument_id)`;
- the background worker (`ml.jobs.worker`);
- the CLIs `py -3.12 -m ml.pipelines.run --instrument CRYPTO:BTC-USDT` and `ml.pipelines.batch --instruments …`.

All defaults are in `ml/config.py` and are **uncalibrated engineering defaults**. The pipeline never sees provider symbols.

## 1. Data (`ml/data`, `ml/providers`, `ml/instruments`)

- **Instrument Master.** The master is synced from permitted listings: Upstox instrument file, SEC company tickers, Binance `exchangeInfo`, CoinGecko `coins/list`, Frankfurter currencies and the AMFI NAV file.
  - Optional sources: Alpha Vantage `LISTING_STATUS` (with a key) and a manual import of NSE files the user downloaded.
  - About 68,600 instruments on 2026-09-27. Every listed instrument is stored; there is no top-N filter.
  - Classification uses listing fields (Upstox series codes, AMFI scheme data), refined by OpenFIGI security types where it has run. `class_source` and `class_confidence` record how each class was decided.
- **Capability profiles** (`ml/instruments/profiles.py`): `has_ohlc`, `has_volume`, `value_kind` (price / nav / reference_rate / yield / index_level), `minimum_history`, calendar and timezone, for 11 asset classes.
- **Router** (`ml/providers/registry.py`): the candidate providers for an instrument are those whose capability covers its class and exchange. They are tried in priority order; a provider without credentials is skipped with the reason `missing_credentials`.
  - If none returns data, `DataUnavailable` is raised with a code and the full list of attempts.
  - There is no hidden fallback to an unrelated source. Yahoo was removed.
- **HTTP layer** (`ml/providers/http.py`):
  - token-bucket rate limit per provider;
  - retries honouring `Retry-After`;
  - circuit breaker after repeated failures;
  - daily budget (Alpha Vantage: 25);
  - every call logged to `provider_calls`;
  - timeouts `(5 s connect, n s read)`.
- **Market data** (`market_data.load_series`):
  - uses stored observations younger than 6 h;
  - otherwise fetches incrementally from the provider;
  - on provider failure, uses stored data marked `stale`;
  - raises `INSUFFICIENT_SOURCE_DATA` on an empty or invalid frame.
- **Validation** (`validation.validate_series`), driven by the capability profile:
  - removes duplicates, non-positive or missing values, impossible OHLC ranges (only where OHLC exists) and holiday placeholder bars;
  - excludes an in-progress session;
  - keeps extreme but valid moves (> 35 %) and flags them;
  - adds a staleness note when the latest observation is older than 3 days (24/7), 5 days (24/5) or 10 days (exchange calendars).
- **Calendars** (`calendars.py`): `exchange_calendars` for exchanges (XNYS; **XBOM as the NSE proxy** because there is no XNSE calendar), plus explicit `24/7` and `24/5` rules. Everything is stored in UTC; trading dates are local exchange dates.
- **Benchmarks**:
  - Indian equity/ETF/REIT/InvIT → `IDX:NSE-NIFTY`;
  - Binance altcoins → `CRYPTO:BTC-USDT`;
  - CoinGecko coins → `CRYPTO:CG-bitcoin`;
  - everything else → none. None is invented; `relative_return` is then unavailable.

## 2. Features (`ml/features`)

For observation *t* only observations ≤ *t* are used. Baselines use observations < *t* (`shift(1)`); windows are never centred. A unit test checks that altering future rows leaves past features unchanged.

Computed where the data allows:
- `return_1, log_return, return_5, volatility_20`, `drawdown`;
- `log_volume, volume_ratio, volume_zscore` (volume only);
- `gap_pct, range_pct` (OHLC only);
- `ma20_distance, rsi_14` (Wilder);
- `relative_return` (benchmark only);
- yield features `change_bp, change_5_bp, volatility_bp_20, level_distance_bp`.

Feature sets (`ml/features/sets.py`, selected by `select_set(profile)`; the version hash is stored with each result):

| Set | Used for | Fingerprint dimensions (equal weights) | Statistical | Detector features |
|---|---|---|---|---|
| `ohlcv` | exchange-traded OHLCV (equities, ETFs, REITs, indices with volume) | return_1, log_volume, volatility_20, range_pct, gap_pct, relative_return | return_1, log_volume, range_pct | 10 incl. gap_pct |
| `ohlcv_continuous` | OHLCV on 24/7 and 24/5 markets (Binance) — the daily open equals the previous close, so the opening gap is meaningless | as `ohlcv` without gap_pct | as `ohlcv` | 9 (no gap_pct) |
| `close_volume` | CoinGecko (close + volume, no OHLC) | return_1, log_volume, volatility_20, drawdown, relative_return | return_1, log_volume | 9 |
| `close` | NAV, FX reference rates, indices without volume, commodity spot | return_1, volatility_20, drawdown, ma20_distance, relative_return | return_1, ma20_distance | 8 |
| `yield` | interest rates (basis points) | change_bp, volatility_bp_20, level_distance_bp | change_bp, level_distance_bp | 4 |

## 3. Behavioural fingerprint (`ml/fingerprint/baseline.py`)

- The baseline at *t* is the median and MAD × 1.4826 of the previous **120** observations. At least **60** are required; with fewer the status is `insufficient_history`.
- Robust z = (x − median) / scale. The per-dimension deviation score maps |z| linearly from 2 (→ 0) to 6 (→ 1).
- **Guarded adaptive update:** an observation with |z| > 4 enters the history clipped to median ± 4·scale. One extreme observation cannot redefine normal behaviour, while persistent shifts are still absorbed.
- `fingerprint_score` is the weighted mean of the available dimension scores. Levels: normal / mild / elevated / high.
- The version (`medmad-v1-<hash>`) is recorded in each result.

## 4. Anomaly detection (`ml/anomaly`)

| Layer | Implementation | Role |
|---|---|---|
| Statistical | classic z-score against the previous 20 observations, on the set's statistical features; max deviation score | baseline 1 |
| Behavioural | fingerprint score | layer 2 |
| ML | Isolation Forest (200 trees, seed 42) on the set's detector features, RobustScaler; fitted **only on observations before the scoring window** (last 250) | baseline 2 |
| Ensemble | 0.35·statistical + 0.35·fingerprint + 0.30·IF (renormalised if a component is missing) | production score |
| LOF | novelty LOF (k = 20), same protocol | evaluation only |
| LSTM autoencoder | 20-step windows, 16 hidden units, 30 epochs, seed 42 | **experimental**, EXP-01 only |
| Change points | ruptures PELT on the set's change-point columns | **retrospective** context only (uses the whole window, so it is excluded from detection and risk) |

- ML scores are mapped to [0, 1] with the ECDF of *training* scores (0 below the 90th training percentile).
- Severity: ≥ 0.85 CRITICAL; ≥ 0.65 HIGH, which is also the flag threshold; ≥ 0.40 MEDIUM.
- `model_agreement` = 1 − (max − min) of the detector scores.
- Contributing features are fingerprint dimensions with |robust z| ≥ 2, each with a plain-language explanation (percentages, or basis points for yields).

Artefacts are stored under `artifacts/models/<safe instrument key>/` with `trained_through`, the feature list, parameters, seed, feature-set version and a training-data hash. An artefact is reused only if it was trained strictly before the scoring window on identical data.

## 5. News and sentiment (`ml/news`)

- **Source.** Alpha Vantage `NEWS_SENTIMENT` is the only production news provider. It needs `ALPHAVANTAGE_API_KEY` and supports:
  - US equities/ETFs (ticker);
  - crypto (`CRYPTO:<BASE>`);
  - forex (`FOREX:<CCY>`).
- **Unsupported instruments.** Indian equities, mutual funds, rates and any other class get `status: unavailable` with the reason `NO_NEWS_PROVIDER_FOR_ASSET`. Google News RSS was removed because robots.txt disallows `/rss/search`.
- **Processing.** HTML, whitespace and Unicode normalisation → de-duplication (URL, normalised headline) → **entity linking** → **FinBERT** → stored.
  - Linking: provider ticker tags with relevance ≥ 0.6 are explicit links; otherwise alias matching from the Instrument Master (strong 0.95, weak 0.70, exclusion phrases); links below 0.6 are dropped.
  - FinBERT: the existing model with unchanged inference (sentences ≤ 64 tokens, probabilities averaged); loaded once per process.
- **No-news states.**
  - `no_relevant_news`: the provider answered, but nothing was linked.
  - `unavailable`: no provider, missing key or provider error, with the reason.
  - `stale_cache`: the provider failed, so stored items are shown.
- **Timestamps.** Alpha Vantage `time_published` has no timezone. It is **assumed to be UTC**, and the assumption is recorded in `provider_meta.timezone_assumed`.
- **Event category.** Transparent keyword rules; the matched keywords are returned.

## 6. Cross-source correlation (`ml/correlation`) and temporal analysis (`ml/temporal`)

For a flagged observation D, candidate news is news on the same instrument published in [open(D) − 24 h, close(D) + 12 h]. Session bounds come from the instrument's calendar; 24/7 markets use the UTC day.

`correlation_score = 0.30·temporal_proximity + 0.25·asset_match + 0.20·|sentiment| + 0.25·anomaly_score` (the ML Pipeline §24 starting formula).

- Temporal proximity is 1 inside the session, decaying linearly to 0 at the window edges.
- Semantic relevance (all-MiniLM-L6-v2) is reported and used as a tie-breaker, not in the score.
- Every match states its relation: before the open, during the session or after the close, with hours.
- Lead/lag: correlation of daily mean sentiment with returns at lags −3…+3 days, only with ≥ 20 news days.
- Language is associative only ("temporally associated with").

## 7. Risk (`ml/risk/scoring.py`)

`risk = 100 × [0.25·anomaly + 0.20·fingerprint + anomaly × (0.15·|sentiment| + 0.20·correlation + 0.10·temporal + 0.10·agreement)]`

**Documented refinement of ML Pipeline §27 (anomaly gate).** Without the gate, ordinary sessions scored risk ≈ 48 merely because news existed. Context terms are therefore scaled by the anomaly score.

- Contributions are reported per component and decompose the score exactly.
- Without news the basis is `market_only_no_aligned_news` or `market_only_news_unavailable`.
- Levels: ≥ 75 HIGH, ≥ 50 ELEVATED, ≥ 25 MODERATE.
- SHAP is not used: there is no trained risk model.

## 8. Evidence chain (`ml/evidence/chain.py`)

Items are time-ordered. Each item has a type, signal, description, value, source, URL, the gap from the previous item and **`provenance`**:

- **Market items:** provider, provider symbol, retrieval time, currency, adjustment, value kind, staleness and how the value was derived.
- **News items:** publisher, URL, publication time and news ID. Sentiment items add the FinBERT model and version.
- **Risk:** the method and components.

Run-level versions (feature set, fingerprint, model, thresholds) are in the result's `versions`.

Items cover:
- each contributing feature;
- the ensemble;
- each aligned article, with its FinBERT output and correlation;
- any retrospective change point;
- the final risk.

`explanation` answers what / when / how unusual / which signals / which news / timing / why, and ends with the non-causal caveat. News is described as "temporally associated with".

## 9. Reproducibility and leakage controls

- Seeds: 42 for Isolation Forest, LOF and LSTM.
- Chronological splits only. Detectors never see the scored window, and ECDF normalisers are fitted on training scores.
- Every result records:
  - `instrument_id`, `asset`, `capabilities`, `feature_set`;
  - `versions` (feature set, fingerprint, model, thresholds, pipeline);
  - data provenance (`data_source`), the validation report, model metadata and parameters.
- `analysis_runs` stores full results.
