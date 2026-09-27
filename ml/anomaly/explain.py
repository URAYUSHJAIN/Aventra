"""Human-readable explanations of fingerprint deviations (feature-level explainability)."""
from __future__ import annotations

import math

LABELS = {
    "return_1": "Daily return", "log_volume": "Trading volume", "volatility_20": "20-period volatility",
    "range_pct": "Intraday range", "gap_pct": "Opening gap", "relative_return": "Return relative to the benchmark",
    "drawdown": "Drawdown from peak", "ma20_distance": "Distance from 20-period mean", "change_bp": "Yield change",
    "volatility_bp_20": "Yield-change volatility", "level_distance_bp": "Yield versus 20-period mean",
}


def _pct(value: float) -> str:
    return f"{value * 100:+.2f}%"


def describe(dim: str, value: float, median: float, z: float) -> str:
    if dim == "log_volume":
        volume, typical = math.expm1(value), math.expm1(median)
        ratio = volume / typical if typical > 0 else float("nan")
        return f"Volume {volume:,.0f} was {ratio:.1f}× the baseline median ({typical:,.0f}); robust z = {z:+.1f}."
    if dim == "volatility_20":
        return f"20-day volatility {value * 100:.2f}% versus a baseline of {median * 100:.2f}%; robust z = {z:+.1f}."
    if dim == "range_pct":
        return f"Intraday range {value * 100:.2f}% of the previous close versus a typical {median * 100:.2f}%; robust z = {z:+.1f}."
    if dim in {"change_bp", "volatility_bp_20", "level_distance_bp"}:
        return f"{LABELS[dim]} {value:+.1f} bp versus a typical {median:+.1f} bp; robust z = {z:+.1f}."
    return f"{LABELS.get(dim, dim)} {_pct(value)} versus a typical {_pct(median)}; robust z = {z:+.1f}."


def contributing_features(row, dims: list[str], features_row, top: int = 4, min_abs_z: float = 2.0) -> list[dict]:
    """Dimensions ranked by |robust z|; only deviations beyond `min_abs_z` are listed."""
    items = []
    for dim in dims:
        z = row.get(f"z_{dim}")
        if z is None or (isinstance(z, float) and math.isnan(z)) or abs(z) < min_abs_z:
            continue
        value, median = float(features_row[dim]), float(row[f"median_{dim}"])
        items.append({
            "feature": dim, "label": LABELS.get(dim, dim), "value": round(value, 6), "baseline_median": round(median, 6),
            "robust_z": round(float(z), 3), "direction": "above" if z > 0 else "below", "deviation_score": round(float(row[f"score_{dim}"]), 4),
            "explanation": describe(dim, value, median, float(z)),
        })
    return sorted(items, key=lambda item: abs(item["robust_z"]), reverse=True)[:top]
