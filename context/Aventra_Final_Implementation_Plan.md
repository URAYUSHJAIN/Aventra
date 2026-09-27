# Aventra — Final Implementation Plan

## 1. Project Goal

Aventra is a local-first financial intelligence platform connecting:

**Market behaviour → anomaly detection → financial news → sentiment → cross-source correlation → risk signal → evidence chain**

The system is not a generic stock predictor or trading bot. Its purpose is to identify unusual market behaviour, find relevant contextual information, correlate the signals, and explain why an event was flagged.

---

## 2. Final Feature Set

| Module | Purpose | Initial Model / Technology |
|---|---|---|
| Live Market Intelligence | Price, volume, OHLCV, returns and market context | yfinance / market API |
| AI Financial News Analysis | Financial-text sentiment | FinBERT |
| Adaptive Behavioural Fingerprinting | Learn normal asset behaviour | Rolling median/MAD baseline |
| Anomaly Detection | Detect unusual behaviour | Isolation Forest + LOF + LSTM Autoencoder |
| Change-Point Detection | Detect regime/behaviour shifts | ruptures / PELT |
| Cross-Source Event Correlation | Link market anomalies with news/events | Timestamp + ticker/entity matching + embeddings |
| Risk & Evidence Analysis | Explain detected events | Transparent risk score + SHAP later |

---

## 3. Overall System Pipeline

```text
                    AVENTRA
                       |
        +--------------+--------------+
        |              |              |
        v              v              v
   Market Data     Financial News   Market Events
        |              |
        v              v
  Price/Volume      FinBERT
        |           Sentiment
        |              |
        +-------+------+
                |
                v
        Feature Engineering
                |
                v
     Adaptive Behavioural
          Fingerprint
                |
                v
        Anomaly Detection
                |
                v
       Cross-Source Event
          Correlation
                |
                v
          Temporal Analysis
                |
                v
           Risk Scoring
                |
                v
          Evidence Chain
                |
                v
         Aventra Dashboard
```

---

## 4. Architecture

### Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- React Router
- Reusable feature components
- API service layer

### Backend

- Python
- Flask
- REST API
- Background/scheduled data ingestion
- ML inference services
- Database access

### ML

- FinBERT
- Robust statistical baseline
- Isolation Forest
- Local Outlier Factor
- LSTM Autoencoder
- Change-point detection
- Sentence Transformers
- Risk model
- SHAP

### Database

Start with SQLite for local development/demo and keep the schema migration-friendly for PostgreSQL later.

### Deployment

- Docker
- Docker Compose

---

## 5. Existing Project Status

The current Aventra project already contains:

- React/Vite/Tailwind frontend
- Flask backend
- FinBERT news-analysis endpoint
- Live market panel
- Behavioural Fingerprinting page
- Anomaly Detection page
- Cross-Source Event Correlation page
- Risk & Evidence page

The four intelligence pages should now be converted from mock/static visualizations into real API-backed features.

**Do not rewrite working functionality unnecessarily.**

---

# 6. Phase 0 — Repository Audit and Foundation

### Tasks

1. Inspect the complete existing repository.
2. Identify frontend entry points.
3. Identify Flask entry point.
4. Identify existing API routes.
5. Identify existing services.
6. Identify existing components.
7. Identify environment configuration.
8. Identify current dependencies.
9. Inspect the existing FinBERT repository.
10. Document the current architecture.

### Deliverable

`docs/current-architecture.md`

---

# 7. Phase 1 — Production-Ready Data Layer

## Market Data

Move market-data retrieval behind Flask.

```text
Market Provider
      ↓
Flask Market Service
      ↓
Database
      ↓
React
```

Do not make the frontend directly dependent on the market provider.

### Store

- ticker
- timestamp
- open
- high
- low
- close
- adjusted close if available
- volume

### Derived features

- percentage return
- rolling return
- volatility
- volume change
- price gap
- intraday range
- distance from rolling mean
- benchmark-relative return

---

# 8. Phase 2 — Financial News Pipeline

The existing FinBERT implementation remains the foundation.

```text
News Source
   ↓
News Ingestion
   ↓
Deduplication
   ↓
Ticker / Entity Linking
   ↓
Text Cleaning
   ↓
FinBERT
   ↓
Sentiment
   ↓
Database
```

### Store

