# CLAUDE.md — Aventra

You are the primary implementation agent for **Aventra**: an explainable financial-intelligence pipeline (market behaviour → fingerprint → anomaly → news sentiment → cross-source correlation → risk → evidence), built as a B.Tech final-year research project.

The repository-wide rules live in AGENTS.md and are imported here. They are binding:

@AGENTS.md

This file adds **how Claude Code must execute work**. If this file and AGENTS.md disagree, stop and point out the disagreement to the user.

---

## 0. Non-negotiables (read these every session)

1. **Never jump straight to implementation.** Follow the mandatory workflow in §2 for every task, including "small" ones.
2. **The repository is the source of truth for what exists.** The `context/` master docs describe what *should* exist. Never report a PLANNED component as implemented (AGENTS.md §7).
3. **Preserve working code.** Don't rewrite, restructure or restyle anything the task didn't ask for.
4. **Never fabricate** data, news, sentiment, scores, metrics, dataset sizes, citations or results. If something is unavailable, return and display an explicit "unavailable" state.
5. **Don't touch the user's uncommitted work**, and don't touch `context/`, unless the task is about them. Run `git status` to see the current list.
6. **Don't install packages, start long-running servers, commit, push or delete files unless the task requires it.** If you need any of these and the user hasn't clearly authorised it, ask first.
7. When a document conflict affects the task, check AGENTS.md §32. If it isn't resolved, **ask**. Never invent a resolution.

---

## 1. Start of every task: what to read

Read in this order and stop once you have enough context. You always need 1–3.

1. **AGENTS.md §7 (status) and §32 (conflicts).** These tell you what exists and what is disputed.
2. **The task-relevant master doc section:**
   - ML, data, features, evaluation: `context/AVENTRA_MASTER_ML_PIPELINE.md` (the filename is uppercase)
   - Scope, milestones, API list, schema: `context/Aventra_Final_Implementation_Plan.md`
   - UI, routes, visuals, motion: `context/Aventra_Design_Specification.md`
3. **The actual code you will touch, plus everything that consumes it.** Starting points:
   - ML: `ml/config.py` (all thresholds/weights) → `ml/pipelines/intelligence.py` (orchestrator; shows how every stage connects) → the stage module → `ml/tests/`
   - Backend: `backend/app.py` → `backend/routes/*_routes.py` → `backend/services/*_service.py` → `backend/tests/`
   - Frontend: `frontend/src/App.tsx` (routing and metadata) → `pages/` → `components/` → `services/*.ts` + `types/api.ts` → `styles/`
   - Config: `frontend/vite.config.ts` (proxy), `frontend/package.json`, `backend/requirements.txt`, root and frontend `.env.example`, `docker-compose.yml`, `frontend/vercel.json`
   - Docs describing the current system: `docs/05_ML_PIPELINE.md`, `docs/14_API_SPECIFICATION.md`, `docs/17_MODEL_EVALUATION.md`
4. `git status` and `git diff`, to learn about uncommitted user work before editing anything nearby.

Do not read `backend/models/finbert/pytorch_model.bin`, `node_modules/`, `frontend/dist/` or `package-lock.json` in full.

---

## 2. Mandatory workflow

**READ → UNDERSTAND → PLAN → INSPECT DEPENDENCIES → IMPLEMENT → TEST → VERIFY → DOCUMENT**

Skipping a stage is a failure, even if the code works.

### READ
Use §1. Read whole files you will edit, not just the lines around the change.

### UNDERSTAND
Before planning, answer these to yourself:
- Which pipeline stage(s) does this task belong to (AGENTS.md §6)?
- Does this functionality **already exist**, fully or partly? (See §3.)
- What is the current status of each upstream dependency: REAL, PARTIAL, PLACEHOLDER or PLANNED?
- Which layer owns the logic: ML package, Flask or React?
- Does any §32 conflict apply?

