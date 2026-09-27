# 17 — Model Evaluation

All numbers below were produced by the commands shown, on 2026-09-27, and are stored in `experiments/results/`. Re-running the commands with the same data reproduces them; live data changes daily, so each JSON records a SHA-1 of the exact bars used.

## EXP-01 — Synthetic anomaly injection on real NSE data

Command: `py -3.12 -m ml.evaluation.run_experiments` · Results: `experiments/results/EXP-01_synthetic_injection.{json,md}` · Code: `ml/evaluation/synthetic.py`.

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
- **Correlation quality** (entity-matching accuracy, relevant-news precision): needs a hand-labelled sample of RSS items.
- **Risk calibration**: needs labelled outcomes; the risk score is a transparent formula, not a validated predictor.
- **End-to-end metrics** (alerts/day, API latency under load): per-stage timings are recorded in each result (`timings_ms`); cold full-pipeline runs took 9–30 s locally, dominated by model loading and provider calls.