- title
- source
- URL
- published timestamp
- article text/excerpt
- ticker/entity
- sentiment label
- positive probability
- neutral probability
- negative probability
- sentiment score

### Important

FinBERT is a financial-text sentiment model.

Do not describe it as:

- fake-news detection
- AI-generated-news detection
- fraud detection
- market manipulation detection

Those are separate problems requiring separate models and validation.

---

# 9. Phase 3 — Adaptive Behavioural Fingerprinting

This is the central Aventra component.

## Step 1 — Feature vector

For every asset/time window:

```text
Return
Volume
Volatility
Gap %
Intraday Range
RSI
VWAP distance
Benchmark-relative return
Sentiment where available
```

## Step 2 — Robust baseline

Start with:

```text
Rolling Median
+
MAD
+
Robust Z-score
```

This establishes what normal behaviour looks like for each asset.

## Step 3 — Fingerprint

```text
Asset
  ↓
Historical features
  ↓
Rolling baseline
  ↓
Current deviation
  ↓
Behavioural fingerprint
```

### V2

After the statistical baseline is validated:

```text
Feature sequences
      ↓
LSTM Encoder
      ↓
Embedding
      ↓
Behavioural fingerprint
```

Do not begin with LSTM before the baseline works.

---

# 10. Phase 4 — Anomaly Detection

Use complementary methods.

### Model A — Isolation Forest

Baseline machine-learning detector.

### Model B — Local Outlier Factor

Second detector for local-density anomalies.

### Model C — LSTM Autoencoder

Temporal sequence reconstruction:

```text
Sequence
  ↓
Encoder
  ↓
Latent representation
  ↓
Decoder
  ↓
Reconstruction error
```

### Model D — Change Point Detection

Use `ruptures` / PELT.

```text
Price/Volume sequence
       ↓
PELT
       ↓
Change point
```

---

# 11. Anomaly Ensemble

Combine normalized signals:

```text
Isolation Forest
       +
LOF
       +
LSTM reconstruction
       +
Change-point signal
       ↓
Normalized anomaly score
```

Initial UI bands may be configurable:

```text
0–30    Normal
30–60   Watch
60–80   Unusual
80–100  High anomaly
```

These are initial product thresholds, not validated scientific thresholds until experiments establish them.

---

# 12. Phase 5 — Cross-Source Event Correlation

This is the main integration feature.

### Inputs

```text
Market anomaly
+
Financial news
+
Ticker/entity
+
Timestamp
+
Sentiment
```

### Pipeline

```text
Market anomaly
      ↓
Candidate news selection
      ↓
Time-window filtering
      ↓
Ticker/entity matching
      ↓
Semantic similarity
      ↓
Event classification
      ↓
Correlation score
```

### Important

Correlation does not automatically prove causation.

Use terms such as:

- correlated with
- associated with
- relevant context
- temporally aligned

unless causal evidence has actually been established.

---

# 13. Semantic Matching

Use Sentence Transformers.

Initial lightweight model:

`all-MiniLM-L6-v2`

```text
Article
   ↓
Embedding

Event description
   ↓
Embedding

        ↓
Cosine similarity
        ↓
Relevance score
```

Store the similarity score with the event record.

---

# 14. Event Classification

Initial categories:

```text
Earnings
Merger / Acquisition
Regulatory
Management Change
Corporate Action
Fraud / Investigation
Legal
Macroeconomic
Market-wide
Other
```

Start with zero-shot classification or rules where appropriate.

Do not train a custom classifier until sufficient labelled data exists.

---

# 15. Phase 6 — Risk & Evidence Analysis

The risk module should explain the event rather than simply output a number.

## Initial risk model

```text
Risk =
    w1 × PriceDeviation
  + w2 × VolumeDeviation
  + w3 × Sentiment
  + w4 × EventSeverity
  + w5 × ChangePoint
```

Weights must be configurable and later calibrated using validation data.

### Output

```text
Risk Signal: <model output>

Contributing signals:

Price deviation       <model contribution>
Volume deviation      <model contribution>
Sentiment             <model contribution>
Event severity        <model contribution>
Change point          <model contribution>
```

Never hard-code these values.

---

# 16. Explainability

When a trained risk model is introduced, integrate SHAP.

```text
Risk = model output

SHAP contributions:

Volume deviation     +XX
Price deviation      +XX
Negative sentiment   +XX
Event severity       +XX
Change point         +XX
```

