"""Run EXP-01 (synthetic injection) and write results to experiments/results/.

    py -3.12 -m ml.evaluation.run_experiments                  # all analysed NSE assets
    py -3.12 -m ml.evaluation.run_experiments --symbols TCS --no-lstm

Results are only what this command computes; re-running with the same data and seed reproduces them.
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
from ml.data.assets import all_assets
from ml.evaluation.synthetic import run_symbol
from ml.pipelines.intelligence import load_benchmark, load_market

EXP_ID = "EXP-01_synthetic_injection"


def _mean_std(values):
    values = [v for v in values if v is not None]
    return {"mean": float(np.mean(values)), "std": float(np.std(values)), "n": len(values)} if values else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbols", default=",".join(a.symbol for a in all_assets() if not a.is_demo))
    parser.add_argument("--no-lstm", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    benchmark, bench_info = load_benchmark(False)
    per_symbol, provenance = {}, {}
    for offset, symbol in enumerate([s.strip().upper() for s in args.symbols.split(",") if s.strip()]):
        bars, source, report = load_market(symbol)
        digest = hashlib.sha1(bars[["open", "high", "low", "close", "volume"]].to_numpy(dtype=float).tobytes()).hexdigest()[:16]
        provenance[symbol] = {"source": source, "rows_after_validation": report["rows_out"], "data_sha1": digest}
        logging.info("EXP-01 %s: %d bars", symbol, len(bars))
        per_symbol[symbol] = run_symbol(bars, benchmark, seed=config.RANDOM_SEED + offset, include_lstm=not args.no_lstm)

    detector_names = next(iter(per_symbol.values()))["detectors"].keys()
    summary = {}
    for name in detector_names:
        rows = [per_symbol[s]["detectors"][name] for s in per_symbol]
        summary[name] = {
            "roc_auc": _mean_std([r["roc_auc"] for r in rows]), "pr_auc": _mean_std([r["pr_auc"] for r in rows]),
            "precision_at_k": _mean_std([r["precision_at_k"] for r in rows]),
            "f1_at_validation_threshold": _mean_std([r["at_validation_threshold"]["f1"] for r in rows]),
            "fpr_at_validation_threshold": _mean_std([r["at_validation_threshold"]["fpr"] for r in rows]),
        }

    result = {
        "experiment_id": EXP_ID, "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "pipeline_version": config.PIPELINE_VERSION,
        "objective": "Compare the statistical baseline, Isolation Forest, LOF, the behavioural fingerprint and the Aventra ensemble on controlled anomalies injected into real NSE daily data.",
        "random_seed": config.RANDOM_SEED, "split": "chronological 70/15/15 (train/validation/test) of feature rows",
        "benchmark": bench_info, "data_provenance": provenance, "ensemble_weights": config.ENSEMBLE_WEIGHTS, "default_threshold": config.ANOMALY_THRESHOLD,
        "summary_mean_over_assets": summary, "per_symbol": per_symbol,
        "limitations": [
            "Genuine unlabelled anomalies in the real series are counted as false positives (precision is a lower bound).",
            "Injection types and magnitudes are design choices; results do not measure real-world detection performance.",
            "News-dependent configurations (baseline 4, sentiment/correlation ablations) are not evaluated here: synthetic market injections have no associated news.",
            "Few assets and one seed per asset; standard deviations across assets are reported, not confidence intervals.",
        ],
    }
    config.EXPERIMENT_DIR.mkdir(parents=True, exist_ok=True)
    (config.EXPERIMENT_DIR / f"{EXP_ID}.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    (config.EXPERIMENT_DIR / f"{EXP_ID}.md").write_text(_markdown(result), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")   # Windows consoles default to cp1252
    print(_markdown(result))
    return 0


def _fmt(stat):
    return "n/a" if not stat else f"{stat['mean']:.3f} ± {stat['std']:.3f}"


def _markdown(result: dict) -> str:
    lines = [f"# {result['experiment_id']}", "", f"Generated {result['generated_at']} by `py -3.12 -m ml.evaluation.run_experiments` (pipeline v{result['pipeline_version']}, seed {result['random_seed']}).", "",
             f"**Objective.** {result['objective']}", "", f"**Split.** {result['split']}. Thresholds chosen on validation, metrics reported on test.", "",
             "## Results on the test segment (mean ± std across assets)", "",
             "| Detector | ROC-AUC | PR-AUC | Precision@k | F1 @ val. threshold | FPR @ val. threshold |", "|---|---|---|---|---|---|"]
    for name, s in result["summary_mean_over_assets"].items():
        lines.append(f"| {name} | {_fmt(s['roc_auc'])} | {_fmt(s['pr_auc'])} | {_fmt(s['precision_at_k'])} | {_fmt(s['f1_at_validation_threshold'])} | {_fmt(s['fpr_at_validation_threshold'])} |")
    lines += ["", "## Data", ""]
    for symbol, info in result["data_provenance"].items():
        ranges = result["per_symbol"][symbol]["date_ranges"]
        lines.append(f"- **{symbol}** — {info['rows_after_validation']} sessions from `{info['source']['provider']}` (fetched {info['source'].get('fetched_at')}, sha1 {info['data_sha1']}); train {ranges['train'][0]}→{ranges['train'][1]}, validation {ranges['validation'][0]}→{ranges['validation'][1]}, test {ranges['test'][0]}→{ranges['test'][1]}.")
    lines += ["", "## Limitations", ""] + [f"- {item}" for item in result["limitations"]]
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
