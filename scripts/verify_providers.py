"""Phase 0 — reproducible verification of candidate market/reference data providers.

    py -3.12 -m scripts.verify_providers

Makes a small number of polite requests per provider (delays between calls) and writes
data/reference/provider_verification.json with the raw evidence (status codes, counts,
date ranges, fields present). It does not change application behaviour; Phase 2 builds
the provider capability matrix from these results. Re-run before relying on a provider:
availability and limits change.
"""
from __future__ import annotations

import csv
import io
import json
import sys
import time
from datetime import datetime, timezone

import requests

from ml import config

UA_BROWSER = {"User-Agent": "Mozilla/5.0 (Aventra research prototype)"}
UA_SEC = {"User-Agent": "Aventra B.Tech research project (ABES Engineering College) contact: aventra-research@example.invalid"}
TIMEOUT = 25
results: list[dict] = []


def record(provider: str, check: str, ok: bool, **evidence) -> None:
    results.append({"provider": provider, "check": check, "ok": ok, **evidence})
    flag = "OK  " if ok else "FAIL"
    print(f"[{flag}] {provider:22s} {check:44s} {json.dumps(evidence, default=str)[:170]}")


def get(url, *, headers=UA_BROWSER, params=None, delay=0.4):
    time.sleep(delay)
    return requests.get(url, headers=headers, params=params, timeout=TIMEOUT)


def epoch(date: str) -> int:
    return int(datetime.fromisoformat(date).replace(tzinfo=timezone.utc).timestamp())


# ---------------------------------------------------------------- Yahoo (unofficial, best effort)
def yahoo():
    base = "https://query1.finance.yahoo.com"
    samples = {
        "equity_in": "TCS.NS", "equity_us": "AAPL", "etf_in": "NIFTYBEES.NS", "etf_us": "SPY", "index_in": "^NSEI", "index_us": "^GSPC",
        "reit_in": "EMBASSY.NS", "forex": "USDINR=X", "crypto": "BTC-USD", "commodity_future": "GC=F", "bond_yield": "^TNX",
        "mutual_fund_us": "VFIAX", "mutual_fund_in": "0P0000XVKP.BO", "equity_bse_short_history": "RELIANCE.BO",
    }
    for label, sym in samples.items():
        r = get(f"{base}/v8/finance/chart/{requests.utils.quote(sym, safe='')}", params={"period1": epoch("2016-01-01"), "period2": epoch("2026-09-27"), "interval": "1d"})
        try:
            res = r.json()["chart"]["result"][0]
            meta, q = res["meta"], res["indicators"]["quote"][0]
            ts = res.get("timestamp", [])
            record("yahoo_chart", f"daily history {label} ({sym})", len(ts) > 250, http=r.status_code, bars=len(ts),
                   first=datetime.fromtimestamp(ts[0], timezone.utc).date() if ts else None, granularity=meta.get("dataGranularity"),
                   instrumentType=meta.get("instrumentType"), exchange=meta.get("exchangeName"), timezone=meta.get("exchangeTimezoneName"),
                   currency=meta.get("currency"), nonzero_volume=sum(1 for v in (q.get("volume") or []) if v), validRanges=meta.get("validRanges"))
        except Exception as error:  # record the failure as evidence
            record("yahoo_chart", f"daily history {label} ({sym})", False, http=r.status_code, error=str(error)[:80], body=r.text[:80])
    r = get(f"{base}/v8/finance/chart/TCS.NS", params={"range": "max", "interval": "1d"})
    record("yahoo_chart", "range=max keeps daily granularity", r.json()["chart"]["result"][0]["meta"].get("dataGranularity") == "1d",
           granularity=r.json()["chart"]["result"][0]["meta"].get("dataGranularity"))
    for interval, rng in (("5m", "60d"), ("1m", "7d"), ("1m", "30d")):
        r = get(f"{base}/v8/finance/chart/TCS.NS", params={"range": rng, "interval": interval})
        body = r.json()["chart"]
        record("yahoo_chart", f"intraday {interval} over {rng}", body.get("result") is not None, http=r.status_code,
               bars=len((body.get("result") or [{}])[0].get("timestamp", []) or []), error=(body.get("error") or {}).get("description"))
    for query in ("reliance", "embassy office parks", "EMBASSY", "mindspace reit", "bitcoin", "gold", "usd inr", "hdfc mutual fund", "treasury yield", "nifty bank"):
        r = get(f"{base}/v1/finance/search", params={"q": query, "quotesCount": 20, "newsCount": 0})
        quotes = r.json().get("quotes", []) if r.ok else []
        record("yahoo_search", f"search '{query}'", bool(quotes), http=r.status_code, results=len(quotes),
               sample=[(q.get("symbol"), q.get("quoteType")) for q in quotes[:5]])


