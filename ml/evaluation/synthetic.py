"""EXP-01 — Controlled synthetic anomaly injection on real NSE histories (Final Plan §28, ML Pipeline §44–47).

Protocol
1. Real daily bars per asset (validated, holiday placeholders removed); chronological split of
   feature rows: 70 % train / 15 % validation / 15 % test. No shuffling.
2. Anomalies are injected into the raw bars of the validation and test segments only, sized
   relative to the asset's own train-period return volatility σ:
   price_jump_up / price_jump_down (persistent level shift of ±5σ from the bar onward),
   volume_spike (×4 volume), volatility_spike (×3 intraday range, close unchanged),
   combined (−4σ shift and ×3 volume). Injections are ≥ 25 bars apart.
3. Features are recomputed on the injected bars (past-only, so earlier rows are unaffected).
4. ML detectors are fitted on the clean train segment only. Decision thresholds are chosen on
   the validation segment (max F1) and applied unchanged to the test segment.
5. Metrics on the test segment: ROC-AUC, PR-AUC (average precision), precision@k (k = number
   of injections), and precision / recall / F1 / FPR at the validation-chosen threshold.

Limitation: the real series contain genuine unlabelled anomalies; detections of those count as
false positives, so precision is a lower bound. Synthetic results are reported separately from
any real-world evaluation and are not evidence of real-world detection performance.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

from ml import config
from ml.anomaly.detectors import UnsupervisedDetector
from ml.anomaly.ensemble import combine
from ml.anomaly.lstm_autoencoder import LstmAutoencoderDetector
from ml.anomaly.statistical import statistical_scores
from ml.features.engineering import compute_features
from ml.features.sets import FEATURE_SETS, select_set
from ml.fingerprint.baseline import compute_fingerprint

TYPES = ("price_jump_up", "price_jump_down", "volume_spike", "volatility_spike", "combined")
MIN_GAP = 25
N_PER_SEGMENT = 10


def split_bounds(n: int) -> tuple[int, int]:
    return int(n * 0.70), int(n * 0.85)


def injection_types(profile: dict) -> tuple[str, ...]:
    """Only anomaly types the instrument's data can express (no volume spikes in a NAV series, no range spikes without OHLC)."""
    if profile.get("value_kind") == "yield":
        return ("level_shift_up", "level_shift_down")
    types = ["price_jump_up", "price_jump_down"]
    if profile.get("has_volume"):
        types += ["volume_spike", "combined"]
    if profile.get("has_ohlc"):
        types.append("volatility_spike")
    return tuple(types)


def inject(bars: pd.DataFrame, positions: list[int], kinds: list[str], sigma: float, has_ohlc: bool = True) -> pd.DataFrame:
    out = bars.copy().reset_index(drop=True)
    for t, kind in zip(positions, kinds):
        if kind in ("level_shift_up", "level_shift_down"):   # yields: persistent shift of ±5σ basis-point changes
            out.loc[t:, "close"] += (5 if kind == "level_shift_up" else -5) * sigma / 100
            continue
        if kind in ("price_jump_up", "price_jump_down", "combined"):
            m = {"price_jump_up": 5 * sigma, "price_jump_down": -5 * sigma, "combined": -4 * sigma}[kind]
            factor = 1 + m
            out.loc[t:, "close"] *= factor
            if has_ohlc:
                out.loc[t:, ["high", "low"]] *= factor
                out.loc[t + 1:, "open"] *= factor
                out.loc[t, "high"] = max(out.loc[t, "high"], out.loc[t, "open"], out.loc[t, "close"])
                out.loc[t, "low"] = min(out.loc[t, "low"], out.loc[t, "open"], out.loc[t, "close"])
        if kind in ("volume_spike", "combined"):
            out.loc[t, "volume"] *= 4 if kind == "volume_spike" else 3
        if kind == "volatility_spike":
            close, half_range = out.loc[t, "close"], (out.loc[t, "high"] - out.loc[t, "low"]) * 1.5
            out.loc[t, "high"] = max(close + half_range, out.loc[t, "open"])
            out.loc[t, "low"] = min(close - half_range, out.loc[t, "open"])
    return out


def choose_positions(rng: np.random.Generator, start: int, end: int, count: int) -> list[int]:
    candidates = list(range(start + 5, end - 5))
    chosen: list[int] = []
    for t in rng.permutation(candidates):
        if all(abs(int(t) - c) >= MIN_GAP for c in chosen):
            chosen.append(int(t))
        if len(chosen) == count:
            break
    return sorted(chosen)


def _metrics_at(scores: np.ndarray, labels: np.ndarray, threshold: float) -> dict:
    predicted = scores >= threshold
    tp = int((predicted & labels).sum()); fp = int((predicted & ~labels).sum()); fn = int((~predicted & labels).sum()); tn = int((~predicted & ~labels).sum())
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"threshold": round(float(threshold), 4), "precision": precision, "recall": recall, "f1": f1, "fpr": fp / (fp + tn) if fp + tn else 0.0, "tp": tp, "fp": fp, "fn": fn}


def _best_threshold(scores: np.ndarray, labels: np.ndarray) -> float:
    candidates = np.unique(np.round(scores, 4))
    best, best_f1 = 1.0, -1.0
    for threshold in candidates:
        f1 = _metrics_at(scores, labels, threshold)["f1"]
        if f1 > best_f1 or (f1 == best_f1 and threshold > best):
            best, best_f1 = float(threshold), f1
    return best


