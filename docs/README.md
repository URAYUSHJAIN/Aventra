# Aventra engineering documentation

Numbering follows the list in `context/AVENTRA_MASTER_ML_PIPELINE.md` §77; files are added as the corresponding work exists (no placeholder documents).

| File | Contents |
|---|---|
| [04_SYSTEM_ARCHITECTURE.md](04_SYSTEM_ARCHITECTURE.md) | Layers, request flow, storage, routes, key decisions |
| [05_ML_PIPELINE.md](05_ML_PIPELINE.md) | Data, features, fingerprint, anomaly, news, correlation, risk, evidence — as implemented, with formulas |
| [14_API_SPECIFICATION.md](14_API_SPECIFICATION.md) | Every endpoint, envelope, status codes, payload schema |
| [17_MODEL_EVALUATION.md](17_MODEL_EVALUATION.md) | EXP-01 synthetic injection, EXP-02 FinBERT PhraseBank, what is not yet evaluated |
| [19_TESTING.md](19_TESTING.md) | Test suites, commands, coverage, latest results |
| [21_DEPLOYMENT.md](21_DEPLOYMENT.md) | Docker Compose, local development, Vercel, CLIs, environment |
| [25_LIMITATIONS.md](25_LIMITATIONS.md) | Data/model/engineering limitations and ordered future work |

Agent rules: [../AGENTS.md](../AGENTS.md) and [../CLAUDE.md](../CLAUDE.md). Experiment records: [../experiments/results/](../experiments/results/).
