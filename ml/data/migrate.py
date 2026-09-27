"""Run Alembic migrations programmatically (backend startup, worker startup, CLI).

    py -3.12 -m ml.data.migrate            # upgrade to head
    py -3.12 -m ml.data.migrate current    # show current revision
"""
from __future__ import annotations

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from ml.data import db

INI = Path(__file__).resolve().parents[2] / "backend" / "alembic.ini"


def alembic_config(url: str | None = None) -> Config:
    cfg = Config(str(INI))
    cfg.attributes["url"] = url or db.database_url()
    return cfg


def upgrade(url: str | None = None) -> None:
    command.upgrade(alembic_config(url), "head")


def main(argv: list[str]) -> int:
    action = argv[0] if argv else "upgrade"
    if action == "current":
        command.current(alembic_config(), verbose=True)
    else:
        upgrade()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