def evaluate_scores(scores: np.ndarray, labels: np.ndarray, val_mask: np.ndarray, test_mask: np.ndarray) -> dict:
    valid = ~np.isnan(scores)
    val, test = val_mask & valid, test_mask & valid
    s_test, y_test = scores[test], labels[test]
    threshold = _best_threshold(scores[val], labels[val])
    k = int(y_test.sum())
    top_k = np.argsort(-s_test, kind="stable")[:k]
    return {
        "roc_auc": float(roc_auc_score(y_test, s_test)) if 0 < k < len(y_test) else None,
        "pr_auc": float(average_precision_score(y_test, s_test)) if k else None,
        "precision_at_k": float(y_test[top_k].mean()) if k else None,
        "at_validation_threshold": _metrics_at(s_test, y_test, threshold),
        "at_default_threshold": _metrics_at(s_test, y_test, config.ANOMALY_THRESHOLD),
        "test_rows_scored": int(test.sum()), "test_injections": k,
    }


def run_symbol(bars: pd.DataFrame, benchmark: pd.DataFrame | None, seed: int, include_lstm: bool = True, profile: dict | None = None) -> dict:
    profile = profile or {"has_ohlc": True, "has_volume": True, "value_kind": "price"}
    feature_set = FEATURE_SETS[select_set(profile)]
    types = injection_types(profile)
    rng = np.random.default_rng(seed)
    n = len(bars)
    train_end, val_end = split_bounds(n)
    clean = compute_features(bars, benchmark, profile)
    sigma = float(clean["change_bp" if profile.get("value_kind") == "yield" else "return_1"].iloc[:train_end].std())
    val_pos = choose_positions(rng, train_end, val_end, N_PER_SEGMENT)
    test_pos = choose_positions(rng, val_end, n, N_PER_SEGMENT)
    kinds = [types[i % len(types)] for i in range(len(val_pos) + len(test_pos))]
    injected = inject(bars, val_pos + test_pos, kinds, sigma, bool(profile.get("has_ohlc")))
    feats = compute_features(injected, benchmark, profile)

    labels = np.zeros(n, dtype=bool); labels[val_pos + test_pos] = True
    idx = np.arange(n)
    val_mask, test_mask = (idx >= train_end) & (idx < val_end), idx >= val_end
    train = feats.iloc[:train_end]

    fp, _ = compute_fingerprint(feats, feature_set["fingerprint"])
    stat = statistical_scores(feats, feature_set["statistical"])["statistical_score"].to_numpy()
    iso = UnsupervisedDetector("isolation_forest").fit(train, feature_set["detector"]).score(feats)
    lof = UnsupervisedDetector("lof").fit(train, feature_set["detector"]).score(feats)
    fingerprint = fp["fingerprint_score"].to_numpy()

    def ensemble(weights: dict) -> np.ndarray:
        frame = pd.DataFrame({"statistical": stat, "fingerprint": fingerprint, "isolation_forest": iso})
        return combine(frame, weights)["anomaly_score"].to_numpy()

    w = config.ENSEMBLE_WEIGHTS
    detectors = {
        "B1_statistical_zscore": stat,
        "B2_isolation_forest": iso,
        "lof": lof,
        "fingerprint_only": fingerprint,
        "B3_ensemble_fingerprint_plus_anomaly": ensemble(w),
        "ablation_without_fingerprint": ensemble({**w, "fingerprint": 0.0}),
        "ablation_without_isolation_forest": ensemble({**w, "isolation_forest": 0.0}),
        "ablation_without_statistical": ensemble({**w, "statistical": 0.0}),
    }
    if include_lstm:
        detectors["experimental_lstm_autoencoder"] = LstmAutoencoderDetector(seed=seed).fit(train, feature_set["detector"]).score(feats)

    by_type = {}
    for kind in types:
        kind_labels = np.zeros(n, dtype=bool)
        kind_labels[[p for p, k in zip(val_pos + test_pos, kinds) if k == kind]] = True
        other = labels & ~kind_labels
        mask = test_mask & ~other   # evaluate each type against normal bars only
        s = detectors["B3_ensemble_fingerprint_plus_anomaly"]
        hits = [bool(s[p] >= config.ANOMALY_THRESHOLD) for p, k in zip(test_pos, kinds[len(val_pos):]) if k == kind]
        by_type[kind] = {"test_injections": len(hits), "detected_at_default_threshold": int(sum(hits))} if mask.any() else {}

    return {
        "rows": n, "train_rows": train_end, "validation_rows": val_end - train_end, "test_rows": n - val_end,
        "date_ranges": {name: [str(feats["trading_date"].iloc[a].date()), str(feats["trading_date"].iloc[b - 1].date())] for name, (a, b) in {"train": (0, train_end), "validation": (train_end, val_end), "test": (val_end, n)}.items()},
        "train_return_sigma": sigma, "injections": {"validation": len(val_pos), "test": len(test_pos)},
        "detectors": {name: evaluate_scores(np.asarray(scores, dtype=float), labels, val_mask, test_mask) for name, scores in detectors.items()},
        "ensemble_detection_by_type": by_type,
    }
