# ML Recommendation Polish Fixes

Backend polish improvements to ML recommendation output for better frontend rendering.

## Changes Made

### Issue 1: NO_ODDS Distinct State

**Problem:** NO_ODDS games mapped to `confidence="low"`, indistinguishable from low-confidence actionable bets.

**Solution:**
- Added `"none"` as a valid confidence value in Recommendation schema
- NO_ODDS now maps to `confidence="none"`
- Updated insight to start with `"ODDS PENDING:"` prefix
- Added machine-readable `{"label": "Status", "value": "NO_ODDS"}` stat

**Before:**
```python
{
    "confidence": "low",
    "insight": "Betting lines not yet posted",
    "supporting_stats": [
        {"label": "Status", "value": "Odds pending"},
        {"label": "Prediction", "value": "ORL by 0.5"}
    ]
}
```

**After:**
```python
{
    "confidence": "none",  # ← DISTINCT from "low"
    "insight": "ODDS PENDING: Model leans ORL by +0.5",
    "supporting_stats": [
        {"label": "Status", "value": "NO_ODDS"},  # ← Machine-readable
        {"label": "Model prediction", "value": "ORL by +0.5"}
    ]
}
```

### Issue 2: Consistent Prediction vs Market Formatting

**Problem:** Inconsistent phrasing and missing sign conventions made insights confusing.

**Solution:**
- Moneyline bets: `"CHI ML @ +116 | Model win prob: 60.3% | Market ML: CHI +116"`
- Spread bets: `"SAC +11.5 @ -108 | Model: PHI by +1.8 | Market spread: PHI -11.5"`
- NO_ODDS: `"ODDS PENDING: Model leans ORL by +0.5"`
- Added explicit `+` sign to positive margins

**Before:**
```
"CHI ML @ +111 | Pred: CHI by 3.7 vs Market: MIA -2.0"
```

**After (Moneyline):**
```
"CHI ML @ +116 | Model win prob: 60.3% | Market ML: CHI +116"
```

**After (Spread):**
```
"SAC +11.5 @ -108 | Model: PHI by +1.8 | Market spread: PHI -11.5"
```

## Files Modified

**Only 1 file changed:** `api/src/nb_analyzer/services/recommendations.py`

**Changes:**
1. Updated `Recommendation` dataclass docstring to include `"none"` confidence
2. Modified `_map_ml_to_api_recommendation()`:
   - NO_ODDS maps to `confidence="none"`
   - Updated insight formatting for all cases
   - Split moneyline vs spread insight formats
3. Updated `_format_margin()` to include `+` sign
4. Updated `_map_confidence_tier()` to handle NO_ODDS → "none"

**Total changes:** ~50 lines modified in existing methods

## Test Results

```bash
./venv/bin/python scripts/test_ml_integration.py --days 1
```

**Output:**
```
SUMMARY
══════════════════════════════════════════════════════════════

Total games tested:    17
Successful:            17
Errors:                0  ← ✓ No errors!

Confidence Breakdown:
  High    : 6
  Medium  : 1
  Low     : 1
  None    : 9  ← ✓ NO_ODDS distinct!

Bet Type Breakdown:
  moneyline   : 3
  spread      : 5
  no_odds     : 9

✅ INTEGRATION TEST COMPLETE
```

## Example Outputs

### 1. HIGH Confidence Moneyline (with odds)

```
Game: MIA @ CHI
Bet Type: moneyline
Subject: CHI
Confidence: high  ← Actionable bet

Insight: CHI ML @ +116 | Model win prob: 60.3% | Market ML: CHI +116

Supporting Stats:
  - Recommendation: CHI ML @ +116
  - Confidence: HIGH
  - Probability: 60.3%
  - Expected Value: 30.1%
  - Model prediction: CHI by +3.7
  - Market spread: MIA -2.5
```

**Key improvements:**
- Clear format: `Bet @ odds | Model win prob: X% | Market ML: odds`
- Model prediction includes explicit `+` sign
- Win probability highlighted for moneyline bets

### 2. HIGH Confidence Spread (with odds)