The values must come from the actual model.

---

# 17. Evidence Chain

Every high-priority anomaly should have an evidence timeline.

```text
10:15  Volume anomaly detected
10:17  Price deviation detected
10:18  Relevant news published
10:18  Negative sentiment detected
10:18  Entity matched
10:20  Behavioural deviation confirmed
```

Evidence should contain:

- timestamp
- signal
- source
- value/score
- explanation
- linked article where applicable

---

# 18. Database Schema

Recommended tables:

```text
assets
prices
news
news_sentiment
features
fingerprints
anomalies
events
risk_scores
evidence
```

Relationship:

```text
Asset
 |
 +-- Prices
 |
 +-- News
 |     |
 |     +-- Sentiment
 |
 +-- Features
 |     |
 |     +-- Fingerprint
 |
 +-- Anomalies
       |
       +-- Events
             |
             +-- Risk
                   |
                   +-- Evidence
```

---

# 19. Backend API

Recommended endpoints:

```text
GET  /api/market/<ticker>
GET  /api/market/<ticker>/history

GET  /api/news
POST /api/news/analyze

GET  /api/fingerprint/<ticker>

GET  /api/anomalies
GET  /api/anomalies/<id>

GET  /api/events
GET  /api/events/<id>

GET  /api/risk/<ticker>

GET  /api/evidence/<anomaly_id>
```

Keep the existing `/api/news/analyze` compatible unless there is a strong reason to change it.

---

# 20. Frontend Implementation

Convert the existing mock pages into real API-backed pages.

## Main Dashboard

```text
Asset Search
     ↓
Current Price
     ↓
Price/Volume Chart
     ↓
Behaviour Status
     ↓
Anomaly Markers
     ↓
News Timeline
     ↓
Risk Signal
     ↓
Evidence Chain
```

## Behavioural Fingerprint

Show:

- historical behaviour
- current behaviour
- deviation
- fingerprint features
- normal vs unusual status

## Anomaly Detection

Show:

- anomaly score
- detection model agreement
- affected features
- timeline
- severity

## Cross-Source Event Correlation

Show:

- market event
- relevant article
- sentiment
- timestamps
- entity match
- semantic relevance
- correlation explanation

## Risk & Evidence

Show:

- risk signal
- contributing factors
- evidence timeline
- linked news
- model explanation

---

# 21. Frontend Structure

Adapt this to the actual repository:

```text
frontend/src/
├── components/
│   ├── dashboard/
│   ├── market/
│   ├── news/
│   ├── fingerprint/
│   ├── anomaly/
│   ├── correlation/
│   └── risk/
├── pages/
├── services/
├── hooks/
├── types/
└── utils/
```

Use a frontend API service layer instead of putting API calls directly inside components.

---

# 22. ML Structure

```text
ml/
├── preprocessing/
├── fingerprint/
├── anomaly/
├── correlation/
├── risk/
├── evaluation/
└── notebooks/
```

Keep experiments separate from production inference code.

---

# 23. Final Repository Structure

```text
Aventra/
│
├── frontend/
├── backend/
│   ├── app.py
│   ├── routes/
│   ├── services/
│   ├── models/
│   ├── schemas/
│   ├── database/
│   ├── tasks/
│   └── tests/
│
├── ml/
│   ├── preprocessing/
│   ├── fingerprint/
│   ├── anomaly/
│   ├── correlation/
│   ├── risk/
│   └── evaluation/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── external/
│
├── experiments/
│   ├── results/
│   ├── figures/
│   └── tables/
│
├── finBERT/
├── docker/
├── docs/
├── docker-compose.yml
├── .env.example
├── README.md
└── .gitignore
```

Create modules progressively; do not create empty directories only for appearance.

---

# 24. Testing Strategy

## Backend

Test:

- valid request
- empty input
- missing input
- invalid JSON
- model loading failure
- inference failure
- unavailable market provider

## Frontend

Test:

- loading
- success
- empty state
- API error
- backend unavailable
- responsive layout

## ML

Test:

- preprocessing
- feature calculations
- model inference
- anomaly score generation
- correlation scoring
- risk calculation

---

# 25. Evaluation

## FinBERT

Use an appropriate labelled financial sentiment dataset such as Financial PhraseBank.

Report:

