"""CLI: run the full intelligence pipeline for one asset.

    py -3.12 -m ml.pipelines.run --symbol DEMO
    py -3.12 -m ml.pipelines.run --symbol RELIANCE --output data/processed/intelligence
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from ml import config
from ml.pipelines.intelligence import run_intelligence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Aventra intelligence pipeline for one asset.")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--output", default=str(config.DATA_DIR / "processed" / "intelligence"), help="Directory for the JSON result")
    parser.add_argument("--no-persist", action="store_true", help="Do not write the result to the SQLite store")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    result = run_intelligence(args.symbol.upper(), persist=not args.no_persist)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{result['symbol']}.json"
    path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    current = result["current_assessment"]
    print(f"{result['symbol']}: {len(result['events'])} flagged session(s) in the scoring window; "
          f"latest {current['trading_date']} anomaly={current['anomaly']['anomaly_score']:.2f} ({current['anomaly']['severity']}), "
          f"risk={current['risk']['score']:.0f} ({current['risk']['level']}). Result: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
