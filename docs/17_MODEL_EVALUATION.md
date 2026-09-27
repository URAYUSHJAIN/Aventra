# 17 — Model Evaluation

Every number below was produced by the command shown and is stored in `experiments/results/`. Re-running a command on the same data reproduces its numbers. Live data changes daily, so each JSON records a SHA-1 of the exact observations used.

## EXP-03 — Synthetic anomaly injection on real multi-asset data (current)

- **Command:** `py -3.12 -m ml.evaluation.run_experiments --no-lstm --instruments CRYPTO:BTC-USDT,CRYPTO:ETH-USDT,CRYPTO:SOL-USDT,CRYPTO:BNB-USDT,CRYPTO:XRP-USDT,FX:USDINR,FX:EURUSD,FX:GBPUSD,FX:USDJPY,MF-IN:135762,MF-IN:122639,MF-IN:118482,MF-IN:119091`
- **Results:** `experiments/results/EXP-03_synthetic_injection_multi_asset.{json,md}` (run on 2026-09-27T18:35Z, seed 42).

**Data (real, keyless providers):**
- Crypto: 1,826 daily OHLCV bars from Binance per instrument (`ohlcv_continuous`).
- Forex: 1,280 daily ECB reference rates from Frankfurter (`close`).
- Mutual funds: 1,230–1,591 daily NAVs from mfapi.in (`close`). The liquid fund 119091 publishes NAVs on calendar days.
- All series run from 2021-09-28 to 2026-09-27.

**Protocol:**
- Chronological 70/15/15 split.
- Injection types depend on what the data provides: price jumps for every class; volume, volatility and combined injections only for OHLCV.
- Injections go into the validation and test segments only.
- ML detectors are fitted on the clean training segment. Thresholds are chosen on validation; metrics are reported on test.
- Results are summarised **per asset class, never pooled**, as mean ± standard deviation across instruments.
- The LSTM autoencoder was excluded (`--no-lstm`) to keep the run short.

| Class (n) | Detector | ROC-AUC | PR-AUC | Precision@k | F1 @ val. thr. | FPR @ val. thr. |
|---|---|---|---|---|---|---|
| crypto (5) | B1 statistical z-score | 0.924 ± 0.045 | 0.634 ± 0.100 | 0.681 ± 0.051 | 0.642 ± 0.075 | 0.017 ± 0.007 |
| | B2 Isolation Forest | 0.808 ± 0.012 | 0.403 ± 0.141 | 0.542 ± 0.094 | 0.583 ± 0.112 | 0.016 ± 0.009 |
| | LOF | 0.946 ± 0.053 | 0.724 ± 0.157 | 0.700 ± 0.147 | 0.660 ± 0.118 | 0.011 ± 0.006 |
| | fingerprint only | 0.903 ± 0.039 | 0.515 ± 0.135 | 0.567 ± 0.054 | 0.611 ± 0.101 | 0.008 ± 0.006 |
| | **B3 ensemble (production)** | 0.927 ± 0.049 | 0.671 ± 0.096 | 0.636 ± 0.043 | 0.551 ± 0.096 | 0.014 ± 0.009 |
| | ensemble without Isolation Forest | 0.933 ± 0.048 | 0.698 ± 0.127 | 0.703 ± 0.063 | 0.619 ± 0.044 | 0.015 ± 0.009 |
| forex (4) | B1 statistical z-score | 0.992 ± 0.010 | 0.806 ± 0.216 | 0.792 ± 0.217 | 0.764 ± 0.217 | 0.009 ± 0.004 |
| | B2 Isolation Forest | 0.986 ± 0.014 | 0.779 ± 0.143 | 0.750 ± 0.186 | 0.720 ± 0.206 | 0.012 ± 0.012 |
| | LOF | 0.977 ± 0.021 | 0.677 ± 0.234 | 0.679 ± 0.205 | 0.461 ± 0.290 | 0.011 ± 0.007 |
| | fingerprint only | 0.984 ± 0.011 | 0.712 ± 0.182 | 0.583 ± 0.250 | 0.604 ± 0.272 | 0.013 ± 0.012 |
| | **B3 ensemble (production)** | 0.997 ± 0.004 | 0.893 ± 0.139 | 0.833 ± 0.167 | 0.777 ± 0.310 | 0.004 ± 0.004 |
| mutual fund (4) | B1 statistical z-score | 0.977 ± 0.033 | 0.883 ± 0.130 | 0.823 ± 0.133 | 0.761 ± 0.102 | 0.002 ± 0.004 |
| | B2 Isolation Forest | 0.968 ± 0.014 | 0.590 ± 0.178 | 0.573 ± 0.139 | 0.423 ± 0.100 | 0.066 ± 0.052 |
| | LOF | 0.934 ± 0.104 | 0.631 ± 0.334 | 0.615 ± 0.335 | 0.590 ± 0.262 | 0.047 ± 0.052 |
| | fingerprint only | 0.945 ± 0.028 | 0.444 ± 0.188 | 0.375 ± 0.217 | 0.379 ± 0.131 | 0.062 ± 0.030 |
| | **B3 ensemble (production)** | 0.997 ± 0.005 | 0.917 ± 0.121 | 0.896 ± 0.108 | 0.751 ± 0.068 | 0.005 ± 0.005 |

