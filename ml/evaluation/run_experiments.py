"""Synthetic anomaly injection on REAL provider data, per asset class (EXP-03; EXP-01 is the v0.1 NSE-only record).

    py -3.12 -m ml.evaluation.run_experiments --instruments CRYPTO:BTC-USDT,FX:USDINR,MF-IN:135762
    py -3.12 -m ml.evaluation.run_experiments --instruments ... --no-lstm --id EXP-03_multi_asset

Instruments are loaded through the Instrument Master and provider router (real data only; unavailable instruments
are recorded as skipped with their reason). Results are summarised per asset class — never pooled across classes.
Re-running with the same data and seed reproduces the results; each record stores a SHA-1 of the bars used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
from datetime import datetime, timezone

import numpy as np

from ml import config
from ml.data import migrate
from ml.data.market_data import capability_profile, load_series
from ml.evaluation.synthetic import run_symbol
from ml.features.sets import select_set
from ml.pipelines.intelligence import InsufficientHistory, UnknownAsset, load_benchmark, resolve_instrument
from ml.providers.registry import DataUnavailable

DEFAULT_ID = "EXP-03_synthetic_injection_multi_asset"
MIN_BARS = 250


def _mean_std(values):
    values = [v for v in values if v is not None]
    return {"mean": float(np.mean(values)), "std": float(np.std(values)), "n": len(values)} if values else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instruments", required=True, help="Comma-separated instrument IDs")
    parser.add_argument("--no-lstm", action="store_true")
    parser.add_argument("--id", default=DEFAULT_ID)
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    migrate.upgrade()

    per_instrument, provenance, skipped = {}, {}, {}
    for offset, raw in enumerate([s.strip() for s in args.instruments.split(",") if s.strip()]):
        try:
            instrument = resolve_instrument(raw)
            bars, source, report = load_series(instrument)
        except (UnknownAsset, DataUnavailable, InsufficientHistory, ValueError) as error:
            skipped[raw] = {"reason": getattr(error, "code", type(error).__name__), "detail": str(error)[:200]}
            continue
        iid = instrument["instrument_id"]
        if len(bars) < MIN_BARS:
            skipped[iid] = {"reason": "INSUFFICIENT_HISTORY", "detail": f"{len(bars)} observations < {MIN_BARS}"}
            continue
        profile = capability_profile(instrument)
        benchmark, bench_info = load_benchmark(instrument)
        digest = hashlib.sha1(bars[["close"]].to_numpy(dtype=float).tobytes()).hexdigest()[:16]
        provenance[iid] = {"asset_class": instrument["asset_class"], "feature_set": select_set(profile), "provider": source["provider"],
                           "provider_symbol": source["provider_symbol"], "fetched_at": source.get("fetched_at"), "rows_after_validation": report["rows_out"],
                           "data_sha1": digest, "benchmark": bench_info}
        logging.info("%s: %s, %d observations from %s", args.id, iid, len(bars), source["provider"])
        per_instrument[iid] = run_symbol(bars, benchmark, seed=config.RANDOM_SEED + offset, include_lstm=not args.no_lstm, profile=profile)

    by_class: dict[str, dict] = {}
    for iid, result in per_instrument.items():
        cls = provenance[iid]["asset_class"]
        for name, metrics in result["detectors"].items():
            bucket = by_class.setdefault(cls, {}).setdefault(name, {"roc_auc": [], "pr_auc": [], "precision_at_k": [], "f1_val": [], "fpr_val": []})
            bucket["roc_auc"].append(metrics["roc_auc"]); bucket["pr_auc"].append(metrics["pr_auc"]); bucket["precision_at_k"].append(metrics["precision_at_k"])
            bucket["f1_val"].append(metrics["at_validation_threshold"]["f1"]); bucket["fpr_val"].append(metrics["at_validation_threshold"]["fpr"])
    summary = {cls: {name: {"roc_auc": _mean_std(v["roc_auc"]), "pr_auc": _mean_std(v["pr_auc"]), "precision_at_k": _mean_std(v["precision_at_k"]),
                            "f1_at_validation_threshold": _mean_std(v["f1_val"]), "fpr_at_validation_threshold": _mean_std(v["fpr_val"])}
                     for name, v in detectors.items()} for cls, detectors in by_class.items()}
    result = {
        "experiment_id": args.id, "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "pipeline_version": config.PIPELINE_VERSION,
        "objective": "Compare the statistical baseline, Isolation Forest, LOF, the behavioural fingerprint and the Aventra ensemble on controlled anomalies injected into real provider data, per asset class.",
        "random_seed": config.RANDOM_SEED, "split": "chronological 70/15/15 (train/validation/test) of feature rows",
        "data_provenance": provenance, "skipped": skipped, "ensemble_weights": config.ENSEMBLE_WEIGHTS, "default_threshold": config.ANOMALY_THRESHOLD,
        "summary_by_asset_class": summary, "per_instrument": per_instrument,
        "limitations": [
            "Genuine unlabelled anomalies in real series count as false positives (precision is a lower bound).",
            "Injection types/magnitudes are design choices; results do not measure real-world detection performance.",
            "Injection types depend on the data an asset provides (no volume/range injections for close-only series).",
            "Few instruments per class and one seed each; standard deviations across instruments are reported, not confidence intervals.",
        ],
    }
    config.EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    (config.EXPERIMENT_DIR / f"{args.id}.json").write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    (config.EXPERIMENT_DIR / f"{args.id}.md").write_text(_markdown(result), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")   # Windows consoles default to cp1252
    print(_markdown(result))
    return 0


def _fmt(stat):
    return "n/a" if not stat else f"{stat['mean']:.3f} ± {stat['std']:.3f} (n={stat['n']})"


def _markdown(result: dict) -> str:
    lines = [f"# {result['experiment_id']}", "", f"Generated {result['generated_at']} by `py -3.12 -m ml.evaluation.run_experiments` (pipeline v{result['pipeline_version']}, seed {result['random_seed']}).", "",
             f"**Objective.** {result['objective']}", "", f"**Split.** {result['split']}. Thresholds chosen on validation, metrics reported on test.", ""]
    for cls, detectors in result["summary_by_asset_class"].items():
        lines += [f"## Asset class: {cls}", "", "| Detector | ROC-AUC | PR-AUC | Precision@k | F1 @ val. threshold | FPR @ val. threshold |", "|---|---|---|---|---|---|"]
        for name, s in detectors.items():
            lines.append(f"| {name} | {_fmt(s['roc_auc'])} | {_fmt(s['pr_auc'])} | {_fmt(s['precision_at_k'])} | {_fmt(s['f1_at_validation_threshold'])} | {_fmt(s['fpr_at_validation_threshold'])} |")
        lines.append("")
    lines += ["## Data", ""]
    for iid, info in result["data_provenance"].items():
        ranges = result["per_instrument"][iid]["date_ranges"]
        lines.append(f"- **{iid}** ({info['asset_class']}, feature set `{info['feature_set']}`) — {info['rows_after_validation']} observations from `{info['provider']}` "
                     f"(`{info['provider_symbol']}`, fetched {info['fetched_at']}, sha1 {info['data_sha1']}); train {ranges['train'][0]}→{ranges['train'][1]}, "
                     f"validation {ranges['validation'][0]}→{ranges['validation'][1]}, test {ranges['test'][0]}→{ranges['test'][1]}.")
    if result["skipped"]:
        lines += ["", "## Skipped (no legitimate data available)", ""] + [f"- {iid}: {v['reason']} — {v['detail']}" for iid, v in result["skipped"].items()]
    lines += ["", "## Limitations", ""] + [f"- {item}" for item in result["limitations"]]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
