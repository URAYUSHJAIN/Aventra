"""Asset-class capability profiles (what data a class provides and which calendar/features apply).

A profile describes what the *class* can provide; the instrument's stored `capabilities` may narrow it after
real data has been inspected (e.g. an index whose provider reports no volume).
"""
from __future__ import annotations

ASSET_CLASSES = ("equity", "etf", "reit", "invit", "bond", "index", "mutual_fund", "forex", "crypto", "rate", "commodity")

PROFILES: dict[str, dict] = {
    "equity":      {"has_ohlc": True,  "has_volume": True,  "value_kind": "price",          "minimum_history": 80},
    "etf":         {"has_ohlc": True,  "has_volume": True,  "value_kind": "price",          "minimum_history": 80},
    "reit":        {"has_ohlc": True,  "has_volume": True,  "value_kind": "price",          "minimum_history": 80},
    "invit":       {"has_ohlc": True,  "has_volume": True,  "value_kind": "price",          "minimum_history": 80},
    "bond":        {"has_ohlc": True,  "has_volume": True,  "value_kind": "price",          "minimum_history": 80},   # exchange-traded, often sparse
    "index":       {"has_ohlc": True,  "has_volume": False, "value_kind": "index_level",    "minimum_history": 80},
    "mutual_fund": {"has_ohlc": False, "has_volume": False, "value_kind": "nav",            "minimum_history": 80},
    "forex":       {"has_ohlc": False, "has_volume": False, "value_kind": "reference_rate", "minimum_history": 80},
    "crypto":      {"has_ohlc": True,  "has_volume": True,  "value_kind": "price",          "minimum_history": 80},
    "rate":        {"has_ohlc": False, "has_volume": False, "value_kind": "yield",          "minimum_history": 80},
    "commodity":   {"has_ohlc": False, "has_volume": False, "value_kind": "price",          "minimum_history": 80},
}

# Calendar per exchange namespace. NSE has no exchange_calendars entry; BSE (XBOM) shares its sessions and holidays
# (verified in Phase 0: differences only on Muhurat/special sessions), so it is used as a documented proxy.
CALENDAR_BY_EXCHANGE = {
    "XNSE": "XBOM", "XBOM": "XBOM", "XNAS": "XNYS", "XNYS": "XNYS", "XASE": "XNYS", "ARCX": "XNYS", "BATS": "XNYS",
    "BINANCE": "24/7", "COINGECKO": "24/7", "FX": "24/5", "AMFI": "XBOM", "FRED": "XNYS", "NSE_INDEX": "XBOM", "BSE_INDEX": "XBOM",
}
TIMEZONE_BY_CALENDAR = {"XBOM": "Asia/Kolkata", "XNYS": "America/New_York", "24/7": "UTC", "24/5": "UTC"}


def profile_for(asset_class: str, overrides: dict | None = None) -> dict:
    base = dict(PROFILES.get(asset_class, PROFILES["equity"]))
    base.update(overrides or {})
    return base