# ---------------------------------------------------------------- official listings
def nse():
    for name, url in (("equities EQUITY_L.csv", "https://archives.nseindia.com/content/equities/EQUITY_L.csv"),
                      ("ETFs eq_etfseclist.csv", "https://archives.nseindia.com/content/equities/eq_etfseclist.csv")):
        r = get(url)
        rows = list(csv.DictReader(io.StringIO(r.text))) if r.ok else []
        record("nse_archives", name, r.ok and len(rows) > 100, http=r.status_code, rows=len(rows), columns=list(rows[0].keys())[:8] if rows else None)
        if "ETF" in name and rows:
            bond_etfs = [row.get("Symbol") for row in rows if "BOND" in (str(row.get("Underlying Asset", "")) + str(row.get("SecurityName", ""))).upper()]
            gold_etfs = [row.get("Symbol") for row in rows if "GOLD" in (str(row.get("Underlying Asset", "")) + str(row.get("SecurityName", ""))).upper()]
            record("nse_archives", "ETF list contains bond / gold ETFs", bool(bond_etfs and gold_etfs), bond_etfs=len(bond_etfs), gold_etfs=len(gold_etfs), bond_sample=bond_etfs[:3])
    r = get("https://archives.nseindia.com/content/equities/REIT_L.csv")
    record("nse_archives", "REIT/InvIT listing file", r.ok, http=r.status_code)


def bse():
    r = get("https://api.bseindia.com/BseIndiaAPI/api/ListofScripData/w", params={"segment": "Equity", "status": "Active"}, headers={**UA_BROWSER, "Referer": "https://www.bseindia.com/"})
    record("bse_api", "scrip master", r.ok, http=r.status_code)


def sec():
    r = get("https://www.sec.gov/files/company_tickers_exchange.json", headers=UA_SEC, delay=0.2)
    data = r.json() if r.ok else {}
    exchanges = {}
    for row in data.get("data", []):
        exchanges[row[3]] = exchanges.get(row[3], 0) + 1
    record("sec", "company_tickers_exchange.json", r.ok, http=r.status_code, rows=len(data.get("data", [])), fields=data.get("fields"), by_exchange=exchanges)


def nasdaq_trader():
    for name in ("nasdaqlisted", "otherlisted", "mfundslist"):
        r = get(f"https://www.nasdaqtrader.com/dynamic/SymDir/{name}.txt")
        lines = [line for line in r.text.splitlines() if line.strip()] if r.ok else []
        header = lines[0].split("|") if lines else []
        etf_col = header.index("ETF") if "ETF" in header else None
        etfs = sum(1 for line in lines[1:] if etf_col is not None and line.split("|")[etf_col:etf_col + 1] == ["Y"])
        is_data = bool(header) and header[0].strip() in {"Symbol", "ACT Symbol", "Fund Symbol"}   # an HTML page is not a symbol file
        record("nasdaq_trader", f"{name}.txt", r.ok and is_data and len(lines) > 10, http=r.status_code, rows=max(len(lines) - 2, 0) if is_data else 0,
               header=header[:8] if is_data else "not a pipe-delimited symbol file (HTML returned)", etf_rows=etfs)


# ---------------------------------------------------------------- mutual funds (India)
def amfi_and_mfapi():
    r = get("https://www.amfiindia.com/spages/NAVAll.txt")
    rows = [line.split(";") for line in r.text.splitlines() if line.count(";") >= 5 and line.split(";")[0].strip().isdigit()] if r.ok else []
    header = next((line for line in r.text.splitlines() if line.startswith("Scheme Code")), "")
    # NAV and date are the last two fields (the file gained Plan/Option columns; 8 fields as of 2026-09).
    amfi_nav = {row[0].strip(): (row[-2].strip(), row[-1].strip()) for row in rows}
    recent = sum(1 for nav, date in amfi_nav.values() if date.endswith("2026"))
    record("amfi", "NAVAll.txt (all schemes, latest NAV)", len(rows) > 1000, http=r.status_code, schemes=len(rows), header=header,
           field_counts=sorted({len(row) for row in rows}), schemes_with_2026_nav=recent, stale_or_inactive=len(rows) - recent)
    r = get("https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx", params={"frmdt": "01-Sep-2026", "todt": "05-Sep-2026"})
    record("amfi", "official NAV history report (date range)", r.ok and r.text.count(";") > 100, http=r.status_code, bytes=len(r.content), head=r.text[:60].replace("\n", " "))
    r = get("https://api.mfapi.in/mf")
    schemes = r.json() if r.ok else []
    record("mfapi_in", "scheme list", len(schemes) > 1000, http=r.status_code, schemes=len(schemes))
    matches = 0
    checked = [code for code in list(amfi_nav)[:400:80]]
    for code in checked:
        h = get(f"https://api.mfapi.in/mf/{code}")
        if h.ok and h.json().get("data"):
            latest = h.json()["data"][0]
            try:
                same = abs(float(latest["nav"]) - float(amfi_nav[code][0])) < 1e-3
            except ValueError:
                same = False
            matches += int(same)
            record("mfapi_in", f"history for AMFI code {code}", True, navs=len(h.json()["data"]), oldest=h.json()["data"][-1]["date"],
                   latest=latest, amfi_latest=amfi_nav[code], latest_matches_amfi=same)
        else:
            record("mfapi_in", f"history for AMFI code {code}", False, http=h.status_code)
    record("mfapi_in", "scheme codes are AMFI codes (latest NAV cross-check)", matches == len(checked), matched=matches, checked=len(checked))


