# Aventra API (Flask)

Flask app factory in `app.py`; blueprints in `routes/` (`news_routes`, `market_routes`, `intelligence_routes`); orchestration in `services/`; shared envelope and validation in `utils/responses.py`. All model and data logic lives in the `ml/` package at the repository root — the backend only orchestrates it.

`services/news_analysis_service.py` re-exports the FinBERT service now located in `ml/news/finbert.py`, so existing imports keep working. The model loads from `backend/models/finbert` once per process (the directory is git-ignored because of the 438 MB weights).

## Start locally (from the repository root)

```powershell
py -3.12 -m pip install -r backend/requirements.txt
py -3.12 -m backend.app          # PORT and FLASK_DEBUG env vars are honoured
```

Endpoints: see [../docs/14_API_SPECIFICATION.md](../docs/14_API_SPECIFICATION.md). Tests: `py -3.12 -m unittest discover -s backend/tests -t .`

## Example

```json
POST /api/news/analyze
{ "text": "The company reported stronger quarterly earnings and raised its outlook." }
```

Returns the FinBERT label, the three class probabilities and `sentiment_score = positive − negative` (original fields), plus `sentiment`, `confidence`, `model`, `model_version`, `timestamp`, `source` and `text`.
