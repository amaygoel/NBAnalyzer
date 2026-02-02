# Confidence Tier System

The bet selector now returns a recommendation for every game with odds, classified into confidence tiers.

## Confidence Tier Rules

Defined as constants in `bet_selector.py` (tunable):

```python
# HIGH tier
CONFIDENCE_HIGH_MIN_EV = 0.06    # 6% expected value
CONFIDENCE_HIGH_MIN_PROB = 0.60  # 60% win probability

# MEDIUM tier
CONFIDENCE_MEDIUM_MIN_EV = 0.03  # 3% expected value
CONFIDENCE_MEDIUM_MIN_PROB = 0.57  # 57% win probability

# LOW tier
CONFIDENCE_LOW_MIN_EV = 0.00     # 0% expected value (break-even)
CONFIDENCE_LOW_MIN_PROB = 0.52   # 52% win probability
```

**Tier Assignment:**
- 🔥 **HIGH**: EV ≥ 6% AND Prob ≥ 60%
- ✓ **MEDIUM**: EV ≥ 3% AND Prob ≥ 57%
- ~ **LOW**: EV ≥ 0% AND Prob ≥ 52%
- ✗ **NO_BET**: Below LOW thresholds
- — **NO_ODDS**: No market odds available

## Behavior Changes

### Old Behavior (Milestone 4)
- Only returned recommendations passing guardrails (min EV 2%, min prob 55%)
- Games not meeting thresholds had no recommendation

### New Behavior (Updated)
- **Always** returns a recommendation when odds exist
- Best candidate among 4 options (home/away ML + home/away spread)
- Classified into confidence tiers
- Product can show **one card per game**

## Guardrails

Still enforced during candidate evaluation:
- **Max spread 14 pts**: Spreads larger than 14 pts are excluded from candidates
- If `abs(spread) > 14`, only moneyline candidates are evaluated
- If no odds exist at all, returns `NO_ODDS`

## Usage

### Show All Games

```bash
./venv/bin/python scripts/pick_bets.py --days 3
```

Shows every upcoming game with:
- Predicted margin
- Market lines
- Best lean (always present if odds exist)
- Confidence tier emoji

### Show Only Actionable Bets

```bash
./venv/bin/python scripts/pick_bets.py --days 3 --only-bets
```

Filters to show only **HIGH** and **MEDIUM** confidence bets.

### Debug Mode

```bash
./venv/bin/python scripts/pick_bets.py --days 3 --debug
```

Shows full candidate table (4 EVs) for first 5 games.

## Example Output

### All Games View

```
──────────────────────────────────────────────────────────────────────────────────────────
📅 Thursday, January 29, 2026
──────────────────────────────────────────────────────────────────────────────────────────

  MIA @ CHI  │  Pred: CHI by 3.7            │  Market: MIA -2.0      │  🔥 HIGH
      Lean: CHI ML               @  +111  │  Prob: 60.3%  │  EV:  27.1%

  SAC @ PHI  │  Pred: PHI by 1.8            │  Market: PHI -11.5     │  ✗ NO_BET
      Lean: SAC ML               @  +410  │  Prob: 44.9%  │  EV: 128.9%

  MIL @ WAS  │  Pred: MIL by 3.8            │  Market: MIL -2.0      │  🔥 HIGH
      Lean: MIL ML               @  -130  │  Prob: 60.3%  │  EV:   6.6%

  HOU @ ATL  │  Pred: ATL by 3.5            │  Market: HOU -4.0      │  ✓ MEDIUM
      Lean: ATL ML               @  +145  │  Prob: 59.7%  │  EV:  46.2%

  CHA @ DAL  │  Pred: DAL by 0.5            │  Market: CHA -4.5      │  ✗ NO_BET
      Lean: DAL ML               @  +146  │  Prob: 51.3%  │  EV:  26.2%

  BKN @ DEN  │  Pred: DEN by 10.7           │  Market: DEN -6.5      │  🔥 HIGH
      Lean: DEN -6.5             @  -110  │  Prob: 61.5%  │  EV:  17.5%

  TOR @ ORL  │  Pred: ORL by 0.5            │  Market: N/A           │  — NO_ODDS
      No odds available
```

### Summary Statistics

```
SUMMARY:
  Total games:           33
  Games with odds:       8

Confidence Breakdown:
  🔥 HIGH:               3 (9.1%)
  ✓  MEDIUM:             1 (3.0%)
  ~  LOW:                0 (0.0%)
  ✗  NO_BET:             4 (12.1%)
  —  NO_ODDS:            25 (75.8%)

Actionable Bets (HIGH + MEDIUM): 4
  By market:             ML: 3, Spread: 1
  By side:               Home: 3, Away: 1
  Avg EV:                24.4%
  Avg Probability:       60.4%
```

### Only Actionable Bets (--only-bets)

