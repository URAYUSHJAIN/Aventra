# 25 — Limitations and Future Work

## Data

- **Market provider:** Yahoo Finance's chart endpoint is unofficial and keyless; it can change, rate-limit or disappear. Stored prices are used as a fallback (marked `stale`). Daily bars only for analytics; intraday history from free providers is too short for multi-year evaluation.
- **News provider:** Google News RSS returns recent headlines (≈ 30 days) without article bodies; older anomalies usually have no aligned news unless the store accumulated it earlier. Coverage and source quality vary.
- **Entity linking** is alias-based; ambiguous names are guarded with exclusion lists but misses and false links remain possible. Accuracy has not been measured.
- **Asset universe:** five NSE large caps plus a synthetic DEMO asset. TATAMOTORS (Final Plan §26) was delisted on the provider after the demerger and was not added.
- **Demo data** is synthetic and exists only for offline demonstration and tests.

## Models

- FinBERT: English only, 64-token sentence inputs, document score is an unweighted sentence mean; confidence is an uncalibrated softmax value. Its PhraseBank evaluation overlaps with its training data.
- All thresholds and weights (ensemble, severity, correlation, risk) are uncalibrated defaults. EXP-01 shows the production ensemble does **not** outperform the simple statistical baseline on synthetic single-bar anomalies.
- LSTM autoencoder and LOF are experimental (EXP-01 only). Change points are retrospective annotations and are excluded from detection and risk.
- No trained risk model, so no SHAP explanations; the risk score is a transparent formula with exact linear contributions.
- Correlation is temporal/asset alignment, never causation. Lead/lag analysis requires ≥ 20 news days and is usually `insufficient_data` with RSS coverage.

## Engineering

- Single-process cache and per-symbol locks (fine for one gunicorn worker; multiple workers would each run the pipeline).
- Cold analyses take 9–30 s (model loading, provider calls).
- ESLint does not lint TypeScript; `tsc` is the type gate.
- Frontend uses a manual router (no React Router) and hand-drawn SVG charts (no chart library).
- Design-specification items not implemented: `/doc` route, Research & Documentation cards (no real patent/paper documents exist), contact globe, homepage reordering (see AGENTS.md C11, C20).

## Future work (ordered)

1. Calibrate ensemble weights and the flag threshold on validation data only; add multi-day/multi-feature injection types and more seeds.
2. Curate a sourced known-event benchmark per asset and evaluate detection lead time.
3. Hand-label a news sample to measure entity-linking and relevant-news precision.
4. Persistent news collection (scheduled ingestion) so historical anomalies have news context.
5. A trained risk model with SHAP once labelled outcomes exist.
6. PostgreSQL + a background worker if multi-user load requires it.
