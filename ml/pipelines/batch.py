"""CLI: run the pipeline for several assets independently (a failure in one does not stop the others).

    py -3.12 -m ml.pipelines.batch --symbols RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK
"""
from __future__ import annotations

import argparse
import logging

from ml.pipelines import run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Aventra pipeline for several assets.")
    parser.add_argument("--symbols", required=True, help="Comma-separated symbols")
    args = parser.parse_args(argv)
    failures = 0
    for symbol in [s.strip().upper() for s in args.symbols.split(",") if s.strip()]:
        try:
            run.main(["--symbol", symbol])
        except Exception as error:  # report and continue with the next asset
            failures += 1
            logging.getLogger(__name__).error("Pipeline failed for %s: %s", symbol, error)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
