# Aventra — End-to-End ML Intelligence Pipeline
## Master Implementation Specification for Claude Code

> **Purpose:** This document is the single source of truth for implementing Aventra's ML + data + backend pipeline.
>
> **Core principle:** Aventra is one connected financial-intelligence pipeline, not five unrelated ML demos.
>
> **Pipeline:** Market + News → Alignment → Features → Behavioural Fingerprint → Anomaly Detection → Cross-Source Correlation → Temporal Analysis → Risk Assessment → Evidence Chain → Flask API → React Dashboard.

---

# 1. Project Identity

## 1.1 Product

**Aventra** is a financial intelligence platform designed to identify unusual market behaviour, connect that behaviour with financial news and sentiment, and present contextual, explainable evidence to a user.

## 1.2 Core UX statement

> **Detect Hidden Patterns. Understand Market Risk.**

## 1.3 Core technical idea

For an asset and time period, Aventra should:

1. Collect market observations.
2. Collect relevant financial news.
3. Analyse financial-news sentiment.
4. Align all signals on a common timeline.
5. Build an adaptive representation of normal asset behaviour.
6. Detect deviations from that behaviour.
7. Correlate market anomalies with news and sentiment events.
8. Analyse temporal order and time gaps.
9. Calculate a transparent behavioural-risk score.
10. Construct an evidence chain explaining the alert.
11. Expose the result through a Flask API.
12. Render it through the React/TypeScript frontend.

---

# 2. Non-Negotiable Architecture Principle

Do **not** implement the five website services as isolated systems.

The five user-facing capabilities are:

1. **Behavioural Fingerprinting**
2. **Anomaly Detection**
3. **AI Financial News Analysis**
4. **Cross-Source Event Correlation**
5. **Explainable Risk & Evidence**

They are stages of the same intelligence system.

```text
                  ┌─────────────────┐
                  │   Market Data   │
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │    News Data    │
                  └────────┬────────┘
                           │
                  ┌────────▼────────┐
                  │ Sentiment Model │
                  └────────┬────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ Alignment / Cleaning │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ Feature Engineering  │
                └──────────┬───────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │ Behavioural Fingerprint  │
              └────────────┬─────────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ Anomaly Detection    │
                └──────────┬───────────┘
                           │
                           ▼
              ┌──────────────────────────┐
              │ Cross-Source Correlation │
              └────────────┬─────────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ Temporal Analysis    │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ Risk Assessment      │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │ Evidence Chain       │
                └──────────┬───────────┘
                           │
                           ▼
                     Flask API
                           │
                           ▼
                 React Dashboard
```

---

# 3. Engineering Goals

The implementation must be:

- modular
- reproducible
- explainable
- testable
- locally runnable
- Docker-compatible
- suitable for a B.Tech final-year project
- suitable for research experiments
- easy to demonstrate
- easy to extend

Avoid unnecessary complexity.

Do not introduce deep-learning architectures merely to make the system look advanced.

---

# 4. Recommended Technology Stack

## Frontend

```text
React
TypeScript
Vite
Tailwind CSS
React Router
Recharts or another lightweight chart library
```

## Backend

```text
Python
Flask
Flask-CORS
Pydantic or Marshmallow for validation
```

## ML/Data

```text
Python
Pandas
NumPy
scikit-learn
SciPy
PyTorch
Transformers
FinBERT
```

## Storage

Development:

```text
SQLite
Parquet
local JSON where appropriate
```

Production-like local deployment:

```text
PostgreSQL
```

Do not introduce PostgreSQL until the basic pipeline works.

## Deployment

```text
Docker
Docker Compose
```

---

# 5. Repository Structure

Recommended final structure:

```text
Aventra/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── sections/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── types/
│   │   ├── utils/
│   │   └── assets/
│   ├── public/
│   ├── package.json
│   └── vite.config.ts
│
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── routes/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── utils/
│   ├── run.py
│   └── requirements.txt
│
├── ml/
│   ├── data/
│   │   ├── ingestion/
│   │   ├── preprocessing/
│   │   └── validation/
│   │
│   ├── features/
│   │
│   ├── news/
│   │
│   ├── fingerprint/
│   │
│   ├── anomaly/
│   │
│   ├── correlation/
│   │
│   ├── temporal/
│   │
│   ├── risk/
│   │
│   ├── evidence/
│   │
│   ├── evaluation/
│   │
│   └── pipelines/
│
├── models/
│   ├── finbert/
│   ├── anomaly/
│   └── fingerprint/
│
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   ├── features/
│   └── demo/
│
├── notebooks/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── pipeline/
│
├── docs/
│
├── docker/
│
├── scripts/
│
├── .env.example
├── docker-compose.yml
├── Dockerfile
└── README.md
```

---

# 6. Data Sources

Aventra should use a modular provider architecture.

Do not hard-code the entire application around one external provider.

