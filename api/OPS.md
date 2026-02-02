# Production Operations Guide

## Overview

This system keeps the NBA Analyzer database current with the latest games, scores, and betting odds. The ML model does **NOT** need daily retraining because:

1. **Predictions are based on historical patterns** - The model learned from 4,375 completed games spanning multiple seasons
2. **New games enrich future training** - Completed games improve the *next* model version, not today's predictions
3. **Retraining is expensive** - Weekly/bi-weekly retraining captures enough signal without overhead
4. **Odds update independently** - Fresh betting lines flow through the existing model naturally

## What Needs Daily Updates

### 1. **Upcoming Games Schedule**
- **Why:** Ensures the app shows games 7-14 days out
- **Frequency:** Once per day (morning)
- **Script:** `fetch_upcoming_games.py`

### 2. **Betting Odds**
- **Why:** Odds shift frequently; ML predictions need current lines to calculate value
- **Frequency:** 4-6 times per day during business hours
- **Script:** `fetch_odds.py`
- **Note:** Uses The Odds API (check your rate limit)

### 3. **Game Scores**
- **Why:** Mark completed games, show live scores, update standings
- **Frequency:** Every 20 minutes during game hours (6pm-1am ET)
- **Script:** `fetch_todays_games.py`

## Operations Runner

Use `scripts/run_ops.py` to orchestrate updates:

```bash
# From api/ directory:

# Morning: fetch upcoming games + odds
./venv/bin/python scripts/run_ops.py --mode daily

# Frequent: refresh odds only
./venv/bin/python scripts/run_ops.py --mode odds

# Evening: update scores for live/completed games
./venv/bin/python scripts/run_ops.py --mode scores

# Full update (all operations)
./venv/bin/python scripts/run_ops.py --mode all

# Custom days (if needed)
./venv/bin/python scripts/run_ops.py --mode daily --days 7
```

**Exit codes:**
- `0` = All operations successful
- `1` = One or more operations failed (check logs)

## Recommended Cron Schedule

Assumes server timezone: **America/Chicago** (adjust `TZ` if different)

```bash
# Edit crontab
crontab -e
```

### Minimal Schedule (Recommended)

```cron
# Set timezone
TZ=America/Chicago

# Define project path
NBA_DIR=/path/to/NBAnalyzer/api
PYTHON=$NBA_DIR/venv/bin/python

# Morning: fetch upcoming games + odds (5am CT)
0 5 * * * cd $NBA_DIR && $PYTHON scripts/run_ops.py --mode daily >> /var/log/nba-ops-daily.log 2>&1

# Afternoon odds refresh (8am, 2pm, 5pm CT)
0 8,14,17 * * * cd $NBA_DIR && $PYTHON scripts/run_ops.py --mode odds >> /var/log/nba-ops-odds.log 2>&1

# Evening: update scores every 20 min from 6pm-1am CT (during game hours)
*/20 18-23 * * * cd $NBA_DIR && $PYTHON scripts/run_ops.py --mode scores >> /var/log/nba-ops-scores.log 2>&1
0,20,40 0 * * * cd $NBA_DIR && $PYTHON scripts/run_ops.py --mode scores >> /var/log/nba-ops-scores.log 2>&1
```

### Alternative: Frequent Odds Updates

If you have a higher API rate limit:

```cron
# Odds every 2 hours during business hours (8am-10pm CT)
0 8-22/2 * * * cd $NBA_DIR && $PYTHON scripts/run_ops.py --mode odds >> /var/log/nba-ops-odds.log 2>&1
```

### Copy-Paste Ready (Update paths first!)

```bash
# Replace /path/to/NBAnalyzer with your actual path
# Then add to crontab

TZ=America/Chicago
NBA_DIR=/Users/amaygoel/Desktop/Projects/NBAnalyzer/api
PYTHON=$NBA_DIR/venv/bin/python

# 5am: Daily updates
0 5 * * * cd $NBA_DIR && $PYTHON scripts/run_ops.py --mode daily >> /var/log/nba-ops-daily.log 2>&1

# 8am, 2pm, 5pm: Odds refresh
0 8,14,17 * * * cd $NBA_DIR && $PYTHON scripts/run_ops.py --mode odds >> /var/log/nba-ops-odds.log 2>&1

# 6pm-1am every 20 min: Scores
*/20 18-23 * * * cd $NBA_DIR && $PYTHON scripts/run_ops.py --mode scores >> /var/log/nba-ops-scores.log 2>&1
0,20,40 0 * * * cd $NBA_DIR && $PYTHON scripts/run_ops.py --mode scores >> /var/log/nba-ops-scores.log 2>&1
```

