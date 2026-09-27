"""News → asset linking (ML Pipeline §9). Low-confidence matches are never linked."""
from __future__ import annotations

import re

from ml import config
from ml.data.assets import Asset, all_assets

CONFIDENCE = {"explicit_metadata": 1.0, "strong_alias": 0.95, "weak_alias": 0.7}


def _contains(text: str, alias: str) -> bool:
    # Short upper-case aliases (tickers such as "TCS", "RIL") must match case-sensitively as whole words.
    flags = 0 if alias.isupper() and len(alias) <= 10 else re.IGNORECASE
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])", text, flags) is not None


def match_asset(text: str, asset: Asset) -> tuple[float, str] | None:
    scrubbed = text
    for phrase in asset.exclude_phrases:   # remove mentions of different companies sharing the name
        scrubbed = re.sub(re.escape(phrase), " ", scrubbed, flags=re.IGNORECASE)
    if any(_contains(scrubbed, alias) for alias in asset.strong_aliases):
        return CONFIDENCE["strong_alias"], "strong_alias"
    if any(_contains(scrubbed, alias) for alias in asset.weak_aliases):
        return CONFIDENCE["weak_alias"], "weak_alias"
    return None


def link_entities(headline: str, summary: str = "", explicit_symbols: list[str] | None = None) -> list[dict]:
    """Return [{symbol, entity_match_confidence, mapping_method}] for matches at/above ENTITY_MIN_CONFIDENCE."""
    text = f"{headline} {summary}"
    links = {symbol: (CONFIDENCE["explicit_metadata"], "explicit_metadata") for symbol in (explicit_symbols or [])}
    for asset in all_assets():
        if asset.symbol in links:
            continue
        match = match_asset(text, asset)
        if match:
            links[asset.symbol] = match
    return [
        {"symbol": symbol, "entity_match_confidence": confidence, "mapping_method": method}
        for symbol, (confidence, method) in links.items() if confidence >= config.ENTITY_MIN_CONFIDENCE
    ]