## 6.1 Market data

Create a provider interface:

```python
class MarketDataProvider:
    def get_historical(self, symbol, start, end):
        ...

    def get_latest(self, symbol):
        ...
```

The implementation can use the project's selected market-data provider.

Required fields:

```text
symbol
timestamp
open
high
low
close
volume
```

Derived:

```text
return
log_return
rolling_mean
rolling_std
volatility
volume_change
volume_zscore
```

---

# 7. News Data

Create:

```python
class NewsProvider:
    def search(self, query, start, end):
        ...
```

Minimum fields:

```text
news_id
timestamp
headline
summary/body if available
source
url
symbol/entity mapping
```

Do not scrape websites in a brittle way unless explicitly required.

Use an adapter layer so the provider can be replaced.

---

# 8. Financial News Sentiment

Use the existing FinBERT implementation as the primary financial-text sentiment component.

Expected flow:

```text
News
 ↓
Text normalization
 ↓
FinBERT tokenizer
 ↓
FinBERT inference
 ↓
class probabilities
 ↓
sentiment label
 ↓
sentiment score
 ↓
confidence
```

Output:

```json
{
  "news_id": "N123",
  "symbol": "AAPL",
  "sentiment": "negative",
  "sentiment_score": -0.81,
  "confidence": 0.92
}
```

Do not retrain FinBERT initially.

Use the existing model for inference first.

---

# 9. Entity / Asset Mapping

A news item must be associated with an asset before cross-source analysis.

Mapping priority:

1. Explicit ticker/entity metadata.
2. Known company name.
3. Alias dictionary.
4. Controlled NLP/entity matching.
5. Manual/demo mapping for local demonstration data.

Do not claim an asset-news relationship when confidence is too low.

Store:

```text
entity_match_confidence
mapping_method
```

---

# 10. Data Alignment

This is one of the most important pipeline steps.

Market data and news do not arrive at identical timestamps.

Use:

```text
asset
timestamp
```

as the primary alignment keys.

Define configurable temporal windows.

Example:

```text
news → market event window = ±15 minutes
```

Do not hard-code the window throughout the project.

Use configuration:

```python
CORRELATION_WINDOW_MINUTES = 15
```

The exact value must be validated experimentally.

---

# 11. Market Preprocessing

Perform:

## Validation

Check:

```text
missing timestamps
duplicate rows
negative prices
zero/invalid volume
incorrect OHLC relationships
out-of-order timestamps
```

## Cleaning

Do not blindly delete outliers.

Distinguish:

```text
data error
vs
actual market anomaly
```

An extreme market movement may be the very event Aventra is supposed to detect.

---

# 12. News Preprocessing

Perform:

```text
duplicate removal
empty-text removal
timestamp normalization
HTML removal if needed
whitespace normalization
encoding normalization
```

Preserve original headline/body for evidence.

---

# 13. Feature Engineering

Feature engineering is a dedicated module.

## 13.1 Price features

```text
return_1
return_5
return_15
return_30
log_return
price_change
price_zscore
```

## 13.2 Volume features

```text
volume_change
volume_ratio
volume_zscore
rolling_volume_mean
```

## 13.3 Volatility

```text
rolling_std
realized_volatility
volatility_zscore
```

## 13.4 Momentum

Use only if justified:

```text
momentum
RSI
moving_average_distance
```

Avoid creating dozens of redundant indicators.

## 13.5 News features

```text
sentiment_score
sentiment_confidence
news_count
news_burst
sentiment_change
sentiment_mean
```

## 13.6 Cross-source features

```text
price_news_time_gap
volume_news_time_gap
sentiment_price_divergence
market_news_alignment
```

---

# 14. Feature Windowing

Features should be calculated using historical information only.

Never allow future observations to leak into a training or detection baseline.

For a timestamp `t`:

```text
history = observations < t
current = observation at t
```

Avoid:

```text
rolling mean centered around t
```

when that would include future data.

---

# 15. Behavioural Fingerprint

## 15.1 Definition

A behavioural fingerprint represents an asset's normal historical behaviour over selected dimensions.

Example:

```text
Fingerprint(asset, time_window)

= {
    price behaviour,
    return behaviour,
    volume behaviour,
    volatility behaviour,
    sentiment behaviour,
    news frequency,
    time-of-day behaviour
}
```

---

# 16. Fingerprint Baseline

For each asset:

```text
historical data
 ↓
rolling window
 ↓
normal distribution/statistics
 ↓
baseline
```

Store:

```text
mean
median
std
quantiles
rolling baseline
time-of-day baseline
```

Where useful, maintain separate baselines for:

```text
market open
mid-session
market close
```

because normal behaviour can vary by time of day.

---

# 17. Fingerprint Deviation

For each current observation calculate deviation from baseline.

A basic normalized deviation:

```text
z = (x - μ) / (σ + ε)
```