# ---------------------------------------------------------------- crypto
def crypto():
    r = get("https://api.binance.com/api/v3/exchangeInfo")
    symbols = r.json().get("symbols", []) if r.ok else []
    trading = [s for s in symbols if s.get("status") == "TRADING"]
    quotes = {}
    for s in trading:
        quotes[s["quoteAsset"]] = quotes.get(s["quoteAsset"], 0) + 1
    record("binance", "exchangeInfo", bool(trading), http=r.status_code, symbols=len(symbols), trading=len(trading),
           top_quote_assets=sorted(quotes.items(), key=lambda kv: -kv[1])[:6], used_weight=r.headers.get("x-mbx-used-weight-1m"))
    r = get("https://api.binance.com/api/v3/klines", params={"symbol": "BTCUSDT", "interval": "1d", "startTime": epoch("2017-01-01") * 1000, "limit": 1000})
    rows = r.json() if r.ok else []
    record("binance", "klines 1d from 2017 (1000/request)", len(rows) == 1000, http=r.status_code, bars=len(rows),
           first=datetime.fromtimestamp(rows[0][0] / 1000, timezone.utc).date() if rows else None, fields="open,high,low,close,volume,quote_volume,trades",
           used_weight=r.headers.get("x-mbx-used-weight-1m"))
    r = get("https://api.exchange.coinbase.com/products")
    products = r.json() if r.ok else []
    record("coinbase_exchange", "public products", len(products) > 50, http=r.status_code, products=len(products))
    r = get("https://api.exchange.coinbase.com/products/BTC-USD/candles", params={"granularity": 86400})
    record("coinbase_exchange", "daily candles (max 300/request)", r.ok, http=r.status_code, bars=len(r.json()) if r.ok else 0)
    r = get("https://api.coingecko.com/api/v3/coins/list", delay=1.5)
    record("coingecko_keyless", "coins/list", r.ok, http=r.status_code, coins=len(r.json()) if r.ok else 0)
    for days in ("365", "max"):
        r = get("https://api.coingecko.com/api/v3/coins/bitcoin/market_chart", params={"vs_currency": "usd", "days": days}, delay=2.5)
        body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        record("coingecko_keyless", f"market_chart days={days}", r.ok and "prices" in body, http=r.status_code, points=len(body.get("prices", [])),
               error=(body.get("error") or body.get("status") or None) if not r.ok else None)


# ---------------------------------------------------------------- forex, rates, commodities, identifiers
def guarded(provider: str, check: str, fn) -> None:
    """Run one check; retry once after a pause on connection errors (FRED resets rapid successive downloads)."""
    for attempt in (1, 2):
        try:
            fn()
            return
        except requests.RequestException as error:
            if attempt == 2:
                record(provider, check, False, error=repr(error)[:140], note="connection failed twice (throttling or reset)")
            time.sleep(8)


def fx_rates_commodities():
    guarded("frankfurter/ecb", "fx block", _fx)
    for series in ("DGS10", "DGS2", "DCOILWTICO", "DCOILBRENTEU", "DEXINUS"):
        guarded("fred_csv_download", f"series {series}", lambda s=series: _fred_csv(s))
    guarded("fred_api", "API without key", _fred_api)
    guarded("openfigi", "ISIN mapping without key", _openfigi)
    guarded("openfigi", "filter: enumerate NSE (exchCode IN) listings", _openfigi_filter)


