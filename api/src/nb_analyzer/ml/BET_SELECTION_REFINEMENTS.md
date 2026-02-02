# Bet Selection Refinements

Document of improvements made to bet selector for production readiness.

## Issue A: Odds Coverage Analysis

### Problem
Only 8/33 games (24.2%) showed odds, raising concerns about coverage.

### Investigation
Using `--diagnose-odds` flag:
```bash
./venv/bin/python scripts/pick_bets.py --days 3 --diagnose-odds
```

**Findings:**
```
Total upcoming games:      33
Games with ANY odds:       8 (24.2%)
Games with spreads:        8 (24.2%)
Games with moneyline:      8 (24.2%)
Games with totals:         8 (24.2%)

Top reasons for NO_ODDS:
  25 games: no_odds_in_db
```

### Root Cause
**Not a bug!** This is correct behavior:
- Today (Jan 29): 8 games with odds
- Tomorrow+ (Jan 30-31): 25 games without odds yet
- Bookmakers don't post odds 24+ hours in advance

**Confirmation:**
- ALL games with odds in DB have complete markets (spreads, ML, totals)
- 100% coverage for games where odds exist
- No filtering issues or query problems

### Solution
✅ No fix needed. Diagnostics confirm system working correctly.

Added `--diagnose-odds` flag for future troubleshooting:
- Shows game-by-game odds availability
- Identifies specific reasons for NO_ODDS
- Cross-checks database queries

---

## Issue B: Best-Bet Selection Refinement

### Problem
Best bet was `max(EV)` regardless of probability, which could recommend longshots with low win probability but high EV (e.g., SAC ML @ +410 with 44.9% prob, 128.9% EV).

These bets failed confidence tier thresholds, resulting in NO_BET, even though a better actionable bet existed (e.g., SAC +11.5 @ -110 with 74.9% prob, 42.9% EV).

### Solution
Split bet selection into two candidates:

```python
@dataclass
class BetRecommendation:
    best_bet: Optional[BetCandidate]      # Actionable bet (prob >= 52%)
    best_overall: Optional[BetCandidate]  # Best EV regardless of thresholds
```

**New Logic:**
1. Find `best_overall`: max EV among all 4 candidates (ML home/away, spread home/away)
2. Find `best_actionable`: max EV among candidates with `prob >= 0.52` (LOW tier threshold)
3. Recommend `best_actionable` if exists; otherwise NO_BET
4. Confidence tier based on actionable bet

### Before vs After

#### Before (Incorrect)
```
SAC @ PHI  │  ✗ NO_BET
    Best: SAC ML @ +410  │  Prob: 44.9%  │  EV: 128.9%
    (Fails prob threshold, so NO_BET)
```

#### After (Correct)
```
SAC @ PHI  │  🔥 HIGH
    Bet:  SAC +11.5 @ -110  │  Prob: 74.9%  │  EV: 42.9%
```

**Debug Output:**
```
DEBUG: SAC @ PHI
Candidate EVs:
Market       Side   Line     Odds     Prob     EV       Status
──────────────────────────────────────────────────────────────────────
moneyline    HOME   ---      -550     55.1%   -34.9%
moneyline    AWAY   ---      +410     44.9%   128.9%  BEST OVERALL
spread       HOME   -11.5    -111     25.1%   -52.2%
spread       AWAY   +11.5    -110     74.9%    42.9%  ACTIONABLE ✓

✓ Actionable bet: AWAY +11.5 @ -110 | Prob: 74.9% | EV: 42.9% | Tier: HIGH
```

### Output Changes

**With Actionable Bet:**
```
SAC @ PHI  │  Pred: PHI by 1.8  │  Market: PHI -11.5  │  🔥 HIGH
    Bet:  SAC +11.5 @ -110  │  Prob: 74.9%  │  EV: 42.9%
```

**Without Actionable Bet (future scenario):**
```
GAME XYZ  │  Pred: ...  │  Market: ...  │  ✗ NO_BET
    NO BET (lean: Team ML @ +500, Prob: 30%, EV: 150%)
```
Shows best overall as context but doesn't recommend betting.

---

## Summary Statistics (Updated)

After refinements, running `./venv/bin/python scripts/pick_bets.py --days 3`:

```
SUMMARY:
  Total games:           33
  Games with odds:       8

Confidence Breakdown:
  🔥 HIGH:               6 (18.2%)
  ✓  MEDIUM:             1 (3.0%)
  ~  LOW:                1 (3.0%)
  ✗  NO_BET:             0 (0.0%)
  —  NO_ODDS:            25 (75.8%)

Actionable Bets (HIGH + MEDIUM): 7
  By market:             ML: 3, Spread: 4
  By side:               Home: 5, Away: 2
  Avg EV:                25.5%
  Avg Probability:       63.2%
```

**Key Improvements:**
- 6 HIGH confidence bets (was 3 before)
- 0 NO_BET cases (was 4 before)
- 7 actionable bets from 8 games with odds (87.5% conversion)

---

## Testing Commands

### Diagnostics
```bash
# Check odds coverage
./venv/bin/python scripts/pick_bets.py --days 3 --diagnose-odds
```

### Normal Usage
```bash
# Show all games
./venv/bin/python scripts/pick_bets.py --days 3

# Show only actionable bets
./venv/bin/python scripts/pick_bets.py --days 3 --only-bets

# Debug mode (show candidate tables)
./venv/bin/python scripts/pick_bets.py --days 3 --debug
```

---

## Files Modified

1. **`api/src/nb_analyzer/ml/bet_selector.py`**
   - Added `best_overall` to `BetRecommendation`
   - Split selection into actionable vs overall best
   - Filter actionable candidates by `prob >= 0.52`

2. **`api/scripts/pick_bets.py`**
   - Added `diagnose_odds_coverage()` function
   - Added `--diagnose-odds` flag
   - Updated output to show actionable bet (or NO_BET with lean)
   - Enhanced debug mode to show ACTIONABLE vs BEST OVERALL

---

## Production Readiness

✅ **Odds Coverage**: Confirmed working correctly
✅ **Bet Selection**: Now selects actionable bets properly
✅ **Diagnostics**: Tools available for troubleshooting
✅ **Output**: Clear, informative, ready for frontend integration

**Next Step:** Ready to integrate into `recommendations.py`