Then combine selected deviations:

```text
fingerprint_deviation =
    weighted_price_deviation
    + weighted_volume_deviation
    + weighted_volatility_deviation
    + weighted_sentiment_deviation
```

Normalize the resulting score.

Example output:

```json
{
  "fingerprint_score": 0.84,
  "deviation_level": "high"
}
```

Do not choose final weights arbitrarily.

Document them and validate them experimentally.

---

# 18. Adaptive Fingerprint

The baseline should update over time.

Use a rolling or exponentially weighted baseline.

Example:

```text
new_baseline =
    alpha * current_observation
    +
    (1-alpha) * previous_baseline
```

The adaptation rate must be configurable.

Important:

Anomalous observations should not automatically dominate the new baseline.

Consider a guarded update:

```text
if anomaly_score < threshold:
    update baseline
else:
    reduce update influence
```

This prevents the system from learning an abnormal event as "normal" too quickly.

---

# 19. Anomaly Detection

Use a layered approach.

## Layer 1 — Statistical

Examples:

```text
z-score
IQR
rolling deviation
```

## Layer 2 — Behavioural

Use:

```text
fingerprint deviation
```

## Layer 3 — ML baseline

Start with:

```text
Isolation Forest
```

Optional research experiments:

```text
One-Class SVM
Autoencoder
LSTM/Temporal model
```

Do not make advanced models mandatory for the first working version.

---

# 20. Isolation Forest

Input:

```text
selected engineered features
```

Output:

```text
raw anomaly score
binary anomaly state
```

Normalize scores to a consistent range.

Example:

```json
{
  "model": "isolation_forest",
  "anomaly_score": 0.78,
  "is_anomaly": true
}
```

---

# 21. Ensemble Anomaly Score

Combine:

```text
statistical_deviation
fingerprint_deviation
isolation_forest_score
```

Example conceptual formula:

```text
anomaly_score =
    w1 * statistical_score
  + w2 * fingerprint_score
  + w3 * ml_score
```

Where:

```text
w1 + w2 + w3 = 1
```

Initial weights should be treated as configurable.

Do not present them as scientifically optimal until validated.

---

# 22. Severity

Map anomaly score to:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

Example initial configuration:

```text
0.00–0.39 → LOW
0.40–0.64 → MEDIUM
0.65–0.84 → HIGH
0.85–1.00 → CRITICAL
```

These are implementation defaults only and should be calibrated using validation data.

---

# 23. Cross-Source Event Correlation

This module combines:

```text
market anomaly
news event
sentiment event
```

into a contextual event.

Example:

```text
10:01  Volume anomaly
10:03  Price deviation
10:05  Negative news
10:07  Sentiment shift
```

Group them if:

```text
same asset
+
within configured time window
+
relevant event types
```

---

# 24. Correlation Score

Possible components:

```text
time proximity
asset match confidence
sentiment strength
market anomaly strength
event relevance
```

Example:

```text
correlation_score =
    0.30 * temporal_proximity
  + 0.25 * asset_match
  + 0.20 * sentiment_strength
  + 0.25 * anomaly_strength
```

This is a starting engineering formula, not a validated scientific claim.

---

# 25. Temporal Analysis

For every correlated event, store:

```text
event_id
asset
event_timestamp
event_type
previous_event
time_gap
source
score
```

Construct a timeline:

```text
Market anomaly
      ↓ 2m
Price movement
      ↓ 3m
Financial news
      ↓ 2m
Sentiment shift
```

This is important for explainability.

---

# 26. Lead/Lag Analysis

Calculate:

```text
news → market
market → news
sentiment → market
market → sentiment
```

Do not infer causality from correlation.

The system should use language such as:

> "The events occurred within the configured time window."

Not:

> "The news caused the price movement."

---

# 27. Risk Assessment

Risk is a contextual score, not a prediction of future price.

Suggested components:

```text
market anomaly
fingerprint deviation
news sentiment
cross-source correlation
temporal consistency
model confidence
```

Example:

```text
risk_score =
    0.25 * anomaly_score
  + 0.20 * fingerprint_score
  + 0.15 * sentiment_strength
  + 0.20 * correlation_score
  + 0.10 * temporal_score
  + 0.10 * confidence_score
```

Normalize:

```text
0–100
```

Document all weights.

---

# 28. Risk Categories

Example:

```text
0–24    LOW
25–49   MODERATE
50–74   ELEVATED
75–100  HIGH
```

These categories are descriptive system outputs, not investment advice.

The UI must clearly state that Aventra provides analytical signals and evidence, not financial advice or guaranteed predictions.

---

# 29. Evidence Chain

Every important alert must contain evidence.

Minimum structure:

