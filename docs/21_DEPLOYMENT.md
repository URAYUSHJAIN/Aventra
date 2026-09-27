# 21 — Deployment and Local Running

## Prerequisites

- FinBERT weights in `backend/models/finbert/` (`config.json`, `pytorch_model.bin`, tokenizer files). They are git-ignored (438 MB). Without them the app still runs, but news sentiment is reported as unavailable (live mode) or served from cached FinBERT outputs (demo asset).
- `all-MiniLM-L6-v2` downloads from Hugging Face on first use (≈ 90 MB). Offline, semantic relevance is reported as unavailable; nothing else is affected.

## Option A — Docker Compose (recommended)

```bash
cp .env.example .env          # optional; defaults work
docker compose up --build
# UI:  http://localhost:8080        API: http://localhost:5050/api/health
```

- Services: `backend` (Flask + ML pipeline, gunicorn, 1 worker × 8 threads) and `frontend` (nginx serving the Vite build and proxying `/api`). SQLite, trained artefacts and the Hugging Face cache persist on the `aventra-state` volume. There is no separate database container yet (SQLite first).
- FinBERT is mounted read-only from `FINBERT_HOST_PATH` (default `./backend/models/finbert`).
- Offline demo: `AVENTRA_DATA_MODE=demo docker compose up --build`, then open `/intelligence?symbol=DEMO`.
- Ports are configurable with `FRONTEND_PORT` and `BACKEND_PORT`.

## Option B — Local development (Windows commands shown)

```powershell
# backend (repo root)
py -3.12 -m pip install -r backend/requirements.txt
py -3.12 -m scripts.generate_demo_data        # only if data/demo/ is missing
py -3.12 -m backend.app                        # http://127.0.0.1:5000

# frontend (second terminal)
cd frontend
npm install
npm run dev                                    # http://localhost:5173, proxies /api → 127.0.0.1:5000
```

If port 5000 is already used on your machine: `$env:PORT=5001; py -3.12 -m backend.app` and start Vite with `$env:AVENTRA_API_PROXY="http://127.0.0.1:5001"; npm run dev`.

## Option C — Vercel frontend + separately hosted backend

`frontend/vercel.json` rewrites all paths to `index.html`. A Vercel build has no `/api` proxy, so set `VITE_API_BASE_URL` to the public backend origin at build time and add the Vercel domain to the backend's `CORS_ORIGINS`. The backend needs ≈ 2 GB RAM for FinBERT + MiniLM.

## Pipeline CLIs

```bash
py -3.12 -m ml.pipelines.run --symbol DEMO
py -3.12 -m ml.pipelines.batch --symbols RELIANCE,TCS,INFY,HDFCBANK,ICICIBANK
py -3.12 -m ml.evaluation.run_experiments          # EXP-01
py -3.12 -m ml.evaluation.finbert_phrasebank       # EXP-02
```

## Environment variables

See `.env.example` (backend/Compose) and `frontend/.env.example`. No API keys are required by the current providers; never place secrets in `VITE_*` variables.