def _openfigi_filter():
    time.sleep(3)
    r = requests.post("https://api.openfigi.com/v3/filter", json={"exchCode": "IN", "securityType2": "Common Stock"}, headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
    body = r.json() if r.ok else {}
    record("openfigi", "filter: enumerate NSE (exchCode IN) listings", r.ok and bool(body.get("data")), http=r.status_code, total=body.get("total"),
           page_size=len(body.get("data", [])), has_next=bool(body.get("next")), sample=[(d.get("ticker"), d.get("name")) for d in body.get("data", [])[:3]],
           ratelimit=r.headers.get("ratelimit-limit"), error=None if r.ok else r.text[:100])


def _fred_csv(series: str) -> None:
    r = get("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": series}, delay=4)
    lines = r.text.splitlines() if r.ok else []
    record("fred_csv_download", f"series {series}", r.ok and len(lines) > 100, http=r.status_code, observations=max(len(lines) - 1, 0), last=lines[-1] if lines else None)


def _fx():
    r = get("https://api.frankfurter.dev/v1/currencies")
    record("frankfurter", "v1 currencies (ECB reference)", r.ok, http=r.status_code, currencies=len(r.json()) if r.ok else 0)
    r = get("https://api.frankfurter.dev/v1/2016-01-01..2026-09-26", params={"base": "USD", "symbols": "INR"})
    record("frankfurter", "USD/INR daily history since 2016", r.ok, http=r.status_code, observations=len(r.json().get("rates", {})) if r.ok else 0)
    r = get("https://data-api.ecb.europa.eu/service/data/EXR/D.INR.EUR.SP00.A", params={"format": "csvdata", "startPeriod": "2016-01-01"})
    record("ecb_data_portal", "EXR daily INR/EUR (official, no key)", r.ok, http=r.status_code, rows=max(len(r.text.splitlines()) - 1, 0))


def _fred_api():
    r = get("https://api.stlouisfed.org/fred/series/observations", params={"series_id": "DGS10", "file_type": "json"})
    record("fred_api", "API without key", r.ok, http=r.status_code, message=r.text[:90])


def _openfigi():
    r = requests.post("https://api.openfigi.com/v3/mapping", json=[{"idType": "ID_ISIN", "idValue": "INE002A01018"}], headers={"Content-Type": "application/json"}, timeout=TIMEOUT)
    data = r.json() if r.ok else []
    record("openfigi", "ISIN mapping without key", r.ok and bool(data and data[0].get("data")), http=r.status_code,
           sample=[(d.get("ticker"), d.get("exchCode"), d.get("securityType")) for d in (data[0].get("data", []) if data else [])[:4]],
           ratelimit=r.headers.get("ratelimit-limit") or r.headers.get("x-ratelimit-limit"))


def upstox():
    """Broker API (India). Docs say an access token is required for candles; a keyless success is undocumented behaviour."""
    import gzip
    r = get("https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz")
    data = json.loads(gzip.decompress(r.content)) if r.ok else []
    segments = {}
    for item in data:
        segments[item.get("segment")] = segments.get(item.get("segment"), 0) + 1
    reits = sorted(item["trading_symbol"] for item in data if item.get("segment") == "NSE_EQ" and item.get("trading_symbol") in {"EMBASSY", "MINDSPACE", "BIRET", "NXST"})
    record("upstox", "public instrument master (complete.json.gz)", bool(data), http=r.status_code, instruments=len(data), segments=segments, nse_reits_found=reits)
    r = get("https://api.upstox.com/v2/historical-candle/NSE_EQ%7CINE002A01018/day/2026-09-25/2025-09-26", headers={**UA_BROWSER, "Accept": "application/json"})
    candles = r.json().get("data", {}).get("candles", []) if r.ok else []
    record("upstox", "v2 daily candles WITHOUT token (undocumented)", bool(candles), http=r.status_code, candles=len(candles),
           note="documentation requires 'Authorization: Bearer <token>'; do not rely on keyless access")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    started = datetime.now(timezone.utc)
    for section in (yahoo, nse, bse, sec, nasdaq_trader, amfi_and_mfapi, crypto, fx_rates_commodities, upstox):
        try:
            section()
        except Exception as error:  # a broken provider must not stop the others
            record(section.__name__, "section failed", False, error=repr(error)[:160])
    out = config.REFERENCE_DIR / "provider_verification.json"
    out.write_text(json.dumps({"verified_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"), "script": "scripts/verify_providers.py", "results": results}, indent=2, default=str), encoding="utf-8")
    print(f"\n{sum(r['ok'] for r in results)}/{len(results)} checks OK → {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