```json
{
  "event_id": "EV102",
  "symbol": "AAPL",
  "timestamp": "2026-09-27T10:05:00",
  "risk_score": 82,
  "evidence": [
    {
      "type": "volume",
      "description": "Volume exceeded rolling baseline",
      "value": 4.8,
      "source": "market"
    },
    {
      "type": "price",
      "description": "Price deviated from baseline",
      "value": 3.1,
      "source": "market"
    },
    {
      "type": "sentiment",
      "description": "Financial news sentiment was negative",
      "value": -0.81,
      "source": "finbert"
    }
  ]
}
```

---

# 30. Explainability

The dashboard should answer:

```text
WHAT happened?
WHEN did it happen?
HOW unusual was it?
WHAT signals contributed?
WHAT news was associated?
HOW close were the events in time?
WHY did Aventra assign this risk level?
```

Never expose unexplained model output alone.

---

# 31. Model Confidence

Every ML-derived output should have a confidence or reliability indicator where meaningful.

Examples:

```text
sentiment_confidence
entity_match_confidence
anomaly_model_confidence
correlation_confidence
```

Do not fabricate confidence values.

If a model does not produce calibrated probability, label the value appropriately.

---

# 32. API Architecture

Flask should be the only backend interface used by the frontend.

React must not directly access ML modules.

```text
React
 ↓
Flask API
 ↓
Service layer
 ↓
ML pipeline
 ↓
Data layer
```

---

# 33. API Endpoints

## Health

```http
GET /api/health
```

## Market

```http
GET /api/market/<symbol>
GET /api/market/<symbol>/history
```

## News

```http
GET /api/news/<symbol>
```

## Sentiment

```http
POST /api/news/analyze
```

## Fingerprint

```http
GET /api/fingerprint/<symbol>
```

## Anomaly

```http
GET /api/anomaly/<symbol>
POST /api/anomaly/detect
```

## Correlation

```http
GET /api/events/<symbol>
```

## Risk

```http
GET /api/risk/<symbol>
```

## Evidence

```http
GET /api/evidence/<event_id>
```

## Full analysis

```http
GET /api/intelligence/<symbol>
```

The last endpoint should return a consolidated dashboard payload.

---

# 34. Example Full API Response

```json
{
  "symbol": "AAPL",
  "timestamp": "2026-09-27T10:05:00Z",

  "market": {
    "price": 214.32,
    "return": 0.024,
    "volume": 1800000,
    "volatility": 0.017
  },

  "fingerprint": {
    "score": 0.84,
    "status": "high_deviation"
  },

  "anomaly": {
    "score": 0.78,
    "is_anomaly": true,
    "severity": "high"
  },

  "news": {
    "count": 4,
    "sentiment": -0.81,
    "confidence": 0.92
  },

  "correlation": {
    "score": 0.86,
    "event_count": 4
  },

  "risk": {
    "score": 82,
    "level": "HIGH"
  },

  "evidence": [
    {
      "type": "volume",
      "description": "Volume exceeded baseline"
    },
    {
      "type": "price",
      "description": "Price deviated from behavioural baseline"
    },
    {
      "type": "news",
      "description": "Negative financial-news sentiment detected"
    }
  ]
}
```

---

# 35. Frontend Dashboard

The dashboard is a visualization of the ML output.

Required modules:

```text
Asset selector
Market snapshot
Price chart
Volume chart
Behavioural fingerprint
Anomaly score
Risk score
News sentiment
Correlated events
Evidence timeline
```

---

# 36. Dashboard Layout

```text
┌──────────────────────────────────────────────────┐
│ AVENTRA                         Asset: AAPL       │
├──────────────────────────────────────────────────┤
│ Price      Change      Volume      Risk          │
├──────────────────────────────┬───────────────────┤
│ Price / Behaviour chart      │ Risk Score        │
│                              │ 82 HIGH           │
├──────────────────────────────┼───────────────────┤
│ Fingerprint deviation        │ News Sentiment    │
├──────────────────────────────┴───────────────────┤
│ Cross-Source Event Timeline                      │
├──────────────────────────────────────────────────┤
│ Evidence Chain                                   │
└──────────────────────────────────────────────────┘
```

---

# 37. Market Intelligence Homepage Section

The public landing page should show a controlled preview.

Do not expose the entire dashboard on the homepage.

Show:

```text
selected asset
current price
change
mini chart
anomaly indicator
sentiment
risk
```

A "View Intelligence" button can open the full intelligence view.

---

# 38. Loading States

Every API-driven component needs:

```text
loading
success
empty
error
```

Do not show blank panels.

---

# 39. Error Handling

Backend:

```text
invalid symbol → 400
not found → 404
provider failure → 502
internal error → 500
```

Frontend should show human-readable messages.

Never expose stack traces to users.

---

# 40. Caching

Do not request the same external market/news data repeatedly.

Use a basic cache layer.

Development:

```text
in-memory cache
```

Later:

```text
Redis
```

Do not introduce Redis until required.

---

# 41. Reproducibility

Every ML experiment must record:

