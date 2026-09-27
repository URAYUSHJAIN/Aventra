"""Instrument Master service: normalisation, search (exact → prefix → alias → name → token match), pagination,
seed data and manual imports. Listing synchronisation from providers lives in ml/instruments/sync.py.
"""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import re
from pathlib import Path

from sqlalchemy import and_, case, exists, func, literal, or_, select

from ml import config
from ml.data import db, store
from ml.instruments import ids
from ml.instruments.profiles import CALENDAR_BY_EXCHANGE, TIMEZONE_BY_CALENDAR, profile_for

LEGAL_SUFFIXES = re.compile(r"\b(limited|ltd|inc|incorporated|corp|corporation|co|company|plc|llc|holdings?)\b\.?", re.IGNORECASE)
MAX_PAGE = 50


def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9& ]", " ", (text or "").lower())).strip()


def name_aliases(name: str) -> list[str]:
    """The name itself and the name without legal suffixes (e.g. 'Reliance Industries Ltd' → 'Reliance Industries')."""
    base = re.sub(r"\s+", " ", LEGAL_SUFFIXES.sub("", name or "")).strip(" .,-")
    return [a for a in dict.fromkeys([name.strip(), base]) if a and len(a) >= 3]


def instrument_row(instrument_id: str, symbol: str, name: str, asset_class: str, exchange: str, *, country=None, currency=None, isin=None,
                   source: str, class_source: str, class_confidence: float, status: str = "listed", capabilities: dict | None = None) -> dict:
    calendar = CALENDAR_BY_EXCHANGE.get(exchange)
    return {
        "instrument_id": instrument_id, "symbol": symbol, "name": name, "asset_class": asset_class, "exchange": exchange, "country": country,
        "currency": currency, "timezone": TIMEZONE_BY_CALENDAR.get(calendar or "", None), "calendar_code": calendar, "isin": isin, "status": status,
        "class_source": class_source, "class_confidence": class_confidence, "capabilities": profile_for(asset_class, capabilities), "source": source,
        "search_text": search_text(symbol, name),
    }


def search_text(symbol: str, name: str) -> str:
    """'axis children s fund axischildrensfund' — tokens plus a compact form so 'childrens' matches "Children's"."""
    normal = normalise(f"{symbol} {name}")
    return f"{normal} {normal.replace(' ', '')}"[:1000]


def alias_rows(instrument_id: str, strong: list[str] = (), weak: list[str] = (), exclude: list[str] = (), tickers: list[str] = (), source: str = "") -> list[dict]:
    rows = []
    for kind, values in (("strong", strong), ("weak", weak), ("exclude", exclude), ("ticker", tickers)):
        for value in values:
            if value and normalise(value):
                rows.append({"instrument_id": instrument_id, "alias": value, "alias_norm": normalise(value)[:200], "kind": kind, "source": source})
    return rows


# ------------------------------------------------------------------------------------------------- search
def _cursor_encode(offset: int) -> str:
    return base64.urlsafe_b64encode(json.dumps({"o": offset}).encode()).decode()


def _cursor_decode(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        return max(0, int(json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())["o"]))
    except (ValueError, KeyError, TypeError):
        return 0


def search(query: str, *, asset_class: str | None = None, exchange: str | None = None, country: str | None = None,
           limit: int = 20, cursor: str | None = None) -> dict:
    """Ranked, paginated search over the Instrument Master. Returns {items, next_cursor, total_estimate}."""
    q = (query or "").strip()
    qn, qu = normalise(q), q.upper()
    if len(qn) < 1:
        return {"items": [], "next_cursor": None}
    limit = max(1, min(limit, MAX_PAGE))
    offset = _cursor_decode(cursor)
    i, a = db.instruments, db.instrument_aliases
    tokens = [t for t in qn.split(" ") if t][:6]
    alias_exact = exists().where(and_(a.c.instrument_id == i.c.instrument_id, a.c.alias_norm == qn, a.c.kind != "exclude"))
    alias_prefix = exists().where(and_(a.c.instrument_id == i.c.instrument_id, a.c.alias_norm.like(f"{qn}%"), a.c.kind != "exclude"))
    name_l = func.lower(i.c.name)
    text = func.coalesce(i.c.search_text, func.lower(i.c.symbol) + literal(" ") + name_l)
    token_match = and_(*[text.like(f"%{t}%") for t in tokens]) if tokens else literal(False)
    # CoinGecko tickers are not unique (junk coins reuse "BITCOIN", "ETH", …), so an exact ticker match there ranks low.
    unique_symbols = i.c.exchange != "COINGECKO"
    rank = case(
        (func.upper(i.c.instrument_id) == qu, 0), (and_(unique_symbols, func.upper(i.c.symbol) == qu), 0),
        (name_l == q.lower(), 1), (alias_exact, 1), (and_(unique_symbols, func.upper(i.c.symbol).like(f"{qu}%")), 2),
        (name_l.like(f"{q.lower()}%"), 3), (alias_prefix, 4), (func.upper(i.c.symbol) == qu, 5), (name_l.like(f"%{q.lower()}%"), 6),
        (token_match, 7), else_=9)
    status_rank = case((i.c.status.in_(["listed", "resolved"]), 0), else_=1)
    popularity_missing = case((i.c.popularity.is_(None), 1), else_=0)
    stmt = select(i, rank.label("rank")).where(rank < 9)
    for column, value in (("asset_class", asset_class), ("exchange", exchange), ("country", country)):
        if value:
            stmt = stmt.where(getattr(i.c, column) == value)
    stmt = stmt.order_by(rank, status_rank, popularity_missing, i.c.popularity, func.length(i.c.symbol), i.c.instrument_id).offset(offset).limit(limit + 1)
    with db.get_engine().connect() as conn:
        rows = [dict(r) for r in conn.execute(stmt).mappings().all()]
    has_more = len(rows) > limit
    items = [_public(row) for row in rows[:limit]]
    return {"items": items, "next_cursor": _cursor_encode(offset + limit) if has_more else None}


