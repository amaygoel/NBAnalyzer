# Bet Selector

Selects the single best bet per game using margin predictions and expected value calculations.

## Overview

The bet selector:
1. Takes predicted margin from ML model
2. Converts margin to win/cover probabilities using normal distribution
3. Calculates expected value (EV) for 4 bet types: home ML, away ML, home spread, away spread
4. Selects the bet with highest EV that meets guardrails

## Usage

### Command Line

```bash
# Pick best bets for next 3 days
./venv/bin/python scripts/pick_bets.py --days 3

# Show debug info (candidate table for first 5 games)
./venv/bin/python scripts/pick_bets.py --days 3 --debug

# Use custom sigma (default: 14.4 from model RMSE)
./venv/bin/python scripts/pick_bets.py --days 3 --sigma 15.0
```

### Python API

```python
from nb_analyzer.ml.margin_inference import MarginInference
from nb_analyzer.ml.bet_selector import get_consensus_odds, select_best_bet

# Initialize inference
inference = MarginInference(db)
inference.load_model()

# Get a game
game = db.query(Game).filter(...).first()

# Predict margin
pred_margin = inference.predict_margin(game)

# Get consensus odds from bookmakers
consensus_odds = get_consensus_odds(db, game)

# Select best bet
recommendation = select_best_bet(
    game=game,
    pred_margin=pred_margin,
    consensus_odds=consensus_odds,
    min_ev=0.02,      # Minimum 2% expected value
    min_prob=0.55,    # Minimum 55% win probability
    max_spread=14.0   # Skip spreads larger than 14 pts
)

if recommendation.best_bet:
    bet = recommendation.best_bet
    print(f"{bet.market} {bet.side} {bet.line or ''} @ {bet.odds}")
    print(f"Probability: {bet.probability:.1%}")
    print(f"Expected Value: {bet.ev:.1%}")
```

## How It Works

### 1. Probability Calculations

The model predicts margin (home_score - away_score). We assume actual margin follows:
```
actual_margin ~ Normal(pred_margin, sigma=14.4)
```

**Win Probability:**
```python
P(home_win) = CDF(pred_margin / sigma)
```

**Cover Probability:**
```python
# If home_line = -6.5 (home favored by 6.5)
# Home covers if: actual_margin > 6.5
P(home_cover) = 1 - CDF((6.5 - pred_margin) / sigma)
```

### 2. Expected Value

```python
decimal_odds = american_to_decimal(american_odds)
EV = probability * decimal_odds - 1
```

**Example:**
- Prob = 60%
- Odds = +100 (decimal = 2.0)
- EV = 0.60 * 2.0 - 1 = 0.20 = 20%

This means you expect to profit $0.20 per $1 wagered long-term.

### 3. Bet Selection

For each game, evaluate 4 candidates:
1. Home moneyline
2. Away moneyline
3. Home spread
4. Away spread

**Guardrails:**
- EV >= 2% (default)
- Probability >= 55% (default)
- Spread size <= 14 pts (ignore large spreads)

Select the bet with **highest EV** that passes all guardrails.

## Sign Conventions

**Spread Lines:**
- Home -6.5 = home favored by 6.5 (must win by 7+)
- Home +6.5 = home underdog by 6.5 (can lose by 6 and still cover)

**Prediction Interpretation:**
- pred_margin = +10 → model predicts home wins by 10
- pred_margin = -5 → model predicts away wins by 5

**Cover Logic:**
- If pred_margin = +10 and spread = -6.5:
  - Model predicts home wins by 10
  - Home needs to win by 7+ to cover
  - P(home covers) ≈ 60% (good bet on home -6.5)

- If pred_margin = +2 and spread = -6.5:
  - Model predicts home wins by 2
  - Home needs to win by 7+ to cover
  - P(home covers) ≈ 38% (bad bet on home -6.5, good bet on away +6.5)

## Example Output

```
================================================================================
NBA BET RECOMMENDATIONS (Next 3 days)
================================================================================

Found 8 games with odds
Using sigma = 14.4 (model RMSE)
Guardrails: EV >= 2%, Prob >= 55%, Max spread 14 pts

────────────────────────────────────────────────────────────────────────────────
📅 Thursday, January 29, 2026
────────────────────────────────────────────────────────────────────────────────

  SAC @ PHI  │  Pred: PHI by 1.8           │  Market: PHI -11.5     │  ML: -550/+410
         ✓ BET: SAC +11.5            @  -110  │  Prob: 74.9%  │  EV: 42.9%

  BKN @ DEN  │  Pred: DEN by 10.7          │  Market: DEN -6.5      │  ML: -270/+223
         ✓ BET: DEN -6.5             @  -110  │  Prob: 61.5%  │  EV: 17.5%

  MIA @ CHI  │  Pred: CHI by 3.7           │  Market: MIA -2.0      │  ML: +111/-132
         ✓ BET: CHI ML               @  +111  │  Prob: 60.3%  │  EV: 27.1%

================================================================================
Total recommendations: 7/33

SUMMARY:
  Games analyzed:        33
  Recommendations:       7 (21.2%)
  By market:             ML: 3, Spread: 4
  By side:               Home: 5, Away: 2
  Avg EV:                25.5%
  Avg Probability:       63.2%
```

## Key Insights

**SAC @ PHI Example:**
- Model: PHI by 1.8
- Market: PHI -11.5
- **Huge disagreement!**
- Model thinks SAC only loses by ~2
- SAC +11.5 is a great bet (74.9% prob, 42.9% EV)

**BKN @ DEN Example:**
- Model: DEN by 10.7
- Market: DEN -6.5
- Model more bullish on DEN than market
- DEN -6.5 is a good bet (61.5% prob, 17.5% EV)

## Performance Expectations

Based on model metrics:
- MAE: 11.4 points
- RMSE: 14.4 points (sigma)
- Winner Direction Accuracy: 61-67%

The 55% probability threshold ensures we only bet when model has meaningful edge over market (which assumes 50% after removing vig).

## Testing

Run the test suite to verify sign conventions and calculations:

```bash
./venv/bin/python scripts/test_bet_selector.py
```

## Next Steps

1. ✅ Dataset builder
2. ✅ Model training
3. ✅ Inference pipeline
4. ✅ Bet selector
5. ⏳ **TODO:** Integrate into recommendations.py
6. ⏳ **TODO:** Track bet performance over time
7. ⏳ **TODO:** Add bankroll management (Kelly criterion)
