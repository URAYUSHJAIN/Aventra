# EXP-01_synthetic_injection

Generated 2026-09-27T15:03:14Z by `py -3.12 -m ml.evaluation.run_experiments` (pipeline v0.1.0, seed 42).

**Objective.** Compare the statistical baseline, Isolation Forest, LOF, the behavioural fingerprint and the Aventra ensemble on controlled anomalies injected into real NSE daily data.

**Split.** chronological 70/15/15 (train/validation/test) of feature rows. Thresholds chosen on validation, metrics reported on test.

## Results on the test segment (mean ± std across assets)

| Detector | ROC-AUC | PR-AUC | Precision@k | F1 @ val. threshold | FPR @ val. threshold |
|---|---|---|---|---|---|
| B1_statistical_zscore | 0.948 ± 0.046 | 0.713 ± 0.090 | 0.713 ± 0.078 | 0.748 ± 0.097 | 0.007 ± 0.004 |
| B2_isolation_forest | 0.875 ± 0.082 | 0.420 ± 0.149 | 0.468 ± 0.156 | 0.438 ± 0.116 | 0.036 ± 0.036 |
| lof | 0.909 ± 0.083 | 0.606 ± 0.151 | 0.578 ± 0.123 | 0.338 ± 0.229 | 0.069 ± 0.084 |
| fingerprint_only | 0.920 ± 0.063 | 0.496 ± 0.161 | 0.432 ± 0.162 | 0.340 ± 0.216 | 0.018 ± 0.013 |
| B3_ensemble_fingerprint_plus_anomaly | 0.922 ± 0.064 | 0.670 ± 0.130 | 0.651 ± 0.122 | 0.387 ± 0.219 | 0.022 ± 0.020 |
| ablation_without_fingerprint | 0.927 ± 0.056 | 0.736 ± 0.093 | 0.713 ± 0.078 | 0.604 ± 0.149 | 0.028 ± 0.026 |
| ablation_without_isolation_forest | 0.938 ± 0.059 | 0.739 ± 0.109 | 0.684 ± 0.097 | 0.638 ± 0.057 | 0.013 ± 0.007 |
| ablation_without_statistical | 0.889 ± 0.071 | 0.475 ± 0.169 | 0.501 ± 0.175 | 0.507 ± 0.076 | 0.023 ± 0.013 |
| experimental_lstm_autoencoder | 0.925 ± 0.055 | 0.557 ± 0.136 | 0.646 ± 0.173 | 0.551 ± 0.165 | 0.032 ± 0.027 |

## Data

- **RELIANCE** — 1235 sessions from `yahoo_finance_chart` (fetched 2026-09-27T15:02:55Z, sha1 94dd34c831540ab9); train 2021-09-27→2025-03-25, validation 2025-03-26→2025-12-23, test 2025-12-24→2026-09-25.
- **TCS** — 1235 sessions from `yahoo_finance_chart` (fetched 2026-09-27T15:03:01Z, sha1 31d31cad857ad869); train 2021-09-27→2025-03-25, validation 2025-03-26→2025-12-23, test 2025-12-24→2026-09-25.
- **INFY** — 1235 sessions from `yahoo_finance_chart` (fetched 2026-09-27T15:03:04Z, sha1 7704c4a14f25073a); train 2021-09-27→2025-03-25, validation 2025-03-26→2025-12-23, test 2025-12-24→2026-09-25.
- **HDFCBANK** — 1235 sessions from `yahoo_finance_chart` (fetched 2026-09-27T15:03:08Z, sha1 f1ec5b8e19b81fb5); train 2021-09-27→2025-03-25, validation 2025-03-26→2025-12-23, test 2025-12-24→2026-09-25.
- **ICICIBANK** — 1235 sessions from `yahoo_finance_chart` (fetched 2026-09-27T15:03:11Z, sha1 e9001c5285e51f5e); train 2021-09-27→2025-03-25, validation 2025-03-26→2025-12-23, test 2025-12-24→2026-09-25.

## Limitations

- Genuine unlabelled anomalies in the real series are counted as false positives (precision is a lower bound).
- Injection types and magnitudes are design choices; results do not measure real-world detection performance.
- News-dependent configurations (baseline 4, sentiment/correlation ablations) are not evaluated here: synthetic market injections have no associated news.
- Few assets and one seed per asset; standard deviations across assets are reported, not confidence intervals.