```text
dataset
date range
features
model
parameters
random seed
training split
validation split
test split
metrics
```

Use:

```python
random_state=42
```

where supported.

---

# 42. Train / Validation / Test

Never randomly mix future and past observations for time-series experiments.

Use chronological splits.

Example:

```text
70% historical → train
15% subsequent → validation
15% latest → test
```

The exact ratio may change, but chronological separation is mandatory.

---

# 43. Data Leakage Prevention

Never use:

```text
future prices
future sentiment
future news
future rolling statistics
```

to calculate a historical feature.

All transformations that learn parameters must be fitted on training data only.

---

# 44. Evaluation Strategy

Evaluate each layer.

## News model

```text
accuracy
precision
recall
F1
confusion matrix
```

## Anomaly detection

Where labels exist:

```text
precision
recall
F1
PR-AUC
ROC-AUC
false-positive rate
```

Where labels do not exist:

Use:

```text
expert-reviewed event set
historical known-event set
precision@k
qualitative validation
```

Do not invent ground-truth labels.

---

# 45. End-to-End Evaluation

Measure:

```text
alert precision
false alerts per day
detection delay
evidence completeness
correlation accuracy
runtime
API latency
```

Aventra should be evaluated as a system, not only as individual models.

---

# 46. Required Baselines

At minimum compare:

```text
Baseline 1:
simple statistical anomaly detection

Baseline 2:
Isolation Forest

Baseline 3:
fingerprint + anomaly

Baseline 4:
fingerprint + anomaly + news correlation
```

This gives the research paper a clear experimental progression.

---

# 47. Ablation Study

Run:

```text
Full system

without fingerprint
without news
without sentiment
without correlation
without temporal analysis
```

Compare results.

This demonstrates which components contribute value.

---

# 48. Performance Metrics

Measure:

```text
ML inference time
API response time
data ingestion time
memory use
CPU use
```

For a B.Tech project, local reproducibility is more important than large-scale cloud deployment.

---

# 49. Testing

## Unit tests

Test:

```text
feature calculations
fingerprint calculations
anomaly scoring
risk scoring
event grouping
API schemas
```

## Integration tests

Test:

```text
data → ML pipeline
ML → Flask
Flask → frontend
```

## End-to-end

Test:

```text
symbol
 ↓
data
 ↓
pipeline
 ↓
API
 ↓
dashboard
```

---

# 50. Security

Do not expose:

```text
API keys
model paths
database credentials
```

Use `.env`.

Example:

```env
MARKET_API_KEY=
NEWS_API_KEY=
FLASK_ENV=development
```

Never commit `.env`.

---

# 51. Logging

Every pipeline stage should log:

```text
timestamp
module
asset
operation
status
duration
error if any
```

Avoid logging secrets.

---

# 52. Docker Architecture

Recommended:

```text
docker-compose.yml

services:

  frontend
      ↓
  backend
      ↓
  ml/backend runtime
      ↓
  database
```

For the first version, ML can run inside the backend container.

Do not create unnecessary microservices.

Later, if inference becomes heavy:

```text
frontend
backend
ml-worker
database
```

---

# 53. Local Run

Target:

```bash
docker compose up --build
```

Expected:

```text
Frontend → localhost:<frontend-port>
Backend  → localhost:<backend-port>
```

The exact ports should be defined in `.env` / Compose.

---

# 54. ML Pipeline CLI

Create:

```bash
python -m ml.pipelines.run --symbol AAPL
```

Expected flow:

```text
Load data
→ preprocess
→ features
→ fingerprint
→ anomaly
→ news sentiment
→ correlation
→ temporal analysis
→ risk
→ evidence
→ save result
```

---

# 55. Batch Processing

Also support:

```bash
python -m ml.pipelines.batch --symbols AAPL,MSFT,GOOGL
```

The system should process assets independently and produce standardized outputs.

---

# 56. Demo Mode

Because external APIs can fail during demonstrations, create a deterministic demo dataset.

Location:

```text
data/demo/
```

Demo should include:

```text
market.csv
news.json
sentiment.json
```

The demo must reproduce a known anomaly/event scenario.

This is essential for the final-year presentation.

---

# 57. Recommended Demo Scenario

Create a controlled sequence:

```text
T0:
normal market behaviour

T1:
volume spike

T2:
price deviation

T3:
negative financial news

T4:
sentiment shift

T5:
Aventra creates correlated event

T6:
risk score increases

T7:
evidence chain displayed
```

This will make the project easy to demonstrate.

---

# 58. Data Schema

## MarketObservation

```text
id
symbol
timestamp
open
high
low
close
volume
return
volatility
source
```

## NewsEvent

```text
id
timestamp
headline
body
source
url
symbol
entity_match_confidence
```

## SentimentResult

```text
news_id
label
score
confidence
model
```

## Fingerprint

