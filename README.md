# Flipkart GRiD 8.0 — Phase 1 Cart Abandonment Prediction

A standalone real-time prediction pipeline that converts live React session
signals into an XGBoost abandonment probability, confidence margin, and exact
SHAP feature attributions. Natural-language reasoning and intervention selection
are intentionally deferred to Phase 2.

## Architecture

```text
React SessionTracker (14 exact features)
        ↓ POST /api/predict-abandonment
FastAPI validation and inference
        ↓
XGBoost probability + SHAP TreeExplainer
        ↓
Probability, confidence, top 3 positive drivers, all feature impacts
```

## Project structure

```text
ml/
  generate_dataset.py
  train_model.py
  data/cart_abandonment_dataset.csv
  artifacts/model.joblib
  artifacts/explainer.joblib
  artifacts/feature_names.json
backend/
  main.py
Flipkart-grid-8.0/src/
  lib/api.ts
  lib/events.ts
  context/SessionContext.tsx
  context/TrackerContext.tsx
```

## Install and train

```sh
python -m pip install -r requirements.txt
python ml/generate_dataset.py
python ml/train_model.py
```

The generator creates 15,000 probabilistically labelled sessions with a target
abandonment rate near 65%. Labels include substantial noise and non-linear
interactions; they are not deterministic copies of feature thresholds.

## Run

Backend:

```sh
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

Frontend:

```sh
npm --prefix Flipkart-grid-8.0 run dev -- --host 0.0.0.0
```

- Frontend: `http://localhost:5173`
- API health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`

## API

`POST /api/predict-abandonment` accepts the exact 14-feature vector documented
in `ml/generate_dataset.py`. It returns:

- `abandonment_probability`: XGBoost probability from 0 to 1
- `confidence_score`: `abs(probability - 0.5) * 2`
- `top_contributing_features`: up to three highest positive SHAP impacts
- `feature_impacts`: SHAP impact for every model feature
- `status`: `success`

Positive SHAP values push the verdict toward abandonment. Negative values push
it toward conversion. Tree SHAP values are additive in the model's raw log-odds
space, not percentage-point changes.

## Validate

```sh
python -m unittest discover -s tests -v
npm --prefix Flipkart-grid-8.0 run build
```

Current synthetic holdout benchmark is recorded in `ml/artifacts/metrics.json`.
Synthetic metrics validate the pipeline only and must not be represented as
production performance.