## Optional: Weekly Model Retraining

**When:** Retrain weekly (Sunday 3am) to incorporate the past week's completed games

**Why Optional:** The model already has 4,375 games of training data. Weekly retraining keeps it fresh but isn't critical for short-term operation.

```cron
# Sunday 3am CT: Retrain ML model (OPTIONAL - computationally expensive)
0 3 * * 0 cd $NBA_DIR && $PYTHON scripts/train_margin_model.py >> /var/log/nba-ops-retrain.log 2>&1
```

**Retraining takes:** ~5-10 minutes depending on hardware

## Monitoring & Logs

### Check if cron is running:
```bash
# View cron logs (Linux)
grep CRON /var/log/syslog | tail -20

# View cron logs (macOS)
log show --predicate 'process == "cron"' --last 1h

# Check our app logs
tail -f /var/log/nba-ops-daily.log
tail -f /var/log/nba-ops-odds.log
tail -f /var/log/nba-ops-scores.log
```

### Test manually:
```bash
cd /path/to/NBAnalyzer/api

# Run and watch output
./venv/bin/python scripts/run_ops.py --mode daily
echo "Exit code: $?"  # Should be 0 on success
```

### Common Issues:

**Problem:** "No module named 'nb_analyzer'"
**Solution:** Make sure `PYTHONPATH` includes the `src/` directory, or run from the `api/` directory

**Problem:** Cron not finding venv Python
**Solution:** Use absolute paths in crontab (as shown above)

**Problem:** API rate limit exceeded (odds)
**Solution:** Reduce odds refresh frequency in cron schedule

## Environment Variables

Ensure `.env` file exists in `api/` directory:

```bash
# api/.env
ODDS_API_KEY=your_key_here
DATABASE_URL=sqlite:///nb_analyzer.db  # or PostgreSQL in production
```

## Database Backup (Recommended)

Add a daily backup before morning updates:

```cron
# 4:30am: Backup database before updates
30 4 * * * cd $NBA_DIR && cp nb_analyzer.db nb_analyzer.db.backup-$(date +\%Y\%m\%d) >> /var/log/nba-ops-backup.log 2>&1

# Weekly cleanup: keep only last 7 backups
0 4 * * 0 cd $NBA_DIR && ls -t nb_analyzer.db.backup-* | tail -n +8 | xargs rm -f
```

## Verifying Everything Works

After setting up cron:

1. **Wait 24 hours** for first full cycle
2. **Check logs** for errors:
   ```bash
   grep ERROR /var/log/nba-ops-*.log
   ```
3. **Verify in app:**
   - Home page shows today's games with odds
   - Game scores update during live games
   - Upcoming games appear 7+ days out
4. **Database checks:**
   ```bash
   cd api
   ./venv/bin/python -c "
   from src.nb_analyzer.database import SessionLocal
   from src.nb_analyzer.models import Game, GameOdds
   db = SessionLocal()
   games = db.query(Game).count()
   odds = db.query(GameOdds).count()
   print(f'Games: {games}, Odds records: {odds}')
   "
   ```

## Production Deployment (Render/Heroku/etc)

Instead of cron, use platform schedulers:

**Render:**
- Add "Cron Jobs" in dashboard
- Set schedule: `0 5 * * *`
- Command: `python scripts/run_ops.py --mode daily`

**Heroku:**
- Use Heroku Scheduler addon
- Add jobs matching the cron schedule above

**Railway/Fly.io:**
- Similar scheduler add-ons available

## Summary

**Minimum viable automation:**
1. Morning update (daily + odds)
2. Afternoon odds refresh (2-3x)
3. Evening score updates (every 20 min during games)

**This keeps ML predictions current** because:
- Fresh odds → accurate value calculations
- New completed games → better training data for *next* model version
- Up-to-date schedule → users see all upcoming games

**No daily retraining needed** because the model's predictive power comes from 3+ years of historical patterns, not yesterday's games.
