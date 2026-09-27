# EXP-03_synthetic_injection_multi_asset

Generated 2026-09-27T18:35:02Z by `py -3.12 -m ml.evaluation.run_experiments` (pipeline v0.1.0, seed 42).

**Objective.** Compare the statistical baseline, Isolation Forest, LOF, the behavioural fingerprint and the Aventra ensemble on controlled anomalies injected into real provider data, per asset class.

**Split.** chronological 70/15/15 (train/validation/test) of feature rows. Thresholds chosen on validation, metrics reported on test.

## Asset class: crypto

| Detector | ROC-AUC | PR-AUC | Precision@k | F1 @ val. threshold | FPR @ val. threshold |
|---|---|---|---|---|---|
| B1_statistical_zscore | 0.924 ± 0.045 (n=5) | 0.634 ± 0.100 (n=5) | 0.681 ± 0.051 (n=5) | 0.642 ± 0.075 (n=5) | 0.017 ± 0.007 (n=5) |
| B2_isolation_forest | 0.808 ± 0.012 (n=5) | 0.403 ± 0.141 (n=5) | 0.542 ± 0.094 (n=5) | 0.583 ± 0.112 (n=5) | 0.016 ± 0.009 (n=5) |
| lof | 0.946 ± 0.053 (n=5) | 0.724 ± 0.157 (n=5) | 0.700 ± 0.147 (n=5) | 0.660 ± 0.118 (n=5) | 0.011 ± 0.006 (n=5) |
| fingerprint_only | 0.903 ± 0.039 (n=5) | 0.515 ± 0.135 (n=5) | 0.567 ± 0.054 (n=5) | 0.611 ± 0.101 (n=5) | 0.008 ± 0.006 (n=5) |
| B3_ensemble_fingerprint_plus_anomaly | 0.927 ± 0.049 (n=5) | 0.671 ± 0.096 (n=5) | 0.636 ± 0.043 (n=5) | 0.551 ± 0.096 (n=5) | 0.014 ± 0.009 (n=5) |
| ablation_without_fingerprint | 0.917 ± 0.047 (n=5) | 0.682 ± 0.086 (n=5) | 0.636 ± 0.043 (n=5) | 0.583 ± 0.056 (n=5) | 0.016 ± 0.005 (n=5) |
| ablation_without_isolation_forest | 0.933 ± 0.048 (n=5) | 0.698 ± 0.127 (n=5) | 0.703 ± 0.063 (n=5) | 0.619 ± 0.044 (n=5) | 0.015 ± 0.009 (n=5) |
| ablation_without_statistical | 0.895 ± 0.039 (n=5) | 0.488 ± 0.132 (n=5) | 0.567 ± 0.054 (n=5) | 0.631 ± 0.087 (n=5) | 0.010 ± 0.006 (n=5) |

## Asset class: forex

| Detector | ROC-AUC | PR-AUC | Precision@k | F1 @ val. threshold | FPR @ val. threshold |
|---|---|---|---|---|---|
| B1_statistical_zscore | 0.992 ± 0.010 (n=4) | 0.806 ± 0.216 (n=4) | 0.792 ± 0.217 (n=4) | 0.764 ± 0.217 (n=4) | 0.009 ± 0.004 (n=4) |
| B2_isolation_forest | 0.986 ± 0.014 (n=4) | 0.779 ± 0.143 (n=4) | 0.750 ± 0.186 (n=4) | 0.720 ± 0.206 (n=4) | 0.012 ± 0.012 (n=4) |
| lof | 0.977 ± 0.021 (n=4) | 0.677 ± 0.234 (n=4) | 0.679 ± 0.205 (n=4) | 0.461 ± 0.290 (n=4) | 0.011 ± 0.007 (n=4) |
| fingerprint_only | 0.984 ± 0.011 (n=4) | 0.712 ± 0.182 (n=4) | 0.583 ± 0.250 (n=4) | 0.604 ± 0.272 (n=4) | 0.013 ± 0.012 (n=4) |
| B3_ensemble_fingerprint_plus_anomaly | 0.997 ± 0.004 (n=4) | 0.893 ± 0.139 (n=4) | 0.833 ± 0.167 (n=4) | 0.777 ± 0.310 (n=4) | 0.004 ± 0.004 (n=4) |
| ablation_without_fingerprint | 0.996 ± 0.006 (n=4) | 0.877 ± 0.166 (n=4) | 0.792 ± 0.217 (n=4) | 0.836 ± 0.187 (n=4) | 0.007 ± 0.007 (n=4) |
| ablation_without_isolation_forest | 0.993 ± 0.009 (n=4) | 0.820 ± 0.201 (n=4) | 0.792 ± 0.217 (n=4) | 0.836 ± 0.187 (n=4) | 0.007 ± 0.007 (n=4) |
| ablation_without_statistical | 0.986 ± 0.013 (n=4) | 0.784 ± 0.134 (n=4) | 0.708 ± 0.182 (n=4) | 0.736 ± 0.152 (n=4) | 0.008 ± 0.009 (n=4) |

