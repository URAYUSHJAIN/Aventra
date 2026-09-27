# 21 — Deployment and Local Running

## Prerequisites

- **FinBERT weights** in `backend/models/finbert/` (`config.json`, `pytorch_model.bin`, tokenizer files). They are git-ignored (438 MB). Without them the app runs, but news sentiment is reported as unavailable.
- **all-MiniLM-L6-v2** downloads from Hugging Face on first use (≈ 90 MB). Offline, semantic relevance is reported as unavailable; nothing else is affected.
- **Provider keys (all optional).** See `.env.example`. Without them the following report `PROVIDER_UNAVAILABLE`:
  - equities, ETFs and indices (Alpha Vantage / Upstox);
  - news (Alpha Vantage);
  - rates (FRED).

  Crypto, forex and Indian mutual funds work without keys.

## Option A — Docker Compose (recommended)

```bash
cp .env.example .env          # set POSTGRES_PASSWORD (required); add keys; optionally AVENTRA_DEFAULT_WATCHLIST
docker compose up --build
# UI:  http://localhost:8080        API: http://localhost:5050/api/health
```

| Service | Image / command | Notes |
|---|---|---|
| `postgres` | `postgres:16-alpine` | Database and job queue; volume `aventra-pg`; not published to the host |
| `backend` | `docker/backend.Dockerfile`, gunicorn (1 worker × 8 threads) | Applies Alembic migrations on start; `AVENTRA_JOB_MODE=external` (enqueues only) |
| `worker` | same image, `python -m ml.jobs.worker` | Claims jobs; scheduler syncs listings when older than 24 h and analyses the watchlist daily; starts after the backend is healthy |
| `frontend` | `docker/frontend.Dockerfile` (Vite build → nginx) | Proxies `/api` to the backend (180 s read timeout) |

- The first start syncs about 68,600 instruments from keyless listings in roughly 2 minutes. Search is empty until then; the UI says so.
- FinBERT is mounted read-only from `FINBERT_HOST_PATH`. Artefacts and the Hugging Face cache persist on `aventra-state`.
- The image contains no synthetic data (`data/demo` is not copied).
- Ports: `FRONTEND_PORT`, `BACKEND_PORT`.
- Reset the database: `docker compose down && docker volume rm aventra_aventra-pg`.

## Option B — Local development (Windows commands shown)

```powershell
# backend (repo root) — SQLite at data/aventra.sqlite3; jobs run in API threads (AVENTRA_JOB_MODE=inline, default)
py -3.12 -m pip install -r backend/requirements.txt
py -3.12 -m ml.instruments.sync                # Instrument Master from permitted listings (~2 min)
$env:AVENTRA_DEFAULT_WATCHLIST="CRYPTO:BTC-USDT,FX:USDINR,MF-IN:122639"   # optional
py -3.12 -m backend.app                        # http://127.0.0.1:5000

# frontend (second terminal)
cd frontend
npm install
npm run dev                                    # http://localhost:5173, proxies /api → 127.0.0.1:5000
```

If port 5000 is taken, run the backend with `$env:PORT=5001` and start Vite with `$env:AVENTRA_API_PROXY="http://127.0.0.1:5001"`.

To use PostgreSQL locally, set `AVENTRA_DATABASE_URL=postgresql+psycopg://user:password@host:5432/db`. To run a separate worker, set `AVENTRA_JOB_MODE=external` and start `py -3.12 -m ml.jobs.worker`.

## Option C — Vercel frontend + separately hosted backend

`frontend/vercel.json` rewrites all paths to `index.html`. A Vercel build has no `/api` proxy, so:
- set `VITE_API_BASE_URL` to the public backend origin at build time;
- add the Vercel domain to the backend's `CORS_ORIGINS`.

The backend needs ≈ 2 GB RAM for FinBERT and MiniLM, a PostgreSQL database and a worker process.

## CLIs

```bash
py -3.12 -m ml.instruments.sync [provider ...]           # listing sync (all keyless + keyed when configured)
py -3.12 -m ml.instruments.sync --refine 500             # OpenFIGI security-type refinement
py -3.12 -m ml.instruments.sync --import-nse EQUITY_L.csv   # manual import of an NSE file you downloaded (never automated)
py -3.12 -m ml.jobs.worker [--once]                      # background worker
py -3.12 -m ml.pipelines.run --instrument CRYPTO:BTC-USDT
py -3.12 -m ml.pipelines.batch --instruments CRYPTO:BTC-USDT,FX:USDINR
py -3.12 -m ml.evaluation.run_experiments --instruments ... [--no-lstm]   # EXP-03
py -3.12 -m ml.evaluation.finbert_phrasebank             # EXP-02
py -3.12 -m scripts.verify_providers                     # Phase 0 provider evidence
```

## Environment variables

`.env.example` lists every variable the code reads: Compose, provider credentials, database/jobs, pipeline settings and the test-only synthetic flag. Keys are server-side only; never place a secret in a `VITE_*` variable.