```
Game: SAC @ PHI
Bet Type: spread
Subject: SAC
Confidence: high  ← Actionable bet

Insight: SAC +11.5 @ -108 | Model: PHI by +1.8 | Market spread: PHI -11.5

Supporting Stats:
  - Recommendation: SAC +11.5 @ -108
  - Confidence: HIGH
  - Probability: 74.9%
  - Expected Value: 44.2%
  - Model prediction: PHI by +1.8
  - Market spread: PHI -11.5
```

**Key improvements:**
- Clear format: `Bet @ odds | Model: prediction | Market spread: line`
- Shows model vs market discrepancy clearly
- Model predicts PHI by only 1.8, but market has PHI -11.5 (huge edge!)

### 3. NO_ODDS Game (no betting lines posted)

```
Game: TOR @ ORL
Bet Type: no_odds
Subject: N/A
Confidence: none  ← Distinct from "low"!

Insight: ODDS PENDING: Model leans ORL by +0.5

Supporting Stats:
  - Status: NO_ODDS  ← Machine-readable
  - Model prediction: ORL by +0.5
```

**Key improvements:**
- `confidence="none"` is distinct from `"low"`
- Insight starts with `"ODDS PENDING:"` prefix
- Status field is machine-readable: `"NO_ODDS"`
- Still shows model prediction for context

## API Contract

### Confidence Values

**Before:**
- `"high"` - High confidence bet
- `"medium"` - Medium confidence bet
- `"low"` - Low confidence bet OR no odds

**After:**
- `"high"` - High confidence bet
- `"medium"` - Medium confidence bet
- `"low"` - Low confidence bet (actionable but barely)
- `"none"` - No odds available (not actionable) ← NEW

**Backward Compatibility:**
- Existing clients that check for `"high"` or `"medium"` will continue working
- Clients that treat unknown confidence as "no bet" will correctly ignore `"none"`
- Recommended frontend handling: `if (confidence === "none") renderPendingOddsCard()`

### Bet Type Values

**All supported:**
- `"moneyline"` - Moneyline bet
- `"spread"` - Spread bet
- `"total"` - Total (over/under) - not yet used
- `"no_odds"` - Odds not posted
- `"no_bet"` - Odds exist but no actionable bet

## Frontend Integration Recommendations

```typescript
// Confidence-based rendering
switch (recommendation.confidence) {
    case "high":
        return <HighConfidenceCard {...recommendation} />
    case "medium":
        return <MediumConfidenceCard {...recommendation} />
    case "low":
        return <LowConfidenceCard {...recommendation} />
    case "none":
        return <PendingOddsCard {...recommendation} />  // ← New distinct card
    default:
        return <NoRecommendationCard />
}

// Parse insight for display
const insight = recommendation.insight
if (insight.startsWith("ODDS PENDING:")) {
    // Show "Odds not yet available" UI
    // But still display model prediction from supporting_stats
}

// Machine-readable status check
const status = recommendation.supporting_stats.find(s => s.label === "Status")?.value
if (status === "NO_ODDS") {
    // Handle pending odds case
}
```

## Benefits

**1. Clear Distinction**
- NO_ODDS games now have `confidence="none"` (distinct from low-confidence bets)
- Frontend can render different UI for pending odds vs. low-confidence bets

**2. Better Formatting**
- Moneyline: Shows win probability (what users care about)
- Spread: Shows model vs market clearly (easy to see edge)
- Consistent use of `+` sign for positive values

**3. Machine-Readable**
- Status field: `"NO_ODDS"`, `"NO_BET"` for programmatic filtering
- Insight prefix: `"ODDS PENDING:"`, `"NO BET:"` for parsing

**4. Backward Compatible**
- Same Recommendation schema
- Same response structure
- Only added new confidence value `"none"`

## Verification

```bash
# Test integration
./venv/bin/python scripts/test_ml_integration.py --days 1

# Should show:
# - 17 games tested successfully
# - 0 errors
# - 9 games with confidence="none" (NO_ODDS)
# - 7 actionable bets (HIGH/MEDIUM/LOW)
```

All tests pass with 0 errors! ✅