## Asset class: mutual_fund

| Detector | ROC-AUC | PR-AUC | Precision@k | F1 @ val. threshold | FPR @ val. threshold |
|---|---|---|---|---|---|
| B1_statistical_zscore | 0.977 ± 0.033 (n=4) | 0.883 ± 0.130 (n=4) | 0.823 ± 0.133 (n=4) | 0.761 ± 0.102 (n=4) | 0.002 ± 0.004 (n=4) |
| B2_isolation_forest | 0.968 ± 0.014 (n=4) | 0.590 ± 0.178 (n=4) | 0.573 ± 0.139 (n=4) | 0.423 ± 0.100 (n=4) | 0.066 ± 0.052 (n=4) |
| lof | 0.934 ± 0.104 (n=4) | 0.631 ± 0.334 (n=4) | 0.615 ± 0.335 (n=4) | 0.590 ± 0.262 (n=4) | 0.047 ± 0.052 (n=4) |
| fingerprint_only | 0.945 ± 0.028 (n=4) | 0.444 ± 0.188 (n=4) | 0.375 ± 0.217 (n=4) | 0.379 ± 0.131 (n=4) | 0.062 ± 0.030 (n=4) |
| B3_ensemble_fingerprint_plus_anomaly | 0.997 ± 0.005 (n=4) | 0.917 ± 0.121 (n=4) | 0.896 ± 0.108 (n=4) | 0.751 ± 0.068 (n=4) | 0.005 ± 0.005 (n=4) |
| ablation_without_fingerprint | 0.996 ± 0.005 (n=4) | 0.928 ± 0.095 (n=4) | 0.896 ± 0.108 (n=4) | 0.781 ± 0.075 (n=4) | 0.012 ± 0.010 (n=4) |
| ablation_without_isolation_forest | 0.997 ± 0.004 (n=4) | 0.921 ± 0.114 (n=4) | 0.896 ± 0.108 (n=4) | 0.686 ± 0.146 (n=4) | 0.013 ± 0.014 (n=4) |
| ablation_without_statistical | 0.962 ± 0.023 (n=4) | 0.526 ± 0.193 (n=4) | 0.531 ± 0.130 (n=4) | 0.456 ± 0.144 (n=4) | 0.057 ± 0.027 (n=4) |

## Data

