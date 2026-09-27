# Aventra

> **Detect Hidden Patterns. Understand Market Risk.**

Aventra is an explainable financial-intelligence platform. It combines adaptive behavioural profiling, anomaly detection, financial-news sentiment and cross-source temporal correlation to put unusual market behaviour in context. For any instrument it can obtain real data for, it answers: *what changed, how unusual it is, what else was happening at the same time, and why it was flagged.*

Aventra does not predict prices, recommend trades or provide financial advice. Signals that line up in time are reported as temporally associated, never as causes. **Aventra never fabricates financial data.** When no permitted provider can supply real data, the API and UI say so: "Data unavailable / insufficient source data", with the providers that were tried.

B.Tech final-year research and development project — ABES Engineering College, Ghaziabad, Uttar Pradesh, India.

## What works, and what needs a key

The Instrument Master is synced from permitted listings: about 68,600 instruments on 2026-09-27. Search covers all of them. Analysis runs only where a legitimate provider supplies history.

| Asset class | Price/value source | Needs | Feature set |
|---|---|---|---|
| Crypto (Binance pairs) | Binance public API, daily OHLCV | nothing | `ohlcv_continuous` |
| Crypto (other coins) | CoinGecko, daily close + volume (365 days keyless) | nothing (`COINGECKO_DEMO_API_KEY` optional) | `close_volume` |
| Forex reference rates | Frankfurter (ECB), daily close | nothing | `close` |
| Indian mutual funds | AMFI listing + mfapi.in NAV history | nothing | `close` (NAV) |
| US equities / ETFs | Alpha Vantage daily | `ALPHAVANTAGE_API_KEY` | `ohlcv` |
| Indian equities / ETFs / REITs / InvITs / bonds / indices | Upstox daily candles (listing is keyless) | `UPSTOX_ACCESS_TOKEN` (personal use per Upstox) | `ohlcv` |
| BSE equities | Alpha Vantage `<SYM>.BSE` | `ALPHAVANTAGE_API_KEY` | `ohlcv` |
| Interest rates, commodity spot | FRED | `FRED_API_KEY` | `yield` / `close` |
| News + sentiment | Alpha Vantage NEWS_SENTIMENT (US equities, crypto, forex) + local FinBERT | `ALPHAVANTAGE_API_KEY` | — |

Removed or never used in production:
- **Yahoo Finance** was removed: its terms prohibit automated collection.
- **Google News RSS** was removed: robots.txt disallows `/rss/search`.
- **NSE files** are never downloaded automatically. An optional manual import of files you download yourself is supported.

Indian-equity news has no permitted provider. Evidence and terms for every provider: [docs/06](docs/06_DATA_SOURCES_AND_PROVIDERS.md).

## Pipeline

```text
Instrument Master (search) → provider router (capability, rate limits, circuit breaker, budget) → validation (capability-aware)
→ features (set chosen from what the data provides) → behavioural fingerprint → anomaly ensemble (statistical + fingerprint + Isolation Forest)
→ news (permitted provider) → entity linking → FinBERT → correlation → risk → evidence chain with provenance → API → React
```

Analyses run as background jobs in a PostgreSQL table (no Redis). The API returns `202` with a job while an analysis runs, and the UI polls the job. Everything is keyed by canonical instrument IDs (`XNAS:AAPL`, `CRYPTO:BTC-USDT`, `FX:USDINR`, `MF-IN:122639`). The ML layer never sees provider symbols. Details: [docs/04](docs/04_SYSTEM_ARCHITECTURE.md), [docs/05](docs/05_ML_PIPELINE.md), [docs/14](docs/14_API_SPECIFICATION.md).

## Evaluation at a glance

Full tables and protocol: [docs/17_MODEL_EVALUATION.md](docs/17_MODEL_EVALUATION.md).

- **EXP-03** (2026-09-27): synthetic anomalies injected into real data for 13 instruments (5 Binance crypto, 4 forex, 4 Indian mutual funds). Chronological split, one seed each, LSTM excluded.
  - The production ensemble reached PR-AUC 0.671 ± 0.096 (crypto), 0.893 ± 0.139 (forex) and 0.917 ± 0.121 (mutual funds).
  - For crypto, LOF (0.724) and the ensemble without the Isolation Forest (0.698) scored higher.
  - The ensemble is **not** consistently the best detector. These are synthetic anomalies, not a measure of real-world detection.
