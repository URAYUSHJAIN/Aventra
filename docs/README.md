# Aventra engineering documentation

Numbering follows the list in `context/AVENTRA_MASTER_ML_PIPELINE.md` §77; files are added as the corresponding work exists (no placeholder documents).

| File | Contents |
|---|---|
| [04_SYSTEM_ARCHITECTURE.md](04_SYSTEM_ARCHITECTURE.md) | Layers, identity, request flow, storage, background jobs, routes, key decisions |
| [06_DATA_SOURCES_AND_PROVIDERS.md](06_DATA_SOURCES_AND_PROVIDERS.md) | Implemented providers (roles, credentials, limits) + the Phase 0 verification record |
| [05_ML_PIPELINE.md](05_ML_PIPELINE.md) | Data, features, fingerprint, anomaly, news, correlation, risk, evidence — as implemented, with formulas |
| [14_API_SPECIFICATION.md](14_API_SPECIFICATION.md) | Every endpoint, envelope, status codes, payload schema |
| [17_MODEL_EVALUATION.md](17_MODEL_EVALUATION.md) | EXP-03 multi-asset synthetic injection, EXP-01 (v0.1 record), EXP-02 FinBERT PhraseBank, what is not yet evaluated |
| [19_TESTING.md](19_TESTING.md) | Test suites, commands, coverage, latest results |
| [21_DEPLOYMENT.md](21_DEPLOYMENT.md) | Docker Compose (postgres, backend, worker, frontend), local development, Vercel, CLIs, environment |
| [25_LIMITATIONS.md](25_LIMITATIONS.md) | Data/model/engineering limitations and ordered future work |

Agent rules: [../AGENTS.md](../AGENTS.md) and [../CLAUDE.md](../CLAUDE.md). Experiment records: [../experiments/results/](../experiments/results/).