- **CRYPTO:BTC-USDT** (crypto, feature set `ohlcv_continuous`) — 1826 observations from `binance` (`BTCUSDT`, fetched 2026-09-27T18:28:08Z, sha1 238031c1581f1f66); train 2021-09-28→2025-03-27, validation 2025-03-28→2025-12-26, test 2025-12-27→2026-09-26.
- **CRYPTO:ETH-USDT** (crypto, feature set `ohlcv_continuous`) — 1826 observations from `binance` (`ETHUSDT`, fetched 2026-09-27T18:28:10Z, sha1 e35437e8ba2f5b4d); train 2021-09-28→2025-03-27, validation 2025-03-28→2025-12-26, test 2025-12-27→2026-09-26.
- **CRYPTO:SOL-USDT** (crypto, feature set `ohlcv_continuous`) — 1826 observations from `binance` (`SOLUSDT`, fetched 2026-09-27T18:34:40Z, sha1 8e4cda03dcd5f891); train 2021-09-28→2025-03-27, validation 2025-03-28→2025-12-26, test 2025-12-27→2026-09-26.
- **CRYPTO:BNB-USDT** (crypto, feature set `ohlcv_continuous`) — 1826 observations from `binance` (`BNBUSDT`, fetched 2026-09-27T18:34:43Z, sha1 c238b56cad19fd04); train 2021-09-28→2025-03-27, validation 2025-03-28→2025-12-26, test 2025-12-27→2026-09-26.
- **CRYPTO:XRP-USDT** (crypto, feature set `ohlcv_continuous`) — 1826 observations from `binance` (`XRPUSDT`, fetched 2026-09-27T18:34:46Z, sha1 36ff021a46e29c09); train 2021-09-28→2025-03-27, validation 2025-03-28→2025-12-26, test 2025-12-27→2026-09-26.
- **FX:USDINR** (forex, feature set `close`) — 1280 observations from `frankfurter` (`USDINR`, fetched 2026-09-27T18:26:02Z, sha1 0003233788c969c7); train 2021-09-28→2025-03-25, validation 2025-03-26→2025-12-23, test 2025-12-24→2026-09-25.
- **FX:EURUSD** (forex, feature set `close`) — 1280 observations from `frankfurter` (`EURUSD`, fetched 2026-09-27T18:34:49Z, sha1 88e3fdfc1d65104d); train 2021-09-28→2025-03-25, validation 2025-03-26→2025-12-23, test 2025-12-24→2026-09-25.
- **FX:GBPUSD** (forex, feature set `close`) — 1280 observations from `frankfurter` (`GBPUSD`, fetched 2026-09-27T18:34:51Z, sha1 71c92efe6cd29dcf); train 2021-09-28→2025-03-25, validation 2025-03-26→2025-12-23, test 2025-12-24→2026-09-25.
- **FX:USDJPY** (forex, feature set `close`) — 1280 observations from `frankfurter` (`USDJPY`, fetched 2026-09-27T18:34:53Z, sha1 12d27ea6d44c6d5a); train 2021-09-28→2025-03-25, validation 2025-03-26→2025-12-23, test 2025-12-24→2026-09-25.
- **MF-IN:135762** (mutual_fund, feature set `close`) — 1239 observations from `mfapi` (`135762`, fetched 2026-09-27T18:26:01Z, sha1 22478db5872d75d1); train 2021-09-28→2025-04-01, validation 2025-04-02→2025-12-30, test 2025-12-31→2026-09-25.
- **MF-IN:122639** (mutual_fund, feature set `close`) — 1230 observations from `mfapi` (`122639`, fetched 2026-09-27T18:34:57Z, sha1 632cb15e30cea86f); train 2021-09-28→2025-03-27, validation 2025-03-28→2025-12-26, test 2025-12-29→2026-09-25.
- **MF-IN:118482** (mutual_fund, feature set `close`) — 1240 observations from `mfapi` (`118482`, fetched 2026-09-27T18:34:59Z, sha1 688f538ca0753c27); train 2021-09-28→2025-04-01, validation 2025-04-02→2025-12-30, test 2025-12-31→2026-09-25.
- **MF-IN:119091** (mutual_fund, feature set `close`) — 1591 observations from `mfapi` (`119091`, fetched 2026-09-27T18:35:01Z, sha1 3b2617feffb2a1dd); train 2021-09-28→2025-04-11, validation 2025-04-14→2026-01-06, test 2026-01-07→2026-09-27.

## Limitations

- Genuine unlabelled anomalies in real series count as false positives (precision is a lower bound).
- Injection types/magnitudes are design choices; results do not measure real-world detection performance.
- Injection types depend on the data an asset provides (no volume/range injections for close-only series).
- Few instruments per class and one seed each; standard deviations across instruments are reported, not confidence intervals.
