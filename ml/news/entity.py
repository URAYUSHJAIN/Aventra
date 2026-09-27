"""News → instrument linking (ML Pipeline §9). Low-confidence matches are never linked.

Aliases come from the Instrument Master (curated seed aliases, listing names with legal suffixes removed,
tickers). Matching is done only against the candidate instruments of a request, so it does not scale with the
size of the universe and never links an article to an unrelated instrument.
"""
from __future__ import annotations

import re

from ml import config
from ml.data import store
from ml.instruments.master import name_aliases

CONFIDENCE = {"explicit_metadata": 1.0, "strong_alias": 0.95, "weak_alias": 0.7}


def _contains(text: str, alias: str) -> bool:
    # Short upper-case aliases (tickers such as "TCS", "RIL") must match case-sensitively as whole words.
    flags = 0 if alias.isupper() and len(alias) <= 10 else re.IGNORECASE
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])", text, flags) is not None


def alias_profile(instrument: dict) -> dict:
    """strong/weak/exclude alias lists for one master row (falls back to name + ticker when none are stored)."""
    stored = instrument.get("aliases") or []
    profile = {"strong": [], "weak": [], "exclude": []}
    for alias in stored:
        kind = "strong" if alias["kind"] in {"strong", "ticker"} else alias["kind"]
        profile.setdefault(kind, []).append(alias["alias"])
    if not profile["strong"]:
        profile["strong"] = name_aliases(instrument.get("name", ""))
        symbol = instrument.get("symbol") or ""
        if len(symbol) >= 3 and symbol.isupper():   # very short tickers produce false matches in prose
            profile["strong"].append(symbol)
    return profile


def match_instrument(text: str, profile: dict) -> tuple[float, str] | None:
    scrubbed = text
    for phrase in profile.get("exclude", []):   # remove mentions of different companies sharing the name
        scrubbed = re.sub(re.escape(phrase), " ", scrubbed, flags=re.IGNORECASE)
    if any(_contains(scrubbed, alias) for alias in profile.get("strong", [])):
        return CONFIDENCE["strong_alias"], "strong_alias"
    if any(_contains(scrubbed, alias) for alias in profile.get("weak", [])):
        return CONFIDENCE["weak_alias"], "weak_alias"
    return None


def link_entities(headline: str, summary: str = "", explicit_ids: list[str] | None = None, candidates: list[str] | None = None,
                  profiles: dict[str, dict] | None = None) -> list[dict]:
    """Return [{instrument_id, entity_match_confidence, mapping_method}] at/above ENTITY_MIN_CONFIDENCE.

    `candidates`: instrument IDs to test (their aliases are loaded from the master unless `profiles` is given).
    """
    text = f"{headline} {summary}"
    links = {iid: (CONFIDENCE["explicit_metadata"], "explicit_metadata") for iid in (explicit_ids or [])}
    for iid in candidates or []:
        if iid in links:
            continue
        profile = (profiles or {}).get(iid)
        if profile is None:
            row = store.get_instrument(iid)
            if row is None:
                continue
            profile = alias_profile(row)
        match = match_instrument(text, profile)
        if match:
            links[iid] = match
    return [{"instrument_id": iid, "entity_match_confidence": confidence, "mapping_method": method}
            for iid, (confidence, method) in links.items() if confidence >= config.ENTITY_MIN_CONFIDENCE]