```text
symbol
window
feature
baseline_mean
baseline_std
baseline_quantiles
updated_at
```

## AnomalyEvent

```text
id
symbol
timestamp
statistical_score
fingerprint_score
ml_score
anomaly_score
severity
```

## CorrelatedEvent

```text
id
symbol
start_time
end_time
events
correlation_score
```

## RiskAssessment

```text
event_id
risk_score
risk_level
components
created_at
```

## Evidence

```text
event_id
type
description
value
source
timestamp
```

---

# 59. Model Versioning

Store:

```text
model_name
model_version
training_date
dataset_version
parameters
```

Every result should be traceable to the model that generated it.

---

# 60. Configuration

Centralize configuration.

Example:

```python
WINDOW_5M = 5
WINDOW_15M = 15

ANOMALY_THRESHOLD = 0.65
CORRELATION_WINDOW = 15

RISK_WEIGHTS = {
    "anomaly": 0.25,
    "fingerprint": 0.20,
    "sentiment": 0.15,
    "correlation": 0.20,
    "temporal": 0.10,
    "confidence": 0.10,
}
```

Do not scatter constants across files.

---

# 61. Research Experiment Structure

Each experiment should have:

```text
Experiment ID
Objective
Dataset
Features
Model
Parameters
Results
Interpretation
Limitations
```

Example:

```text
EXP-03

Objective:
Evaluate whether behavioural fingerprinting reduces false alerts.

Baseline:
Isolation Forest

Experiment:
Fingerprint + Isolation Forest

Metric:
Precision / F1 / False Positive Rate
```

---

# 62. Research Paper Mapping

The implementation should produce evidence for:

## Research Question 1

Can adaptive behavioural profiling identify asset-specific deviations?

## Research Question 2

Does adding financial-news sentiment improve contextual anomaly detection?

## Research Question 3

Does cross-source temporal correlation reduce isolated false alerts?

## Research Question 4

Can evidence-chain explanations make anomaly alerts more interpretable?

These are research questions, not predetermined conclusions.

---

# 63. Patent/Disclosure Mapping

Maintain an internal implementation map:

```text
Adaptive Behavioural Fingerprinting
        ↓
ml/fingerprint/

Cross-Modal Analysis
        ↓
ml/correlation/

Temporal Analysis
        ↓
ml/temporal/

Behavioural Risk Score
        ↓
ml/risk/

Evidence Chain
        ↓
ml/evidence/

Explainable Dashboard
        ↓
frontend/
```

Do not alter patent/legal claims based solely on implementation convenience.

Patentability and legal scope require professional review.

---

# 64. What NOT to Build Initially

Do not start with:

```text
large Transformer trained from scratch
real-time Kafka cluster
Kubernetes
Redis cluster
complex graph database
multiple microservices
reinforcement learning
high-frequency trading engine
automatic trading
price prediction
portfolio management
```

These are scope risks.

The core system should work locally first.

---

# 65. Optional Advanced Research

After the core pipeline is stable:

```text
Temporal autoencoder
LSTM
Transformer
Graph-based event correlation
Continual learning
Concept drift detection
Online fingerprint adaptation
Multimodal embeddings
```

Each must be treated as an experiment.

Do not replace the working baseline without evidence.

---

# 66. Failure Scenarios

The system must handle:

```text
no market data
no news
FinBERT unavailable
invalid symbol
missing timestamps
duplicate news
provider timeout
API rate limit
model failure
empty feature set
insufficient historical data
```

Example:

If news is unavailable:

```text
Aventra can still run market anomaly detection.
```

But the UI must explicitly show:

```text
News context unavailable
```

Never silently substitute fabricated data.

---

# 67. Cold Start

An asset with insufficient history cannot have a reliable behavioural fingerprint.

Return:

```text
status = insufficient_history
```

Do not generate a misleading risk score.

Minimum history should be configurable.

---

# 68. Explainability Rules

Never say:

> "Aventra predicts the stock will fall."

Instead:

> "Aventra detected an unusual behavioural pattern associated with negative financial-news sentiment."

The system detects and contextualizes anomalies; it does not guarantee future price movements.

---

# 69. UI Language

Preferred:

```text
Anomaly detected
Elevated risk signal
Behavioural deviation
Associated news
Temporal relationship
Evidence
Confidence
```

Avoid:

```text
Guaranteed
Will crash
Buy
Sell
100% accurate
Certain
```

---

# 70. Frontend Service Layer

Example:

```text
frontend/src/services/api.ts
```

Functions:

```typescript
getMarketData(symbol)
getNews(symbol)
getFingerprint(symbol)
getAnomaly(symbol)
getRisk(symbol)
getEvents(symbol)
getEvidence(eventId)
getIntelligence(symbol)
```

Components should call service functions, not raw `fetch()` repeatedly.

---

# 71. TypeScript Types

Create:

