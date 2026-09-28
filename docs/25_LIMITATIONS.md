# 25 — Limitations and Future Work

## Data and providers

- **Keys decide coverage.** Without keys, analysis is limited to Binance/CoinGecko crypto, Frankfurter/ECB forex and Indian mutual funds (NAV). The following are *listed and searchable* but return `PROVIDER_UNAVAILABLE`:
  - US and BSE equities/ETFs (Alpha Vantage key; the free tier allows 25 requests a day);
  - NSE equities, ETFs, REITs, InvITs, bonds and indices (Upstox token, personal use per Upstox);
  - rates and commodities (FRED key).
- **News.** Alpha Vantage `NEWS_SENTIMENT` is the only news source; it needs a key and covers US tickers, crypto and forex.
  - **Indian equities, mutual funds and rates have no permitted news source**, so their news status is `unavailable` and their risk basis is market-only.
  - Alpha Vantage timestamps carry no timezone and are **assumed to be UTC** (recorded in each item's provenance).
- **Calendars.** There is no XNSE calendar in exchange_calendars; **XBOM is the NSE proxy**. Phase 0 found known mismatches (Muhurat sessions and two unexplained dates), so historical sessions come from observed bars.
- **Classification.**
  - Classes come from listing fields and name rules. ETFs in the Upstox and SEC listings are detected by name, which is imperfect: only 88 ETFs were detected in the first Upstox classification.
  - OpenFIGI refinement (`--refine`) runs in batches and has not been run over the whole master.
  - `class_source` and `class_confidence` show how each class was decided.
- **Coverage gaps.**
  - CoinGecko history is limited to 365 days without a key, which is too short for some detectors.
  - Mutual-fund history comes from mfapi.in, which is community-run and has no published terms. AMFI is authoritative for the latest NAV.
  - US mutual funds, futures and MCX commodities are not supported.
  - US equities have no benchmark (no permitted index source); `relative_return` is unavailable for them.
- **Removed sources.**
  - Yahoo Finance: its terms prohibit automated collection.
  - Google News RSS: robots.txt disallows it.
  - Automated NSE downloads: NSE's terms prohibit them.

  Legacy v0.1 rows from these sources are excluded from production reads.
- **SEC fair access** asks for a real contact in the User-Agent. Set `AVENTRA_SEC_USER_AGENT`; the default names the project but has no contact address.

## Models

- **FinBERT.** English only, 64-token sentence inputs, unweighted sentence mean, uncalibrated confidence. Its PhraseBank evaluation overlaps with its training data.
- **Uncalibrated defaults.** All thresholds and weights (ensemble, severity, correlation, risk) are defaults. In EXP-03 the production ensemble is **not** uniformly the best detector: LOF and ablations win on crypto. It also misses most single-day volume and volatility spikes at the default threshold.
- **EXP-01** is a v0.1 record on Yahoo-era NSE data and cannot be reproduced with current providers without an Upstox token.
- **Experimental parts.** The LSTM autoencoder and LOF are experimental (evaluation only). Change points are retrospective annotations.
- **Risk.** There is no trained risk model and no SHAP; risk is a transparent formula with exact linear contributions.
- **Correlation** is temporal and asset alignment, never causation. Lead/lag needs at least 20 news days.

## Engineering

- The API process keeps a small in-memory cache for sync mode only. The worker and API share state through the database.
- One gunicorn worker (FinBERT memory); the worker container scales horizontally on PostgreSQL (`SKIP LOCKED`).
- The frontend uses a manual router (every navigation is a full page load) and hand-drawn SVG charts.
- The `/doc` publication cards (patent, research paper, review paper) are marked Coming Soon: no documents exist yet.
- The 3D scenes are decorative; the first page that shows one downloads the three.js chunk (~133 kB gzip). There is no "Financials" tab because no fundamentals endpoint exists.
- `pip install` of the backend requirements may upgrade shared packages in a global Python (it upgraded `packaging`, which conflicts with an unrelated Streamlit install on the development machine). Use a virtual environment.

## Future work (ordered)

1. Obtain the Alpha Vantage educational tier and/or an Upstox token, then run EXP-03 on equities, ETFs and indices.
2. Calibrate ensemble weights and the flag threshold on validation data per asset class; add multi-day and multi-feature injections; use more seeds.
3. Run OpenFIGI refinement over the full equity/ETF master and measure classification accuracy on a labelled sample.
4. Find a permitted news source for Indian instruments; hand-label a news sample to measure entity linking.
5. Curate a sourced known-event benchmark per asset class and evaluate detection lead time.
6. A trained risk model with SHAP once labelled outcomes exist.
