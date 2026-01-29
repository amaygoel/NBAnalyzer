# Model Training Guide

Quick reference for training the margin prediction model.

## Training Pipeline

### 1. Build Dataset (if needed)

```bash
cd api
./venv/bin/python scripts/build_training_dataset.py --seasons 2022-23 2023-24 2024-25 2025-26
```

Output: `data/margin_training_data.csv` (4,375 games)

### 2. Train Model

**Basic training:**
```bash
./venv/bin/python scripts/train_margin_model.py
```

**With feature weights:**
```bash
./venv/bin/python scripts/train_margin_model.py --print-coefs
```

**Rebuild data + train:**
```bash
./venv/bin/python scripts/train_margin_model.py --rebuild-data --print-coefs
```

**Custom alpha search:**
```bash
./venv/bin/python scripts/train_margin_model.py --alphas 0.01 0.1 1 10 100 1000
```

## Output Artifacts

After training, two files are saved:

**1. `artifacts/margin_model.pkl`** (1.7KB)
- Trained sklearn Pipeline: StandardScaler + Ridge
- Load with: `joblib.load('margin_model.pkl')`

**2. `artifacts/margin_model_metadata.json`**
- Feature columns used
- Best alpha hyperparameter
- Train/val/test metrics
- Training timestamp
- Seasons used for each split

## Model Performance

**Current model (α=0.1, 11 features):**

| Split | Games | MAE (pts) | RMSE (pts) | Winner Accuracy |
|-------|-------|-----------|------------|-----------------|
| Train | 2,460 | 10.75     | 13.71      | 63.6%           |
| Val   | 1,225 | 11.19     | 14.33      | 66.7%           |
| Test  | 690   | 11.41     | 14.44      | 61.0%           |

**Feature Importance (standardized coefficients):**

| Rank | Feature | Coefficient | Interpretation |
|------|---------|-------------|----------------|
| 1 | last10_margin_diff | +1.58 | Recent form differential is strongest predictor |
| 2 | home_home_margin_to_date | +1.28 | Home team's home performance matters |
| 3 | away_last10_margin | -1.23 | Away team's recent form (opposing effect) |
| 4 | away_b2b | +1.11 | Away team tired on B2B (helps home) |
| 5 | home_last10_margin | +1.01 | Home team's recent form |
| 6 | away_away_margin_to_date | -0.95 | Away team's away performance (opposing) |
| 7 | home_b2b | -0.70 | Home team tired on B2B (hurts home) |

*Intercept: +2.32 (baseline home court advantage)*

## Evaluation Metrics Explained

**MAE (Mean Absolute Error):**
- Average prediction error in points
- Lower is better
- 11.4 pts = predictions off by ~1.5 possessions on average

**RMSE (Root Mean Squared Error):**
- Penalizes large errors more than MAE
- 14.4 pts = includes some bigger misses

**Winner Direction Accuracy:**
- % of games where predicted winner matches actual winner
- 61-67% across splits
- Random guessing = 50%, perfect = 100%
- This is the most important metric for betting

## Data Splits

**Train (2,460 games):**
- Seasons: 2022-23, 2023-24
- Used for model training

**Validation (1,225 games):**
- Season: 2024-25
- Used for alpha hyperparameter selection

**Test (690 games):**
- Season: 2025-26 (in progress)
- Held-out evaluation only

## Model Details

**Algorithm:** Ridge Regression (L2 regularization)
- Linear model with regularization to prevent overfitting
- Interpretable coefficients
- Fast inference (<1ms per prediction)

**Preprocessing:** StandardScaler
- Centers features to mean=0, std=1
- Ensures all features on same scale

**Hyperparameter:** α (alpha) = 0.1
- Controls regularization strength
- Selected via grid search on validation set
- Lower α = less regularization (best for this problem)

## Retraining

Model should be retrained when:
1. New season data becomes available
2. Significant data accumulates (e.g., every month)
3. Performance degrades on recent games

Simply re-run:
```bash
./venv/bin/python scripts/train_margin_model.py --rebuild-data --print-coefs
```

This will:
1. Rebuild dataset with latest completed games
2. Retrain model with updated data
3. Overwrite artifacts with new version
4. Print updated metrics

## Using the Model

**Load trained model:**
```python
import joblib
import json

# Load model
pipeline = joblib.load('src/nb_analyzer/ml/artifacts/margin_model.pkl')

# Load metadata
with open('src/nb_analyzer/ml/artifacts/margin_model_metadata.json') as f:
    metadata = json.load(f)

feature_cols = metadata['feature_columns']
```

**Make prediction:**
```python
import pandas as pd

# Prepare features for a game
features = pd.DataFrame([{
    'home_win_pct_to_date': 0.65,
    'away_win_pct_to_date': 0.45,
    'win_pct_diff': 0.20,
    'home_last10_margin': 5.2,
    'away_last10_margin': -3.1,
    'last10_margin_diff': 8.3,
    'home_home_margin_to_date': 6.5,
    'away_away_margin_to_date': -4.2,
    'rest_diff': 1,
    'home_b2b': 0,
    'away_b2b': 0,
}])

# Predict margin
predicted_margin = pipeline.predict(features)[0]
print(f"Predicted margin: {predicted_margin:.1f} points")
# Positive = home team favored
# Negative = away team favored
```

## Next Steps

1. ✅ Dataset builder implemented
2. ✅ Training pipeline implemented
3. ⏳ **TODO:** Integrate into `recommendations.py`
4. ⏳ **TODO:** Create bet selection logic (margin → moneyline/spread/total)
5. ⏳ **TODO:** Test on live games