- Accuracy
- Precision
- Recall
- F1
- Confusion Matrix

## Anomaly Detection

Use known historical events and controlled synthetic anomaly injection.

Report:

- Precision
- Recall
- F1
- False Positive Rate
- Precision@K
- Detection Lead Time

## Event Correlation

Evaluate:

- ticker/entity matching accuracy
- relevant-news precision
- semantic similarity quality
- event matching precision/recall

## Risk Model

Evaluate where labelled data supports it:

- calibration
- classification metrics
- false positive rate
- stability across assets

Do not claim effectiveness merely from visually convincing dashboard output.

---

# 26. Dataset and Experimental Strategy

Start with a manageable universe:

```text
RELIANCE
TCS
INFY
HDFCBANK
ICICIBANK
TATAMOTORS
```

Expand only when computationally feasible.

Include:

- normal periods
- high-volatility periods
- known corporate events
- earnings periods
- regulatory events
- market-wide events

Avoid train/test leakage.

---

# 27. Known-Event Evaluation

Create a historical event benchmark containing:

```text
Event date
Asset
Event category
Market movement
Volume behaviour
Relevant news
Sentiment
Expected detection window
```

Evaluate whether Aventra detects each event and how early.

Do not select only successful examples for final performance claims.

---

# 28. Synthetic Anomaly Evaluation

Create controlled anomalies such as:

```text
Sudden price spike
Sudden price drop
Volume spike
Volatility spike
Combined price-volume anomaly
Regime shift
```

Keep synthetic data separate from real-world evaluation.

---

# 29. Model Development Order

Use this order:

```text
1. Statistical baseline
        ↓
2. Isolation Forest
        ↓
3. LOF
        ↓
4. Change-point detection
        ↓
5. LSTM Autoencoder
        ↓
6. Ensemble
        ↓
7. Cross-source correlation
        ↓
8. Risk model
        ↓
9. Explainability
```

This gives meaningful baselines and a defensible research comparison.

---

# 30. Docker Plan

Final local workflow:

```bash
docker compose up --build
```

Services:

```text
aventra-frontend
aventra-backend
aventra-db
```

Do not create a separate container for every ML algorithm. FinBERT, anomaly models and risk models can initially run in the backend ML environment.

```text
              Docker Compose
                    |
       +------------+------------+
       |            |            |
       v            v            v
   Frontend      Backend      Database
   React         Flask        SQLite/
   Vite                        PostgreSQL
                    |
                    v
                ML Pipeline
```

---

# 31. Local Run Target

The final local workflow should be:

```bash
docker compose up --build
```

Then:

```text
http://localhost
```

The system should provide:

```text
React
 ↓
Flask
 ↓
Database
 ↓
ML services
```

---

# 32. Technical References

Use these repositories as technical references rather than blindly copying code.

### FinBERT

https://github.com/ProsusAI/finBERT

Financial sentiment analysis.

### Sentence Transformers

https://github.com/UKPLab/sentence-transformers

Semantic embeddings and similarity.

### ruptures

https://github.com/deepcharles/ruptures

Change-point detection and PELT.

For Isolation Forest, LOF, LightGBM/XGBoost and SHAP, use the established Python packages and official documentation rather than copying unrelated repositories.

---

# 33. Scope Control

Do not add:

- generic chatbot
- stock price prediction
- buy/sell recommendations
- automatic trading
- portfolio management
- crypto trading
- payment systems
- unnecessary authentication
- unrelated AI features

Keep the core:

```text
Market behaviour
      ↓
Anomaly
      ↓
News context
      ↓
Correlation
      ↓
Risk
      ↓
Evidence
```

---

# 34. Implementation Milestones

## Milestone 1 — Foundation

- repository audit
- backend cleanup
- frontend cleanup
- environment configuration
- market API through Flask

## Milestone 2 — Data

- market ingestion
- news ingestion
- database
- ticker/entity mapping

## Milestone 3 — FinBERT

- production model loading
- news analysis
- sentiment storage
- sentiment history

## Milestone 4 — Fingerprinting

- feature engineering
- rolling baseline
- robust Z-score
- fingerprint visualization

## Milestone 5 — Anomaly Detection

- Isolation Forest
- LOF
- change points
- LSTM Autoencoder
- ensemble

## Milestone 6 — Correlation

- timestamp alignment
- ticker/entity matching
- semantic similarity
- event classification