def _public(row: dict) -> dict:
    return {k: row.get(k) for k in ("instrument_id", "symbol", "name", "asset_class", "exchange", "country", "currency", "timezone", "status",
                                    "class_source", "class_confidence", "capabilities", "isin")} | ({"match_rank": row["rank"]} if "rank" in row else {})


def get(instrument_id: str) -> dict | None:
    row = store.get_instrument(instrument_id)
    if not row:
        return None
    public = _public(row)
    public["aliases"] = row["aliases"]
    public["providers"] = [{k: p[k] for k in ("provider", "provider_symbol", "priority", "last_ok_at", "last_error")} for p in row["providers"]]
    public["calendar_code"], public["benchmark_id"], public["source"] = row["calendar_code"], row["benchmark_id"], row["source"]
    return public


# ------------------------------------------------------------------------------------------------- seeds and imports
def seed_from_reference() -> int:
    """Seed the master with the v0.1 reference assets (data/reference/assets.json) — a seed, not the universe.
    Keeps their curated aliases/exclusions for news matching. The synthetic DEMO asset is never seeded."""
    raw = json.loads((config.REFERENCE_DIR / "assets.json").read_text(encoding="utf-8"))
    rows, aliases = [], []
    for asset in raw["assets"]:
        if asset.get("is_demo"):
            continue
        iid = ids.make("XNSE", asset["symbol"])
        rows.append(instrument_row(iid, asset["symbol"], asset["name"], "equity", "XNSE", country="IN", currency="INR", source="reference_seed",
                                   class_source="reference_seed", class_confidence=1.0))
        al = asset.get("aliases", {})
        aliases += alias_rows(iid, strong=al.get("strong", []), weak=al.get("weak", []), exclude=al.get("exclude", []), tickers=[asset["symbol"]], source="reference_seed")
    store.upsert_instruments(rows, aliases)
    return len(rows)


def import_nse_listing(path: str | Path) -> dict:
    """Manual import of an NSE listing file the USER downloaded (EQUITY_L.csv or eq_etfseclist.csv).
    Automated/scheduled NSE downloads are prohibited by NSE's Terms of Use (docs/06, AGENTS.md C22)."""
    path = Path(path)
    if path.suffix.lower() != ".csv" or path.stat().st_size > 20_000_000:
        raise ValueError("Expected an NSE listing CSV file under 20 MB.")
    content = path.read_bytes()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8", errors="replace")))
    fields = {f.strip().upper(): f for f in (reader.fieldnames or [])}
    is_etf = "UNDERLYING ASSET" in fields
    symbol_col = fields.get("SYMBOL")
    name_col = fields.get("SECURITYNAME") if is_etf else fields.get("NAME OF COMPANY")
    isin_col = fields.get("ISINNUMBER") if is_etf else fields.get("ISIN NUMBER")
    if not (symbol_col and name_col):
        raise ValueError("Unrecognised NSE listing format (expected EQUITY_L.csv or eq_etfseclist.csv columns).")
    rows, aliases = [], []
    for record in reader:
        symbol = (record.get(symbol_col) or "").strip().upper()
        name = (record.get(name_col) or "").strip()
        if not symbol or not ids.CODE_PATTERN.match(symbol):
            continue
        iid = ids.make("XNSE", symbol)
        upper = name.upper()
        asset_class = ("etf" if is_etf else "invit" if re.search(r"\bINVIT\b|INFRA(STRUCTURE)? INVESTMENT TRUST", upper)
                       else "reit" if re.search(r"\bREIT\b|REAL ESTATE INVESTMENT TRUST", upper) else "equity")
        rows.append(instrument_row(iid, symbol, name, asset_class, "XNSE", country="IN", currency="INR", isin=(record.get(isin_col) or "").strip() or None,
                                   source="nse_manual_import", class_source="nse_etf_list" if is_etf else "nse_equity_list", class_confidence=1.0 if is_etf else 0.9))
        aliases += alias_rows(iid, strong=name_aliases(name), tickers=[symbol], source="nse_manual_import")
    store.upsert_instruments(rows, aliases)
    store.record_listing_snapshot("nse_manual_import", len(rows), hashlib.sha256(content).hexdigest(), "ok", note=path.name)
    return {"imported": len(rows), "kind": "etf" if is_etf else "equity"}


def ensure_default_watchlist() -> list[str]:
    """Default watchlist comes from configuration (AVENTRA_DEFAULT_WATCHLIST), never from code."""
    import os
    configured = [part.strip() for part in os.getenv("AVENTRA_DEFAULT_WATCHLIST", "").split(",") if part.strip()]
    valid = []
    for raw in configured:
        try:
            valid.append(str(ids.parse(raw, allow_legacy=False)))
        except ids.InvalidInstrumentId:
            continue
    existing = store.get_watchlist()
    if valid and (not existing or existing["items"] != valid):
        store.save_watchlist("default", valid, is_default=True)
    return valid or (existing["items"] if existing else [])