### PLAN
- Write a short plan: files to create or modify, contract changes, tests to add, docs to update.
- Choose the smallest change that delivers real, verifiable value.
- If the task is large (more than about five files, or it crosses the ML, Flask and React layers), break it into increments that can each be verified on their own (§5). Present the plan to the user before starting.
- If the plan needs a new dependency, a file move or rename, an API breaking change or a §32 resolution, ask the user first.

### INSPECT DEPENDENCIES
- `Grep` every symbol, endpoint path, CSS class, env var and exported type you will change, across `backend/` and `frontend/src/`.
- For API changes, list every frontend consumer (`services/*.ts` → components) and confirm the change is additive.
- For new packages, check `package.json` / `requirements.txt` for something that already covers the need. Check version constraints too: `torch<2.5`, `transformers<4.41` and `numpy<2` are pinned.

### IMPLEMENT
- Follow the existing conventions (AGENTS.md §9–10): app factory and blueprints, lazy-loaded model singletons, typed domain exceptions, `{success, data|error}` envelope, `services/*.ts` for all network calls, named function components, and token-based styles in `styles/` (tokens → base → site / intelligence).
- Match the density and style of the file you are editing.
- Put constants in config and add new env vars to `.env.example`.
- Implement every state: loading, empty, error and success.

### TEST
Run what applies and read the output. Don't assume it passed.

```bash
# ML + backend (from repo root; offline)
py -3.12 -m unittest discover -s ml/tests -t .
py -3.12 -m unittest discover -s backend/tests -t .

# Frontend (from frontend/)
npm test                     # vitest + jsdom
npm run typecheck            # the real type gate — `npm run build` does NOT type-check
npm run build
npm run lint                 # note: currently lints only .js/.jsx (AGENTS.md C12)

# Pipeline smoke run on real keyless data (network)
py -3.12 -m ml.pipelines.run --instrument FX:EURUSD --no-persist
```

- Write the tests along with the code: API cases, ML unit tests with hand-computed expected values, and leakage tests for features (AGENTS.md §14).
- Tests must not call live providers. Mock them or use the synthetic `TEST:DEMO` instrument (tests enable it with `AVENTRA_ENABLE_SYNTHETIC_TEST_DATA=1`; it is never a production fallback).
- If a test fails, fix the cause. Never skip, delete or weaken a test.

### VERIFY
Tests passing isn't the whole job. Verify the real integration path for whatever you changed:

- **Backend endpoint:** call it through the Flask test client or a short-lived local run and inspect the actual JSON, including the error paths.
- **Frontend ↔ backend:** confirm that the service function hits the right path with `VITE_API_BASE_URL` empty (dev proxy), that the response type matches the backend JSON field by field, and that the component renders each state. If you cannot run a browser, say so explicitly and describe what was verified statically.
- **ML pipeline:** run the stage on `TEST:DEMO` in tests and on a small real keyless sample (crypto, forex or a mutual fund) end to end. Check output shapes, ranges and NaNs. Check that past values don't change when future rows are removed. Check that the Flask payload contains the ML output unchanged.
- **UI:** check the AGENTS.md §22 widths for overflow, reduced-motion behaviour and keyboard focus.
- Stop any server you started once verification is done.

### DOCUMENT
- Update AGENTS.md §7 if a component's status changed, and §32 if you found or resolved a conflict. Update §31 if you found a new limitation.
- Update `.env.example`, `backend/README.md` or `readme.md`, and `docs/`, whenever setup, endpoints, env vars or architecture changed.
- For ML work, write the experiment record (AGENTS.md §13) to disk.

---

## 3. Does it already exist? (check before building anything)

