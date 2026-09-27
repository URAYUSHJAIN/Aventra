# 06 — Data Sources and Providers (Phase 0 verification, 2026-09-27)

Evidence: `py -3.12 -m scripts.verify_providers` → `data/reference/provider_verification.json` (raw status codes, counts, date ranges). Terms and limits come from the providers' own pages, fetched on 2026-09-27 (links at the end). **Re-verify before relying on any row: availability, limits and terms change.**

Status legend: **VERIFIED** = data retrieved and terms/limits read on the provider's own pages · **DATA-ONLY** = data retrieved, but terms missing/unclear · **BLOCKED** = technically works but the terms prohibit our use · **UNAVAILABLE** = could not retrieve.

## 1. Headline findings

1. **Yahoo Finance (currently used by Aventra) is BLOCKED by its terms.** Yahoo's Terms of Service §2.4(i) prohibit collecting data "using any automated means … for any purpose without our express, prior permission", and §2.5 prohibits commercial reuse. The chart and search endpoints are undocumented. Technically, Yahoo also returned silent partial data: `RELIANCE.BO` and `INFY.BO` gave HTTP 200 with one daily bar, and `range=max` switched to monthly bars. **Yahoo can only be an explicitly-labelled, best-effort fallback for local academic use, never the foundation — and even that needs your decision.**
2. **NSE's website is BLOCKED for automated collection.** The NSE Terms of Use state: "User is prohibited to conduct any systematic or automated data collection activities (including scraping, data mining, data extraction and data harvesting) on or in relation to our Website". The listing files (`EQUITY_L.csv`, `eq_etfseclist.csv`) download fine but **must not be fetched on a schedule**. A manual, user-performed import is the only compliant use.
3. **No verified free source permits displaying Indian or US equity, ETF or index prices to other users.** Every candidate is personal/internal-use only (Tiingo, Twelve Data Basic, Upstox), needs your account or key (Alpha Vantage, Upstox), or is blocked (Yahoo, NSE).
4. **Verified, API-based classes:**
   - crypto (Binance, Coinbase Exchange, CoinGecko);
   - forex reference rates (Frankfurter, ECB Data Portal);
   - US rates and commodity spot series (FRED CSV now; FRED API with a free key);
   - Indian mutual-fund NAVs (AMFI official file, plus mfapi.in history — community-run, terms unavailable);
   - US security listings (SEC, Nasdaq Trader);
   - identifier mapping (OpenFIGI).

## 2. Provider matrix