- **EXP-01** (v0.1 record): the same protocol on five NSE stocks, using Yahoo-era data that is no longer a permitted source. The statistical baseline beat the ensemble.
- **EXP-02**: FinBERT on Financial PhraseBank reached accuracy 0.9717. This overlaps with FinBERT's training data, so it validates the integration only.

## Run it

**Docker (recommended):**

```bash
cp .env.example .env              # set POSTGRES_PASSWORD; add provider keys you have; optionally AVENTRA_DEFAULT_WATCHLIST
docker compose up --build         # UI http://localhost:8080 · API http://localhost:5050/api/health
```

Services:
- `postgres`: database and job queue.
- `backend`: Flask API; applies migrations on start.
- `worker`: background jobs, listing sync, scheduled watchlist analysis.
- `frontend`: nginx serving the build.

On first start the worker syncs the keyless listings, which takes about 2 minutes.

**Local development** (SQLite, jobs run in API threads):

```powershell
py -3.12 -m pip install -r backend/requirements.txt
py -3.12 -m ml.instruments.sync                     # build the Instrument Master from permitted listings
py -3.12 -m backend.app                             # API on http://127.0.0.1:5000
cd frontend; npm install; npm run dev               # UI on http://localhost:5173
```

The FinBERT weights must be in `backend/models/finbert/` (git-ignored). Everything else: [docs/21_DEPLOYMENT.md](docs/21_DEPLOYMENT.md).

## Tests

```bash
py -3.12 -m unittest discover -s ml/tests -t .         # 73 tests (1 PostgreSQL test skipped unless AVENTRA_TEST_DATABASE_URL is set)
py -3.12 -m unittest discover -s backend/tests -t .    # 25 tests
cd frontend && npm test && npm run typecheck && npm run lint && npm run build   # 23 tests
```

Automated tests use a synthetic `TEST:DEMO` instrument. It exists only when `AVENTRA_ENABLE_SYNTHETIC_TEST_DATA=1`, which the tests set themselves. It is never a production fallback.

## Repository structure

```text
Aventra/
├── AGENTS.md, CLAUDE.md          agent instructions (status table, conflicts, rules)
├── docs/                         engineering documentation
├── backend/                      Flask: app.py, routes/, services/, utils/, migrations/ (Alembic), tests/
├── ml/                           instruments/ (IDs, master, sync), providers/ (registry, adapters), data/ (db, store, calendars, validation),
│                                 features/, fingerprint/, anomaly/, news/, correlation/, temporal/, risk/, evidence/, pipelines/, jobs/, evaluation/, tests/
├── frontend/                     React + TypeScript + Vite + Tailwind; src/{components,pages,services,types,hooks,utils,styles}
├── data/reference/               seeds, aliases, Phase 0 provider evidence      data/demo/  synthetic fixtures (tests only)
├── experiments/results/          experiment records (JSON + Markdown)
├── scripts/                      verify_providers.py, generate_demo_data.py (test fixtures)
├── docker/, docker-compose.yml, .env.example
```

## Technology

- Frontend: React 19, TypeScript, Vite 8, Tailwind CSS v4.
- Backend: Flask 3, SQLAlchemy 2 Core, Alembic, PostgreSQL 16 / SQLite, exchange_calendars.
- ML: pandas, NumPy, scikit-learn, PyTorch, Transformers (FinBERT), sentence-transformers, ruptures.
- Deployment: Docker Compose, nginx, gunicorn.

## Research integrity

Every metric in this repository was produced by a committed command and is stored with its data provenance. Thresholds and weights are engineering defaults, not validated values. No novelty, causation or predictive-accuracy claims are made.

## License

To be determined. Financial PhraseBank (used only for evaluation, not committed) is CC BY-NC-SA 3.0. Provider data remains under each provider's terms (see docs/06).