```text
MarketData
NewsEvent
SentimentResult
FingerprintResult
AnomalyResult
CorrelatedEvent
RiskAssessment
EvidenceItem
IntelligenceResponse
```

Avoid `any`.

---

# 72. Frontend State

Use simple state first.

Do not add Redux unless the application actually requires global complex state.

Suggested:

```text
React state
React Query/TanStack Query if needed
```

---

# 73. Visual Dashboard Principle

The dashboard should show:

```text
DATA
 ↓
SIGNAL
 ↓
CONTEXT
 ↓
RELATIONSHIP
 ↓
RISK
 ↓
EVIDENCE
```

Not:

```text
10 random charts
```

---

# 74. Core Dashboard Components

```text
MarketSnapshot
PriceChart
VolumeChart
FingerprintChart
AnomalyIndicator
RiskScoreCard
SentimentCard
EventTimeline
EvidenceChain
NewsPanel
```

---

# 75. Landing Page Relationship

The public landing page should explain Aventra.

The intelligence dashboard should demonstrate Aventra.

Do not put every technical component into the marketing landing page.

---

# 76. Documentation Relationship

Create:

```text
/docs
```

with:

```text
Architecture
ML Pipeline
Data Pipeline
Models
API
Experiments
Research
Patent Mapping
```

The UI `/doc` route should present a simplified version.

The repository `docs/` contains the detailed engineering documentation.

---

# 77. Required Documentation Files

```text
docs/
├── 01_PROJECT_OVERVIEW.md
├── 02_PRD.md
├── 03_SRS.md
├── 04_SYSTEM_ARCHITECTURE.md
├── 05_ML_PIPELINE.md
├── 06_DATA_PIPELINE.md
├── 07_FEATURE_ENGINEERING.md
├── 08_BEHAVIORAL_FINGERPRINT.md
├── 09_ANOMALY_DETECTION.md
├── 10_CROSS_SOURCE_CORRELATION.md
├── 11_RISK_SCORING.md
├── 12_EXPLAINABILITY.md
├── 13_DATA_SCHEMA.md
├── 14_API_SPECIFICATION.md
├── 15_FRONTEND_ARCHITECTURE.md
├── 16_MODEL_TRAINING.md
├── 17_MODEL_EVALUATION.md
├── 18_EXPERIMENT_TRACKING.md
├── 19_TESTING.md
├── 20_SECURITY.md
├── 21_DEPLOYMENT.md
├── 22_DOCKER_ARCHITECTURE.md
├── 23_RESEARCH_MAPPING.md
├── 24_PATENT_FEATURE_MAPPING.md
├── 25_LIMITATIONS.md
└── 26_FUTURE_WORK.md
```

This master document should be the parent reference for these files.

---

# 78. Implementation Order

Claude Code should implement in this order.

## Phase 1 — Repository

1. Inspect existing repository.
2. Do not delete working functionality.
3. Identify current frontend/backend structure.
4. Create `docs/`.
5. Create configuration.
6. Create tests.

## Phase 2 — Data

7. Build market provider adapter.
8. Build news provider adapter.
9. Build data validation.
10. Build preprocessing.
11. Create demo dataset.

## Phase 3 — News ML

12. Integrate existing FinBERT.
13. Build sentiment service.
14. Build entity/asset mapping.
15. Test inference.

## Phase 4 — Features

16. Implement price features.
17. Implement volume features.
18. Implement volatility features.
19. Implement news features.
20. Implement cross-source features.

## Phase 5 — Fingerprinting

21. Implement baseline.
22. Implement deviation.
23. Implement adaptive update.
24. Add unit tests.

## Phase 6 — Anomaly

25. Implement statistical detector.
26. Implement Isolation Forest.
27. Normalize scores.
28. Implement ensemble score.
29. Calibrate thresholds.

## Phase 7 — Correlation

30. Implement temporal windows.
31. Implement event grouping.
32. Implement correlation score.
33. Implement lead/lag metadata.

## Phase 8 — Risk

34. Implement risk score.
35. Implement risk level.
36. Implement component contribution output.

## Phase 9 — Evidence

37. Build evidence chain.
38. Build explanation generator.
39. Store evidence.

## Phase 10 — API

40. Build Flask routes.
41. Add validation.
42. Add error handling.
43. Add API tests.

## Phase 11 — Frontend

44. Connect React to Flask.
45. Build intelligence dashboard.
46. Build charts.
47. Build event timeline.
48. Build evidence chain UI.

## Phase 12 — Evaluation

49. Create baseline experiments.
50. Create ablation experiments.
51. Calculate metrics.
52. Save results.

## Phase 13 — Docker

53. Create Dockerfiles.
54. Create Compose.
55. Test clean machine setup.

## Phase 14 — Documentation

56. Update architecture.
57. Update ML pipeline.
58. Update API docs.
59. Update experiment results.
60. Update README.

---

# 79. Definition of Done — ML Core

