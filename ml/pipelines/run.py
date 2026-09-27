"""CLI: run the full intelligence pipeline for one instrument (canonical ID, as in the Instrument Master).

    py -3.12 -m ml.pipelines.run --instrument CRYPTO:BTC-USDT
    py -3.12 -m ml.pipelines.run --instrument MF-IN:122639 --output data/processed/intelligence
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

from ml import config
from ml.instruments import ids
from ml.pipelines.intelligence import run_intelligence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Aventra intelligence pipeline for one instrument.")
    parser.add_argument("--instrument", "--symbol", dest="instrument", required=True, help="Canonical instrument ID, e.g. XNAS:AAPL (a bare NSE symbol is accepted)")
    parser.add_argument("--output", default=str(config.DATA_DIR / "processed" / "intelligence"), help="Directory for the JSON result")
    parser.add_argument("--no-persist", action="store_true", help="Do not write the result to the database")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

    instrument_id = str(ids.parse(args.instrument))
    result = run_intelligence(instrument_id, persist=not args.no_persist)
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{ids.safe_key(instrument_id)}.json"
    path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    current = result["current_assessment"]
    print(f"{instrument_id}: {len(result['events'])} flagged observation(s) in the scoring window; "
          f"latest {current['trading_date']} anomaly={current['anomaly']['anomaly_score']:.2f} ({current['anomaly']['severity']}), "
          f"risk={current['risk']['score']:.0f} ({current['risk']['level']}). Result: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
