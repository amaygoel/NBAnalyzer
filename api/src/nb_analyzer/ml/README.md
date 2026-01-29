# Margin Prediction Model

Machine learning pipeline for predicting NBA game margins (home_score - away_score).

## Training Dataset Builder

### Quick Start

Build training dataset from last 3 complete seasons:

```bash
cd api
./venv/bin/python scripts/build_training_dataset.py --sanity-check
```

### Command Options

```bash
# Build with specific seasons
./venv/bin/python scripts/build_training_dataset.py --seasons 2022-23 2023-24 2024-25

# Run sanity checks (recommended first time)
./venv/bin/python scripts/build_training_dataset.py --sanity-check

# Custom output filename
./venv/bin/python scripts/build_training_dataset.py --output my_dataset.csv

# Custom output directory
./venv/bin/python scripts/build_training_dataset.py --output-dir /path/to/dir
```

### Output

Dataset saved to: `api/data/margin_training_data.csv`

**Columns:**

**Identifiers:**
- `game_id` - NBA game ID
- `game_date` - Date of game
- `season` - Season (e.g., "2024-25")
- `home_team_id` - Home team NBA ID
- `away_team_id` - Away team NBA ID

**Target:**
- `y_margin` - Target variable (home_score - away_score)

**Features (no data leakage - only uses games before each game's date):**

*Win Percentages:*
- `home_win_pct_to_date` - Home team's overall win % up to this game
- `away_win_pct_to_date` - Away team's overall win % up to this game
- `win_pct_diff` - home_win_pct - away_win_pct

*Average Margins:*
- `home_avg_margin_to_date` - Home team's average point differential
- `away_avg_margin_to_date` - Away team's average point differential
- `home_last10_margin` - Home team's avg margin over last 10 games
- `away_last10_margin` - Away team's avg margin over last 10 games
- `last10_margin_diff` - home_last10_margin - away_last10_margin

*Home/Away Splits:*
- `home_home_margin_to_date` - Home team's avg margin in home games only
- `away_away_margin_to_date` - Away team's avg margin in away games only

*Rest & Schedule:*
- `home_rest_days` - Days since home team's last game
- `away_rest_days` - Days since away team's last game
- `rest_diff` - home_rest_days - away_rest_days
- `home_b2b` - 1 if home team on back-to-back, 0 otherwise
- `away_b2b` - 1 if away team on back-to-back, 0 otherwise

*Metadata (for debugging):*
- `home_games_to_date` - Number of games home team has played before this game
- `away_games_to_date` - Number of games away team has played before this game

## Data Leakage Prevention

The builder uses an **efficient single-pass algorithm**:

1. Loads ALL completed games for chosen seasons in ONE database query
2. Processes games in chronological order (sorted by date)
3. Maintains in-memory `TeamState` for each team with running statistics
4. For each game:
   - **FIRST**: Extracts features using current team state (no leakage)
   - **THEN**: Updates team state with game result
5. Uses `deque(maxlen=10)` for efficient last-10-games rolling window

**Key guarantee**: Features for game on date D only use games with date < D.

## Sanity Check Output

When run with `--sanity-check`, validates:

✓ No negative games_to_date counts
✓ First games have 0 prior games for new teams
✓ Later games have reasonable prior game counts
✓ y_margin statistics look reasonable (mean ~0-3 for home advantage)
✓ Feature ranges are valid
✓ No missing values in key features

Sample output shows 5 games across time periods with their features.

## Next Steps

1. **Load dataset in Python:**
   ```python
   import pandas as pd
   df = pd.read_csv('api/data/margin_training_data.csv')

   # Split features and target
   feature_cols = [
       'home_win_pct_to_date', 'away_win_pct_to_date', 'win_pct_diff',
       'home_last10_margin', 'away_last10_margin', 'last10_margin_diff',
       'home_home_margin_to_date', 'away_away_margin_to_date',
       'rest_diff', 'home_b2b', 'away_b2b'
   ]
   X = df[feature_cols]
   y = df['y_margin']
   ```

2. **Train model:**
   ```python
   from sklearn.model_selection import train_test_split
   from sklearn.linear_model import Ridge
   # or: from xgboost import XGBRegressor

   X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

   model = Ridge(alpha=1.0)
   model.fit(X_train, y_train)

   # Evaluate
   from sklearn.metrics import mean_absolute_error
   y_pred = model.predict(X_test)
   mae = mean_absolute_error(y_test, y_pred)
   print(f'MAE: {mae:.2f} points')
   ```

3. **Save trained model:**
   ```python
   import joblib
   joblib.dump(model, 'api/src/nb_analyzer/ml/margin_predictor.pkl')
   ```

4. **Integrate into recommendations.py** (next milestone)

## Performance

**Efficiency:** Processes ~4,000 games in <5 seconds using single-pass algorithm.

**Memory:** O(num_teams) - only stores state for 30 teams, not all games.

**No N+1 queries:** Uses ONE database query instead of `get_team_games()` per game.