All ablations (without fingerprint / Isolation Forest / statistical) are in the result files.

Ensemble detections at the default threshold 0.65, per injection type (test segments, summed over instruments):

| Class | Price jump up | Price jump down | Volume spike | Volatility spike | Combined |
|---|---|---|---|---|---|
| crypto | 7/9 | 9/9 | 1/10 | 0/9 | 7/7 |
| forex | 6/12 | 8/13 | — | — | — |
| mutual fund | 5/13 | 12/13 | — | — | — |

**Interpretation (honest reading):**
- The production ensemble has the highest PR-AUC for forex and mutual funds. For crypto, LOF, the ensemble without the Isolation Forest and (on F1) the statistical baseline do better. The ensemble is **not** uniformly best.
- The ensemble detects price-jump and combined injections well. At the default threshold it misses almost all **single-day volume and volatility spikes** on crypto, the same weakness EXP-01 showed.
- It detects downward jumps more often than upward jumps in every class; the cause has not been investigated.
- Standard deviations are large: only 4–5 instruments per class, one seed each. These are not confidence intervals.
- On forex and mutual funds the Isolation Forest is much weaker on F1 and FPR than the statistical score, although it contributes to the ensemble.
- Synthetic injections on real series measure sensitivity to *designed* anomalies. They do not measure real-world detection; genuine unlabelled anomalies count as false positives.
- Not evaluated: equities, ETFs and indices (need keys), CoinGecko close+volume series, yields.

## EXP-01 — Synthetic anomaly injection on real NSE data (v0.1 record, superseded)

> **Provenance note:** EXP-01 was run in v0.1 on NSE prices obtained from Yahoo Finance's chart endpoint. Yahoo has since been removed from Aventra because its terms prohibit automated collection (docs/06). The record is kept for transparency and for comparison with EXP-03; it cannot be re-run with the current providers without an Upstox token.

Command (v0.1): `py -3.12 -m ml.evaluation.run_experiments` · Results: `experiments/results/EXP-01_synthetic_injection.{json,md}` · Code: `ml/evaluation/synthetic.py`.

**Protocol.** RELIANCE, TCS, INFY, HDFCBANK, ICICIBANK; 1,235 validated daily sessions each (2021-09-27 → 2026-09-25). Chronological 70/15/15 split. Price jumps (±5σ level shift), volume spikes (×4), volatility spikes (×3 range) and combined events (−4σ, ×3 volume) injected into validation and test segments only (≥ 25 sessions apart; 4–7 per test segment). ML detectors fitted on the clean train segment; thresholds chosen on validation; metrics on test.

