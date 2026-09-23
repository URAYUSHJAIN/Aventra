# Aventra News Analysis API

The Flask API exposes financial-text sentiment analysis at `POST /api/news/analyze`.
It loads the local FinBERT model from `backend/models/finbert` once per server process.
The model directory is intentionally ignored by Git because it contains large model weights.

## Start locally

From the project root:

```powershell
py -3.12 -m pip install -r backend/requirements.txt
py -3.12 -m backend.app
```

Then start the frontend in a second terminal:

```powershell
cd frontend
npm run dev
```

Vite forwards browser requests from `/api` to Flask at `http://127.0.0.1:5000`.
For deployment on separate origins, set `VITE_API_BASE_URL` in the frontend and `CORS_ORIGINS` in the backend.

## Example request

```json
POST /api/news/analyze
{
  "text": "The company reported stronger quarterly earnings and raised its outlook."
}
```

The response contains a FinBERT label plus positive, neutral and negative probabilities and the score `positive_probability - negative_probability`.
