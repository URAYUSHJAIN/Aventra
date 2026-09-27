# Aventra

> **Detect Hidden Patterns. Understand Market Risk.**

Aventra is an explainable financial-intelligence pipeline that combines adaptive behavioural profiling, anomaly detection, financial-news sentiment and cross-source temporal correlation to contextualise unusual market behaviour. For a selected NSE asset it answers: *what changed, how unusual it is, what else was happening at the same time, and why it was flagged.*

Aventra does not predict prices, recommend trades or provide financial advice. Correlated signals are reported as temporally aligned, never as causes.

B.Tech final-year research and development project — ABES Engineering College, Ghaziabad, Uttar Pradesh, India.

## What is implemented

| Stage | Implementation | Status |
|---|---|---|
| Market data | Provider abstraction: Yahoo Finance chart API (server-side, cached, stored fallback) and a synthetic demo provider | Implemented |
| Validation & alignment | Duplicates, invalid OHLC, holiday placeholder bars; UTC storage; NSE session alignment | Implemented |
| Feature engineering | 12 past-only features (returns, volatility, volume ratio/z, gap, range, MA distance, RSI, NIFTY-relative return) | Implemented |
| Behavioural fingerprint | Rolling median/MAD robust baseline per asset with guarded adaptive update | Implemented |
| Anomaly detection | Statistical z-score + fingerprint + Isolation Forest ensemble; LOF and LSTM autoencoder evaluated experimentally; PELT change points as retrospective context | Implemented / experimental parts marked |
| News & sentiment | Google News RSS, de-duplication, alias-based entity linking, existing FinBERT model, rule-based event categories | Implemented |
| Cross-source correlation | Time-window alignment, entity match, sentiment, anomaly strength, semantic relevance (MiniLM) | Implemented |
| Temporal analysis | Ordered timelines, session-relative timing, lead/lag (when data suffices) | Implemented |
| Risk scoring | Transparent weighted formula with anomaly gate and exact per-component contributions | Implemented (uncalibrated) |
| Evidence chain | Time-ordered, source-attributed evidence + plain-language explanation | Implemented |
| Flask API | Health, assets, market, news, sentiment, fingerprint, anomaly, events, risk, evidence, intelligence | Implemented |
| React dashboard | `/intelligence`, four capability pages, homepage market panel and intelligence preview, FinBERT text analysis | Implemented |
| Storage | SQLite (prices, news, sentiment, runs, anomalies, events, risk, evidence); versioned model artefacts | Implemented |
| Evaluation | EXP-01 synthetic injection (baselines + ablations), EXP-02 FinBERT on PhraseBank | Run; results in `experiments/results/` |
| Docker | Compose: backend (Flask + ML) and frontend (nginx), SQLite volume | Implemented |

Details: [docs/](docs/README.md). Limitations and open research questions: [docs/25_LIMITATIONS.md](docs/25_LIMITATIONS.md).

## Evaluation at a glance

Measured on 2026-09-27 (full tables and protocol in [docs/17_MODEL_EVALUATION.md](docs/17_MODEL_EVALUATION.md)):

- **EXP-01** (synthetic anomalies injected into 5 years of real NSE data for five assets, chronological split): the production ensemble reached PR-AUC 0.670 ± 0.130; the simple statistical baseline reached 0.713 ± 0.090. The ensemble does **not** outperform the baseline on these single-bar synthetic anomalies — calibration and richer benchmarks are future work.
- **EXP-02** FinBERT on Financial PhraseBank (AllAgree, 2,264 sentences): accuracy 0.9717, macro-F1 0.9625 — **overlaps with FinBERT's training data**, so it validates the integration, not generalisation.

## Run it

**Docker (recommended):**

```bash
docker compose up --build        # UI http://localhost:8080 · API http://localhost:5050/api/health
```

**Local development:**

```powershell
py -3.12 -m pip install -r backend/requirements.txt
py -3.12 -m backend.app                              # API on http://127.0.0.1:5000
cd frontend; npm install; npm run dev                # UI on http://localhost:5173
```

FinBERT weights must be present in `backend/models/finbert/` (git-ignored). Offline demo: set `AVENTRA_DATA_MODE=demo` and open `/intelligence?symbol=DEMO` (synthetic data, clearly labelled). Full instructions, port overrides and Vercel notes: [docs/21_DEPLOYMENT.md](docs/21_DEPLOYMENT.md).

## Tests

```bash
py -3.12 -m unittest discover -s ml/tests -t .         # 35 tests
py -3.12 -m unittest discover -s backend/tests -t .    # 18 tests
cd frontend && npm test && npm run typecheck && npm run build   # 15 tests
```

## Repository structure

```text
Aventra/
├── AGENTS.md, CLAUDE.md          agent instructions (status table, conflicts, rules)
├── context/                      master design / implementation / ML documents
├── docs/                         engineering documentation
├── backend/                      Flask app: app.py, routes/, services/, utils/, tests/, models/finbert (weights, ignored)
├── ml/                           data/, features/, fingerprint/, anomaly/, news/, correlation/, temporal/, risk/, evidence/, pipelines/, evaluation/, tests/
├── frontend/                     React + TypeScript + Vite + Tailwind; src/{components,pages,services,types,hooks,utils,styles}
├── data/reference/               asset registry and aliases      data/demo/  synthetic demo dataset
├── experiments/results/          experiment records (JSON + Markdown)
├── scripts/generate_demo_data.py
├── docker/, docker-compose.yml, .env.example
```

## Technology

React 19, TypeScript, Vite 8, Tailwind CSS v4, lucide-react · Flask 3, Flask-CORS · pandas, NumPy, scikit-learn, PyTorch, Transformers (FinBERT), sentence-transformers, ruptures · SQLite · Docker Compose, nginx, gunicorn.

## Research integrity

Every metric in this repository was produced by a committed command and is stored with its data provenance. Thresholds and weights are engineering defaults, not validated values. No novelty, causation or predictive-accuracy claims are made.

## License

To be determined. Financial PhraseBank (used only for evaluation, not committed) is CC BY-NC-SA 3.0.