| Detector | ROC-AUC | PR-AUC | Precision@k | F1 @ val. threshold | FPR @ val. threshold |
|---|---|---|---|---|---|
| B1 statistical z-score | 0.948 ± 0.046 | 0.713 ± 0.090 | 0.713 ± 0.078 | 0.748 ± 0.097 | 0.007 ± 0.004 |
| B2 Isolation Forest | 0.875 ± 0.082 | 0.420 ± 0.149 | 0.468 ± 0.156 | 0.438 ± 0.116 | 0.036 ± 0.036 |
| LOF | 0.909 ± 0.083 | 0.606 ± 0.151 | 0.578 ± 0.123 | 0.338 ± 0.229 | 0.069 ± 0.084 |
| Fingerprint only | 0.920 ± 0.063 | 0.496 ± 0.161 | 0.432 ± 0.162 | 0.340 ± 0.216 | 0.018 ± 0.013 |
| **B3 ensemble (production)** | 0.922 ± 0.064 | 0.670 ± 0.130 | 0.651 ± 0.122 | 0.387 ± 0.219 | 0.022 ± 0.020 |
| Ensemble without fingerprint | 0.927 ± 0.056 | 0.736 ± 0.093 | 0.713 ± 0.078 | 0.604 ± 0.149 | 0.028 ± 0.026 |
| Ensemble without Isolation Forest | 0.938 ± 0.059 | 0.739 ± 0.109 | 0.684 ± 0.097 | 0.638 ± 0.057 | 0.013 ± 0.007 |
| Ensemble without statistical | 0.889 ± 0.071 | 0.475 ± 0.169 | 0.501 ± 0.175 | 0.507 ± 0.076 | 0.023 ± 0.013 |
| LSTM autoencoder (experimental) | 0.925 ± 0.055 | 0.557 ± 0.136 | 0.646 ± 0.173 | 0.551 ± 0.165 | 0.032 ± 0.027 |

Mean ± standard deviation across the five assets.

**Interpretation (honest reading).**
- On these *synthetic, single-bar* anomalies the simple statistical baseline performs best, and the production ensemble does not beat it; removing the fingerprint or the Isolation Forest from the ensemble improves PR-AUC. The ensemble detects injected price jumps and combined events at the default threshold but misses most single-day volume or volatility spikes (per-type counts in the JSON).
- Validation-chosen thresholds generalise poorly (few validation injections per asset → unstable thresholds, 0.40–0.83 across assets): the ensemble's test F1 at the fixed default 0.65 is higher than at its validation-chosen threshold on 4 of 5 assets (exception: TCS, 0.625 vs 0.571). The default threshold was not tuned on these data.
- The injection design favours detectors that react to one-bar jumps. The fingerprint and Isolation Forest target multi-dimensional, asset-specific deviations, which this experiment does not isolate. The result therefore does **not** support a claim that behavioural fingerprinting improves detection; that question (research question 1) remains open.
- Next steps (not done): calibrate ensemble weights and threshold on validation data only; add multi-day and multi-feature injection types; more seeds per asset; a curated known-event benchmark.

**Limitations.** Real series contain genuine unlabelled anomalies counted as false positives; only five assets and one seed each; news-dependent configurations (baseline 4 and the news/sentiment/correlation ablations of ML Pipeline §47) cannot be evaluated with synthetic market injections.

## EXP-02 — FinBERT on Financial PhraseBank

Command: `py -3.12 -m ml.evaluation.finbert_phrasebank` · Results: `experiments/results/EXP-02_finbert_phrasebank_AllAgree.{json,md}`.

> **Disclosure:** ProsusAI/finBERT was fine-tuned on Financial PhraseBank. These numbers overlap with its training data and are **not** a generalisation estimate; they verify that Aventra's local model, label mapping and aggregation behave as expected.

Sentences_AllAgree (2,264 sentences, sha256-verified download): **accuracy 0.9717, macro-F1 0.9625** (positive F1 0.962, negative F1 0.943, neutral F1 0.983). CPU inference 125 s. Confusion matrix and per-class precision/recall are in the result files. Dataset licence CC BY-NC-SA 3.0; the file is downloaded to `data/external/` and not committed.

## Not yet evaluated

- **Known-event benchmark** (Final Plan §27): requires a curated, sourced list of historical events per asset. Not created — events must not be invented. Template fields: event date, asset, category, market movement, volume behaviour, relevant news (with URL), expected detection window.
- **Correlation quality** (entity-matching accuracy, relevant-news precision): needs a hand-labelled sample of Alpha Vantage news items (requires a key).
- **Risk calibration**: needs labelled outcomes; the risk score is a transparent formula, not a validated predictor.
- **End-to-end metrics** (alerts/day, API latency under load): per-stage timings are recorded in each result (`timings_ms`); cold analyses of keyless instruments took 2–4 s in Docker after the one-off model load (2026-09-27).