| If the task mentions… | It already exists here — extend it, don't duplicate it |
|---|---|
| Sentiment, FinBERT, news analysis | `ml/news/finbert.py` (`get_news_analysis_service()`, `analyze`, `analyze_many`), `POST /api/news/analyze`, `frontend/src/services/newsApi.ts`, `components/news/NewsAnalysis.tsx` |
| News ingestion, entity linking, event categories | `ml/news/ingest.py`, `providers.py`, `entity.py`, `events.py`; `GET /api/news` |
| Instrument search, IDs, listings | `ml/instruments/{ids,master,sync,profiles}.py`, `/api/instruments/*`, `frontend/src/components/search/GlobalSearch.tsx` |
| Providers, rate limits, fallback | `ml/providers/` (`registry.py` router, `http.py`), `GET /api/providers` |
| Market snapshots, history, watchlist | `ml/data/market_data.py` → `backend/services/market_service.py` → `/api/market/*`, `/api/watchlists/default` → `frontend/src/services/intelligenceApi.ts` |
| Background jobs | `ml/jobs/{queue,worker}.py`, `POST /api/intelligence/<id>/runs`, `GET /api/jobs/<id>` |
| Validation, calendars/timezones, database | `ml/data/validation.py`, `calendars.py`, `db.py`, `store.py`, `migrate.py`, `backend/migrations/` |
| Features, fingerprint, detectors, ensemble | `ml/features/engineering.py`, `ml/fingerprint/baseline.py`, `ml/anomaly/*` |
| Correlation, risk, evidence | `ml/correlation/correlate.py`, `ml/risk/scoring.py`, `ml/evidence/chain.py` |
| The whole pipeline for one instrument | `ml/pipelines/intelligence.py::run_intelligence`, `GET /api/intelligence/<id>`, `frontend/src/components/intelligence/IntelligenceWorkspace.tsx` |
| Experiments / metrics | `ml/evaluation/*`, `experiments/results/`, `docs/17_MODEL_EVALUATION.md` |
| Frontend API calls, loading/error/unavailable states | `services/apiClient.ts`, `hooks/useApiResource.ts`, `components/intelligence/StateViews.tsx` (`DataUnavailableState`) |
| Health check | `GET /api/health` in `backend/app.py` |
| Service list and links | `frontend/src/data/services.ts` (used by `Navbar`, `Footer`, `Services`, `CapabilityPage`) |
| UI primitives, tones, 3D | `components/common/` (Button, Badge, Metric, Panel, SectionHeading, Logo), `components/visual/Scene3D` (lazy three.js), `styles/tokens.css` |
| Fingerprint, anomaly, correlation and risk pages | `frontend/src/pages/CapabilityPage.tsx` (API-backed panels) and the route map in `App.tsx` |
| Page titles and SEO | the `metadata` map in `App.tsx` |
| Buttons and headings | `components/common/Button.tsx`, `SectionHeading.tsx` |
| Pipeline diagram (How It Works) | `components/home/HowItWorks.tsx` (the `steps` array) |
| CORS and env config | `backend/app.py`, root `.env.example` (all backend variables), `frontend/.env.example` |

Also search before creating anything new:
```text
Grep: the concept name, the endpoint path, the likely function name, the CSS class prefix
Glob: backend/**/*<area>*, frontend/src/**/*<Area>*
```
If similar code exists, extend it. Create a new module only if the existing one would take on a second responsibility.

---

## 4. Safely modifying legacy code

- Most frontend components are written as **dense single-line JSX**. When you edit one, change only the part you need and keep that style. Don't reformat the whole file; that makes the diff unreadable to the user.
- Styles are split by layer (`tokens.css`, `base.css`, `site.css`, `intelligence.css`). Add rules next to the related block, use tokens only, and don't reflow existing lines.
- Keep exported names, props, CSS class names, URLs and JSON field names stable. If one must change, update every consumer in the same change and say so in the report.
- Currency, timezone and value kind always come from the API (`asset`, `capabilities`); never hard-code ₹, IST or an instrument list in the UI.
- Replacing a PLACEHOLDER with real data is encouraged. Keep the layout and styling, change the data source, and add the unavailable/empty states.
- Before deleting anything (including the known dead files `App.css`, `react.svg`, `vite.svg`), confirm it has zero references and get the user's OK.