```
──────────────────────────────────────────────────────────────────────────────────────────
📅 Thursday, January 29, 2026
──────────────────────────────────────────────────────────────────────────────────────────

  MIA @ CHI  │  Pred: CHI by 3.7            │  Market: MIA -2.0      │  🔥 HIGH
      Lean: CHI ML               @  +111  │  Prob: 60.3%  │  EV:  27.1%

  MIL @ WAS  │  Pred: MIL by 3.8            │  Market: MIL -2.0      │  🔥 HIGH
      Lean: MIL ML               @  -130  │  Prob: 60.3%  │  EV:   6.6%

  HOU @ ATL  │  Pred: ATL by 3.5            │  Market: HOU -4.0      │  ✓ MEDIUM
      Lean: ATL ML               @  +145  │  Prob: 59.7%  │  EV:  46.2%

  BKN @ DEN  │  Pred: DEN by 10.7           │  Market: DEN -6.5      │  🔥 HIGH
      Lean: DEN -6.5             @  -110  │  Prob: 61.5%  │  EV:  17.5%

Showing 4 actionable bets (HIGH/MEDIUM only)
```

## Interpretation

### HIGH Confidence (🔥)
- **Strong edge**: EV ≥ 6%, Prob ≥ 60%
- Model has high conviction
- Market appears mispriced
- **Action**: Consider betting with larger stake

### MEDIUM Confidence (✓)
- **Good edge**: EV ≥ 3%, Prob ≥ 57%
- Model has moderate conviction
- Decent value opportunity
- **Action**: Consider betting with standard stake

### LOW Confidence (~)
- **Marginal edge**: EV ≥ 0%, Prob ≥ 52%
- Model has slight edge
- Borderline value
- **Action**: Pass or minimal stake

### NO_BET (✗)
- **No edge**: Below LOW thresholds
- Model favors this side but odds don't justify bet
- Market is efficient or model is uncertain
- **Action**: Do not bet

### NO_ODDS (—)
- No market available yet
- Cannot make recommendation
- **Action**: Check back later when odds posted

## Example Scenarios

### Scenario 1: High EV but Low Probability (NO_BET)
```
SAC @ PHI  │  Pred: PHI by 1.8  │  ✗ NO_BET
    Lean: SAC ML @ +410  │  Prob: 44.9%  │  EV: 128.9%
```
- Best candidate has huge EV (128.9%) but only 44.9% prob
- Fails probability threshold (need 52%+)
- **Interpretation**: Market thinks SAC has no chance (+410), model gives them small chance (44.9%)
- Model disagrees with market but not enough to recommend longshot

### Scenario 2: High Probability but Low EV (NO_BET)
```
CHA @ DAL  │  Pred: DAL by 0.5  │  ✗ NO_BET
    Lean: DAL ML @ +146  │  Prob: 51.3%  │  EV: 26.2%
```
- Good EV (26.2%) but only 51.3% prob
- Fails probability threshold (need 52%+)
- **Interpretation**: Nearly even game, model slightly favors DAL, decent value but too close to call

### Scenario 3: Both Thresholds Met (HIGH/MEDIUM)
```
MIA @ CHI  │  Pred: CHI by 3.7  │  🔥 HIGH
    Lean: CHI ML @ +111  │  Prob: 60.3%  │  EV: 27.1%
```
- EV: 27.1% (way above 6%)
- Prob: 60.3% (above 60%)
- **Tier: HIGH**
- **Interpretation**: Model strongly favors CHI and odds offer great value

## Product Integration

The recommendation object includes:

```python
@dataclass
class BetRecommendation:
    game: Game                          # Game details
    pred_margin: float                  # Model's predicted margin
    sigma: float                        # Uncertainty (14.4)
    consensus_odds: ConsensusOdds       # Market lines/odds
    best_bet: BetCandidate              # Recommended bet (always present if odds exist)
    all_candidates: list[BetCandidate]  # All 4 candidates evaluated
    confidence_tier: str                # "HIGH", "MEDIUM", "LOW", "NO_BET", "NO_ODDS"
```

**Frontend can:**
1. Show one card per game (always has a recommendation)
2. Filter by confidence tier
3. Display predicted margin vs market line
4. Show EV and probability for each bet
5. Color-code by confidence (green=HIGH, yellow=MEDIUM, gray=LOW/NO_BET)

## Tuning Thresholds

To adjust confidence tier thresholds, edit constants in `bet_selector.py`:

```python
# Make HIGH tier more selective
CONFIDENCE_HIGH_MIN_EV = 0.10    # Raise to 10%
CONFIDENCE_HIGH_MIN_PROB = 0.65  # Raise to 65%

# Make MEDIUM tier broader
CONFIDENCE_MEDIUM_MIN_EV = 0.02  # Lower to 2%
CONFIDENCE_MEDIUM_MIN_PROB = 0.55  # Lower to 55%
```

Then retrain or re-run predictions to see updated tier assignments.
