"""CLI: run the pipeline for several instruments independently (a failure in one does not stop the others).

    py -3.12 -m ml.pipelines.batch --instruments CRYPTO:BTC-USDT,FX:USDINR,MF-IN:122639

For recurring analysis prefer the background worker (python -m ml.jobs.worker), which schedules the watchlist.
"""
from __future__ import annotations

import argparse
import logging

from ml.pipelines import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Aventra pipeline for several instruments.")
    parser.add_argument("--instruments", "--symbols", dest="instruments", required=True, help="Comma-separated canonical instrument IDs")
    args = parser.parse_args(argv)
    failures = 0
    for instrument_id in [s.strip() for s in args.instruments.split(",") if s.strip()]:
        try:
            run.main(["--instrument", instrument_id])
        except Exception as error:  # report and continue with the next instrument
            failures += 1
            logging.getLogger(__name__).error("Pipeline failed for %s: %s", instrument_id, error)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