---

## 5. Incremental implementation pattern

Build bottom-up. Each increment must leave the app working:

1. **Contract:** response schema (Python), then TS type in `frontend/src/types/`.
2. **Core logic:** ML-package function plus unit tests on fixtures (no Flask, no network).
3. **Service:** backend service calling the ML function, plus provider/caching/error mapping.
4. **Route:** blueprint endpoint plus API tests (valid, invalid, upstream failure).
5. **Client:** function in `frontend/src/services/`.
6. **UI:** component with all four states, wired into the existing page or route.
7. **Verify** end to end (§2 VERIFY), then **document** it.

The core pipeline (increments a–e of the original plan) was implemented on 2026-09-27. Suggested next increments, in order (see docs/25_LIMITATIONS.md). Confirm each with the user:
- a. Calibrate ensemble weights and threshold on **validation** data only; extend EXP-01 with multi-day/multi-feature injections and more seeds.
- b. A sourced known-event benchmark (never invent events), then detection-lead-time evaluation.
- c. Scheduled news ingestion, so historical anomalies get news context.
- d. A labelled news sample for entity-linking and relevant-news precision.
- e. Replace the `/doc` Coming Soon cards with real publications once they exist (C20).

---

## 6. ML-specific checklist (for any ML or data change)

Before you say an ML change is done, confirm each item. Say which ones you checked.
- [ ] Features use only past data (no centred windows); scalers and models are fit on the train split only.
- [ ] Split is chronological; boundaries are recorded.
- [ ] The same feature function serves training and inference.
- [ ] Missing values, duplicates, outliers vs data errors, UTC timestamps and calendar/session alignment are handled explicitly (AGENTS.md §11).
- [ ] A baseline is included for comparison.
- [ ] Seed, parameters, data version and feature list are saved with the artefact and results.
- [ ] Metrics suit the problem (PR-AUC, precision@k, FPR for rare anomalies); they are produced by a command you actually ran and saved to disk.
- [ ] Thresholds and weights live in config and are labelled "default, not validated" until calibrated.
- [ ] Insufficient history returns `insufficient_history`, not a score.
- [ ] Output wording follows AGENTS.md §13: no "predicts", no "caused".

---

## 7. Handling uncertainty and conflicting requirements

- **A fact you can check** (a file, a version, whether an endpoint exists, a label order): check it. Don't ask the user.
- **A decision that belongs to the user** (§32 conflicts, a new dependency, a breaking change, a rename or move, deleting their work, changing the design direction): ask one concise question, give a recommended option, and don't implement until they answer.
- **A minor ambiguity with an obvious conventional default:** pick the default, state the assumption in your report, and make it easy to change (put it in config).
- **A conflict between documents:** follow the hierarchy in AGENTS.md §5. If the hierarchy doesn't settle it, add it to AGENTS.md §32 and ask.
- If you notice that a master doc asks for something unsafe or dishonest (e.g. showing an unvalidated score as validated), follow AGENTS.md §29 and tell the user.

---

## 8. Reporting completed work

End every task with a short report in this order:

1. **What changed:** files created or modified, as clickable links, one line each.
2. **Status change:** which AGENTS.md §7 rows moved (e.g. "Fingerprinting: PLANNED → REAL (demo + NSE daily)").
3. **Verification:** the exact commands you ran and their results (pass/fail counts), plus what you checked end to end. Also list what you could **not** verify, and why.
4. **Assumptions and defaults chosen:** anything the user should confirm.
5. **Conflicts:** anything added to or resolved in §32.
6. **Next step:** the single most sensible next increment.

Report plainly. If tests failed or a step was skipped, say so first. Never describe placeholder output as working functionality, and never quote a metric the code didn't produce.