| Provider | Access | Classes verified with real data | Listing / search | History verified | Limits (source) | Terms status | Aventra role |
|---|---|---|---|---|---|---|---|
| Yahoo chart/search | undocumented, keyless | equities IN/US, ETFs, indices, forex, crypto, futures, IN REIT, US & IN mutual funds, US yields | search ≤ 10–20 results, incomplete ("mindspace reit" → 0); no listing | daily 2016→ for all samples; 5 m for 60 d; 1 m for 8 d only; BSE names can return 1 bar | none published | **BLOCKED** (ToS §2.4 i, §2.5) | optional fallback only if you approve; always labelled |
| NSE archives (`EQUITY_L.csv`, `eq_etfseclist.csv`) | website download | listing only: 2,585 equities; 351 ETFs (4 bond, 26 gold) | listing | — | — | **BLOCKED for automation** (NSE ToU) | manual import by user only |
| NSE REIT/InvIT list | — | — | — | — | — | **UNAVAILABLE** (404) | — |
| BSE scrip API | — | — | — | — | — | **UNAVAILABLE** (403) | — |
| SEC `company_tickers_exchange.json` | public file | US issuers: 10,427 (Nasdaq 4,374, NYSE 3,302, OTC 2,542, CBOE 44) | listing | — | 10 req/s, declared User-Agent (SEC fair-access page) | **VERIFIED** (US-government public data) | US equity master |
| Nasdaq Trader `nasdaqlisted`/`otherlisted` | public files | US listed securities with ETF flag (4,449 ETFs in otherlisted) | listing | — | none stated; files updated through the day | **DATA-ONLY** (no usage terms on the definitions page) | US ETF classification |
| Nasdaq Trader `mfundslist.txt` | — | — | — | — | — | **UNAVAILABLE** (returns an HTML page) | — |
| AMFI `NAVAll.txt` + NAV history report | public files | Indian mutual funds: 14,396 scheme rows (8 fields incl. plan/option); 8,970 with a 2026 NAV, 5,426 stale/inactive | listing + latest NAV; official history by date range | yes (history report returned ~4.7 MB for 5 days) | none stated | **DATA-ONLY** (AMFI site terms not reviewed) | MF master; official NAV source |
| mfapi.in | keyless REST | Indian MF NAV history (37,917 schemes incl. inactive); codes = AMFI codes (5/5 latest NAVs matched AMFI) | list + per-scheme | back to 2006 for sampled schemes | "no rate limiting" (site) | **DATA-ONLY** (community-run; terms page 404) | MF history convenience; AMFI is authoritative |
| Binance public API | keyless REST | crypto spot: 3,713 symbols (1,368 trading; 496 USDT pairs) | `exchangeInfo` | daily OHLCV from 2017-08-17, 1,000 bars/request | weight-based; 429 → 418 IP ban 2 min–3 days; honour `Retry-After` (Binance docs) | **DATA-ONLY** (limits documented; jurisdiction terms not verified) | primary crypto bars |
| Coinbase Exchange public API | keyless REST | crypto: 838 products | `products` | daily candles, 300 per request | not reviewed | **DATA-ONLY** | crypto fallback |
| CoinGecko | keyless / free Demo key | 21,641 coins | `coins/list` | keyless: 365 days max (`days=max` → 401, error 10012) | Demo: 100 calls/min, 10k/month, key required (CoinGecko pages) | **VERIFIED** for metadata; history needs a Demo key | coin names/aliases; fallback history |
| Frankfurter | keyless REST | forex: 30 ECB currencies on `/v1`; USD/INR 2,749 daily obs since 2016 | `currencies` | daily since 1999 (ECB) | throttled, no caps (Frankfurter site) | **VERIFIED** (open source; data under each central bank's terms) | primary FX reference series |
| ECB Data Portal | keyless REST | official EXR series (INR/EUR 2,748 daily rows) | SDMX | daily | not reviewed | **DATA-ONLY** | FX authority / cross-check |
| FRED CSV download | website CSV | DGS10, DGS2 (Treasury yields), DCOILWTICO, DCOILBRENTEU (oil spot), DEXINUS (USD/INR) | — | decades | connection reset after ~3 rapid downloads; OK with 4 s spacing | **DATA-ONLY** (website download; API terms apply to the API) | interim only |
| FRED API | free key | same series | series search | decades | "may impose limits" (FRED terms) | **VERIFIED**: key required; attribution notice mandatory; some series third-party copyrighted | rates & commodity spot (after you register a key) |
| OpenFIGI | keyless / free key | identifier mapping (RELIANCE ISIN → IN/IB/IS/IG listings); **`/v3/filter` enumerates 6,478 NSE (`exchCode IN`) common stocks**, 100 per page | `/v3/mapping`, `/v3/search`, `/v3/filter` | — | no key: 25 mapping req/min (10 jobs), 5 search/filter req/min; free key: 25 per 6 s, 20/min (OpenFIGI docs) | **VERIFIED** (free & open) | ISIN/ticker resolution; permitted listing enumeration candidate |
| Upstox | broker API (account) | public instrument file: 119,883 instruments (NSE/BSE equities incl. ETFs, all 4 NSE REITs, 139 NSE indices, MCX, currency F&O) | instrument file | daily candles; docs: token required, ≤ 1 year per request | 50/s, 500/min, 2000/30 min per user (Upstox docs) | **PERSONAL USE ONLY** (Upstox staff, community forum); keyless candle access worked but is undocumented | India equities/ETF/REIT/index/commodity **only with your own account, for local use** |
| Alpha Vantage | free key | BSE equity daily since 2005 (RELIANCE.BSE, 5,353 bars, docs demo); global symbol search; US listing status 14,483 stocks/ETFs | `SYMBOL_SEARCH`, `LISTING_STATUS` | 20+ years | free: 25 req/day; "unlimited" for verified open-source/educational projects (AV support page) | **VERIFIED** limits; full ToS not reviewed; educational tier requires your application | strongest candidate for India + US equities/ETFs if the educational tier is granted |
| Tiingo | free key | not tested (needs key) | — | — | 50/h, 1,000/day, 500 symbols/month (Tiingo pricing) | **Internal use only** (Tiingo pricing) | not appropriate for displayed data |
| Twelve Data | free key | not tested (needs key) | — | — | 8/min, 800/day; India exchanges only on paid plans (Twelve Data pricing) | **Internal non-display use** on free plan | not appropriate |
| Stooq | — | — | — | — | — | **UNAVAILABLE** (HTML instead of CSV) | — |

## 3. Market calendars (`exchange_calendars` 4.13.2, installed only in a scratch directory for testing)

- 71 calendars, including XBOM, XNYS, XNAS, XLON, XTKS, XHKG, CMES, `24/7` and `24/5`. **There is no XNSE calendar.**
- XNYS vs Yahoo AAPL trading days, 2021–2026: **exact match** (1,255 days).
- XBOM vs NSE trading days (RELIANCE.NS): 1,235 provider days vs 1,233 calendar sessions.
  - 4 NSE days are missing from XBOM, e.g. Diwali Muhurat sessions (2021-11-04, 2022-10-24, 2024-11-01).
  - 2 XBOM sessions have no NSE bar (2024-01-20, a Saturday; 2025-03-18). The reason for these two has not been confirmed.
- **Conclusion:** use the calendar only for future and in-progress session logic. Historical session sets come from the provider's observed bars. NSE uses XBOM as a proxy, and the mismatches above are expected.

## 4. Asset-class verdict (what Aventra may claim)

| Class | Verdict | Basis |
|---|---|---|
| Crypto | **Supportable now** | Binance/Coinbase public APIs (OHLCV); CoinGecko metadata |
| Forex (reference rates) | **Supportable now** (close-only, daily, no volume) | Frankfurter / ECB |
| Indian mutual funds | **Supportable now** (NAV-only) | AMFI official files; mfapi.in history (community) |
| US Treasury yields, oil spot (WTI/Brent) | **Supportable after a free FRED key** | FRED API + attribution |
| US equities / ETFs | **Listing verified; prices need a permitted source** (Alpha Vantage key/educational tier, or accept Yahoo fallback) | SEC + Nasdaq Trader listings |
| Indian equities / ETFs / REITs / indices | **Listing verified via OpenFIGI (permitted API: 6,478 NSE common stocks; ETF/REIT coverage by securityType still to be checked in Phase 1). Prices need your decision** (Alpha Vantage educational tier, Upstox personal account, or Yahoo fallback) | NSE ToU, Yahoo ToS, Upstox personal-use |
| Commodities | **Partial**: WTI/Brent spot via FRED; futures only via Yahoo (fallback); Indian gold/silver ETFs follow the Indian-equity decision; MCX only via Upstox (personal) | — |
| Indian government / corporate bonds | **UNAVAILABLE** (no verified free API); bond ETFs follow the Indian-equity decision | — |
| US mutual funds | **Prices only via Yahoo fallback**; no permitted listing (`mfundslist` unavailable) | — |

## 5. Decisions needed before Phase 1

1. **Yahoo:** remove it entirely, or keep it as an opt-in, labelled fallback for local academic use in spite of ToS §2.4(i)? (This affects the pipeline that already ships.)
2. **Indian/US equity prices:** apply for Alpha Vantage's educational tier (their page says unlimited for verified educational projects), and/or use your own Upstox account for local personal use.
3. **Keys to register** (free): FRED API, CoinGecko Demo, OpenFIGI (optional, higher limits), Alpha Vantage.
4. **NSE listings:** use OpenFIGI `/v3/filter` (permitted API) as the automated listing source, with an optional manual import of NSE files that you download yourself — never scheduled NSE downloads.

Evidence file: `data/reference/provider_verification.json`, run 2026-09-27T17:08:36Z, 57/66 checks OK; every failed check is a real provider limitation listed above.

## Sources

[Yahoo Terms of Service](https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html) · [Yahoo developer API terms](https://legal.yahoo.com/us/en/yahoo/terms/product-atos/apiforydn/index.html) · [NSE Terms of Use](https://www.nseindia.com/static/nse-terms-of-use) · [SEC fair access](https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data) · [Nasdaq Trader symbol directory definitions](https://www.nasdaqtrader.com/trader.aspx?id=symboldirdefs) · [mfapi.in](https://www.mfapi.in/) · [Binance API limits](https://developers.binance.com/docs/binance-spot-api-docs/rest-api/limits) · [CoinGecko pricing](https://www.coingecko.com/en/api/pricing) · [CoinGecko rate limits](https://docs.coingecko.com/docs/common-errors-rate-limit) · [Frankfurter](https://frankfurter.dev/) · [FRED API terms](https://fred.stlouisfed.org/docs/api/terms_of_use.html) · [OpenFIGI API documentation](https://www.openfigi.com/api/documentation) · [Upstox historical candle API](https://upstox.com/developer/api-documentation/get-historical-candle-data/) · [Upstox rate limits](https://upstox.com/developer/api-documentation/rate-limiting/) · [Upstox community: personal-use response](https://community.upstox.com/t/usage-of-api-for-personally-owned-website/4715) · [Alpha Vantage support](https://www.alphavantage.co/support/) · [Tiingo pricing](https://www.tiingo.com/about/pricing) · [Twelve Data pricing](https://twelvedata.com/pricing)