## Milestone 7 — Risk & Evidence

- risk score
- evidence chain
- explanations
- SHAP

## Milestone 8 — Evaluation

- benchmark dataset
- known-event testing
- synthetic anomalies
- model comparison
- ablation study

## Milestone 9 — Production Demo

- dashboard
- API integration
- error handling
- performance testing
- Docker

## Milestone 10 — Documentation

- architecture
- methodology
- experiments
- results
- limitations
- reproducibility
- README
- viva demonstration

---

# 35. Final Demonstration Scenario

The final viva/demo should show one complete event:

```text
1. Select an asset
        ↓
2. Load market history
        ↓
3. Generate behavioural fingerprint
        ↓
4. Detect unusual behaviour
        ↓
5. Retrieve relevant financial news
        ↓
6. Analyse news with FinBERT
        ↓
7. Match ticker/entity
        ↓
8. Align timestamps
        ↓
9. Calculate correlation
        ↓
10. Generate risk signal
        ↓
11. Display evidence chain
```

The examiner should be able to answer:

- What happened?
- Why was it unusual?
- What information was relevant?
- What did the news sentiment indicate?
- How closely were the signals aligned?
- What evidence supports the alert?

---

# 36. Final System Definition

> **Aventra is an AI-driven financial intelligence platform that detects unusual market behaviour, analyses financial news, correlates cross-source signals, and produces explainable evidence for detected events.**

The implementation should demonstrate the complete pipeline rather than isolated AI models.

---

# 37. Critical Engineering Rules

1. Inspect existing code before modifying it.
2. Preserve working functionality.
3. Never hard-code model results.
4. Never fabricate live data.
5. Avoid data leakage.
6. Separate training from inference.
7. Start with explainable baselines.
8. Add deep learning only after baselines work.
9. Do not claim causation from temporal correlation.
10. Do not claim novelty solely from combining existing models.
11. Record experiments and configurations.
12. Keep model versions reproducible.
13. Test every API endpoint.
14. Test failure states.
15. Keep Docker reproducible.
16. Document unresolved limitations.

---

# 38. Final Success Criteria

- [ ] Market data comes through the backend.
- [ ] Financial news can be ingested.
- [ ] FinBERT works through Flask.
- [ ] Sentiment is stored and visualized.
- [ ] Behavioural fingerprints are generated from real data.
- [ ] Isolation Forest works on real features.
- [ ] LOF is evaluated.
- [ ] Change points are detected.
- [ ] LSTM Autoencoder is evaluated.
- [ ] Anomaly models are combined.
- [ ] News and anomalies can be correlated.
- [ ] Entity/ticker matching works.
- [ ] Semantic similarity works.
- [ ] Event categories are assigned.
- [ ] Risk score is generated.
- [ ] Evidence chain is displayed.
- [ ] Explainability is available where applicable.
- [ ] Known events are evaluated.
- [ ] Synthetic anomalies are evaluated.
- [ ] Results are reproducible.
- [ ] Frontend is fully connected to backend.
- [ ] Docker Compose starts the complete system.
- [ ] README contains complete setup instructions.
- [ ] Final demo runs locally without manual code changes.

---

# 39. Final Architecture

```text
                         AVENTRA
                            |
                 +----------+----------+
                 |                     |
                 v                     v
           Market Data            Financial News
                 |                     |
                 v                     v
           Feature Engine           FinBERT
                 |                     |
                 +----------+----------+
                            |
                            v
                 Behavioural Fingerprint
                            |
                            v
                   Anomaly Detection
                            |
                  +---------+---------+
                  |                   |
                  v                   v
             Change Points       Market Signals
                  |                   |
                  +---------+---------+
                            |
                            v
                 Cross-Source Correlation
                            |
                  +---------+---------+
                  |                   |
                  v                   v
             Event Context       Sentiment
                  |                   |
                  +---------+---------+
                            |
                            v
                       Risk Model
                            |
                            v
                     Evidence Chain
                            |
                            v
                    Aventra Dashboard
                            |
                            v
                    Dockerized System
```

## Final Implementation Principle

Build from the bottom up, validate each layer with real data, and only then connect it to the next layer.

The final system should be a reproducible research prototype with a complete working path:

**React → Flask → Data → ML → Correlation → Risk → Evidence → Dashboard → Docker**