The ML core is complete only when:

- [ ] Market data can be ingested.
- [ ] News can be ingested.
- [ ] Financial news receives sentiment analysis.
- [ ] Market and news timestamps are aligned.
- [ ] Features are generated without leakage.
- [ ] Behavioural fingerprint is generated.
- [ ] Fingerprint adapts safely.
- [ ] Anomalies are detected.
- [ ] Multiple anomaly signals can be combined.
- [ ] Market/news events can be correlated.
- [ ] Temporal relationships are preserved.
- [ ] Risk score is generated transparently.
- [ ] Evidence chain is generated.
- [ ] Results are available through Flask.
- [ ] React can display results.
- [ ] Demo mode works without external APIs.
- [ ] Tests pass.
- [ ] Pipeline is reproducible.

---

# 80. Definition of Done — Research

- [ ] Baselines are defined.
- [ ] Experimental dataset is documented.
- [ ] Chronological train/test split is used where applicable.
- [ ] Leakage checks are documented.
- [ ] Metrics are defined before experiments.
- [ ] Ablation study is performed.
- [ ] Results are reproducible.
- [ ] Limitations are documented.
- [ ] No unsupported novelty claims are made.

---

# 81. Definition of Done — Deployment

Run:

```bash
docker compose up --build
```

Then verify:

```text
Frontend loads
Backend health works
API returns data
ML pipeline runs
Demo scenario works
Dashboard displays evidence
```

---

# 82. Claude Code Operating Rules

When implementing this repository:

## Rule 1

**Inspect before modifying.**

Read:

```text
README.md
existing source code
package.json
requirements.txt
existing docs
existing ML code
existing FinBERT clone
```

before making architectural changes.

## Rule 2

Do not rewrite working code unnecessarily.

## Rule 3

Reuse existing FinBERT implementation if functional.

## Rule 4

Do not duplicate ML logic between Flask and the ML package.

The ML package owns the intelligence.

## Rule 5

Flask is an orchestration/API layer.

## Rule 6

React is a presentation layer.

## Rule 7

All configuration belongs in configuration files/environment variables.

## Rule 8

Every major ML function needs a unit test.

## Rule 9

No hard-coded API keys.

## Rule 10

No fabricated data in production mode.

Demo data must be clearly separated.

## Rule 11

Do not introduce advanced infrastructure until the basic pipeline works.

## Rule 12

When a design decision is uncertain, document the assumption rather than silently inventing behaviour.

---

# 83. Final System

The final Aventra architecture should conceptually look like this:

```text
                    AVENTRA
                       │
          ┌────────────┴────────────┐
          │                         │
     MARKET DATA                NEWS DATA
          │                         │
          │                    FINBERT
          │                         │
          └────────────┬────────────┘
                       │
                       ▼
               DATA ALIGNMENT
                       │
                       ▼
              FEATURE ENGINEERING
                       │
                       ▼
          ADAPTIVE BEHAVIOURAL
                 FINGERPRINT
                       │
                       ▼
             ANOMALY DETECTION
                       │
                       ▼
           CROSS-SOURCE CORRELATION
                       │
                       ▼
              TEMPORAL ANALYSIS
                       │
                       ▼
                RISK SCORE
                       │
                       ▼
               EVIDENCE CHAIN
                       │
                       ▼
                 FLASK API
                       │
                       ▼
               REACT DASHBOARD
```

---

# 84. The Core Research Contribution

The project should not be presented as:

> "We built an AI stock prediction website."

The technically stronger description is:

> **Aventra is an explainable financial-intelligence pipeline that combines adaptive behavioural profiling, anomaly detection, financial-news sentiment and cross-source temporal correlation to contextualize unusual market behaviour.**

This distinction should remain consistent across:

```text
implementation
README
research paper
presentation
viva
documentation
```

---

# 85. Final MVP Boundary

The minimum complete Aventra system is:

```text
Market Data
+
Financial News
+
FinBERT
+
Feature Engineering
+
Adaptive Behavioural Fingerprint
+
Isolation Forest / Statistical Anomaly Detection
+
Cross-Source Correlation
+
Temporal Event Timeline
+
Transparent Risk Score
+
Evidence Chain
+
Flask API
+
React Dashboard
+
Docker
+
Demo Dataset
+
Evaluation
```

Everything else is optional until this pipeline is stable.

---

# 86. Final Implementation Philosophy

Build **depth before breadth**.

One excellent end-to-end intelligence pipeline is more valuable than many disconnected AI features.

The product story should always remain:

```text
Market
  ↓
Behaviour
  ↓
Deviation
  ↓
News
  ↓
Context
  ↓
Correlation
  ↓
Risk
  ↓
Evidence
```

The final user should be able to select an asset and understand:

> **What changed, how unusual it is, what else was happening at the same time, and why Aventra flagged it.**

That is the core Aventra experience.
