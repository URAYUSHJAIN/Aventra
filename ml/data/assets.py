"""Asset registry loaded from data/reference/assets.json."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache

from ml import config

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9&^.\-]{1,20}$")


@dataclass(frozen=True)
class Asset:
    symbol: str
    name: str
    exchange: str
    provider_symbol: str | None
    sector: str = ""
    is_demo: bool = False
    strong_aliases: tuple[str, ...] = field(default_factory=tuple)
    weak_aliases: tuple[str, ...] = field(default_factory=tuple)
    exclude_phrases: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict:
        return {"symbol": self.symbol, "name": self.name, "exchange": self.exchange, "sector": self.sector, "is_demo": self.is_demo}


@lru_cache(maxsize=1)
def _registry() -> tuple[dict[str, Asset], dict]:
    raw = json.loads((config.REFERENCE_DIR / "assets.json").read_text(encoding="utf-8"))
    assets = {}
    for item in raw["assets"]:
        aliases = item.get("aliases", {})
        assets[item["symbol"]] = Asset(
            symbol=item["symbol"], name=item["name"], exchange=item["exchange"], provider_symbol=item.get("provider_symbol"),
            sector=item.get("sector", ""), is_demo=bool(item.get("is_demo", False)),
            strong_aliases=tuple(aliases.get("strong", [])), weak_aliases=tuple(aliases.get("weak", [])), exclude_phrases=tuple(aliases.get("exclude", [])),
        )
    return assets, raw["benchmark"]


def all_assets() -> list[Asset]:
    return list(_registry()[0].values())


def get_asset(symbol: str) -> Asset | None:
    return _registry()[0].get(symbol.upper())


def benchmark() -> dict:
    return dict(_registry()[1])


def normalize_symbol(symbol: str) -> str | None:
    """Uppercase and strip an exchange suffix; return None when the format is invalid."""
    if not isinstance(symbol, str):
        return None
    cleaned = symbol.strip().upper()
    if cleaned.endswith(".NS"):
        cleaned = cleaned[:-3]
    return cleaned if SYMBOL_PATTERN.match(cleaned) else None


def provider_symbol_for(symbol: str) -> str:
    """Yahoo symbol for a registry asset, or `<SYMBOL>.NS` for other NSE equities (quotes only)."""
    asset = get_asset(symbol)
    if asset and asset.provider_symbol:
        return asset.provider_symbol
    return symbol if symbol.startswith("^") else f"{symbol}.NS"
