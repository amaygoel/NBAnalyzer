# macOS Automation with LaunchAgents

## Problem with Cron on macOS
Cron doesn't have proper permissions on modern macOS to execute scripts or write logs. Apple recommends using `launchd` agents instead.

## Active LaunchAgents

### 1. Daily Updates (5 AM)
**File:** `~/Library/LaunchAgents/com.nba-analyzer.daily.plist`
- Fetches upcoming games (next 14 days)
- Fetches betting odds
- Runs once per day at 5:00 AM

### 2. Odds Refresh (4x daily)
**File:** `~/Library/LaunchAgents/com.nba-analyzer.odds.plist`
- Updates betting lines
- Runs at: 8 AM, 2 PM, 5 PM, 10 PM

### 3. Score Updates (Every 20 min)
**File:** `~/Library/LaunchAgents/com.nba-analyzer.scores.plist`
- Updates game scores and results
- Runs continuously every 20 minutes

### 4. Weekly Model Retraining (Sunday 3 AM)
**File:** `~/Library/LaunchAgents/com.nba-analyzer.retrain.plist`
- Retrains XGBoost ML model with all completed games
- Incorporates new game data from the past week
- Takes 5-10 minutes to complete
- Runs every Sunday at 3:00 AM

## Logs
All output is written to:
- `~/logs/nba-analyzer/daily.log`
- `~/logs/nba-analyzer/daily-error.log`
- `~/logs/nba-analyzer/odds.log`
- `~/logs/nba-analyzer/odds-error.log`
- `~/logs/nba-analyzer/scores.log`
- `~/logs/nba-analyzer/scores-error.log`
- `~/logs/nba-analyzer/retrain.log`
- `~/logs/nba-analyzer/retrain-error.log`

## Managing LaunchAgents

### Check Status
```bash
launchctl list | grep nba-analyzer
```

### Manually Trigger Jobs
```bash
# Run daily update now
launchctl start com.nba-analyzer.daily

# Run odds refresh now
launchctl start com.nba-analyzer.odds

# Run score update now
launchctl start com.nba-analyzer.scores

# Run model retraining now (takes 5-10 minutes)
launchctl start com.nba-analyzer.retrain
```

### Stop/Unload Agent
```bash
launchctl unload ~/Library/LaunchAgents/com.nba-analyzer.daily.plist
launchctl unload ~/Library/LaunchAgents/com.nba-analyzer.odds.plist
launchctl unload ~/Library/LaunchAgents/com.nba-analyzer.scores.plist
launchctl unload ~/Library/LaunchAgents/com.nba-analyzer.retrain.plist
```

### Reload After Changes
```bash
# Unload first
launchctl unload ~/Library/LaunchAgents/com.nba-analyzer.*.plist

# Then load again
launchctl load ~/Library/LaunchAgents/com.nba-analyzer.daily.plist
launchctl load ~/Library/LaunchAgents/com.nba-analyzer.odds.plist
launchctl load ~/Library/LaunchAgents/com.nba-analyzer.scores.plist
launchctl load ~/Library/LaunchAgents/com.nba-analyzer.retrain.plist
```

### View Recent Logs
```bash
# Watch live updates
tail -f ~/logs/nba-analyzer/scores.log

# Check today's activity
cat ~/logs/nba-analyzer/daily.log
cat ~/logs/nba-analyzer/odds.log

# Check for errors
tail -50 ~/logs/nba-analyzer/*-error.log
grep -i error ~/logs/nba-analyzer/*.log
```

## Troubleshooting

### Jobs not running?
1. Check if agents are loaded:
   ```bash
   launchctl list | grep nba-analyzer
   ```

2. Check error logs:
   ```bash
   cat ~/logs/nba-analyzer/*-error.log
   ```

3. Manually trigger to test:
   ```bash
   launchctl start com.nba-analyzer.daily
   ```

### Need to disable automation temporarily?
```bash
launchctl unload ~/Library/LaunchAgents/com.nba-analyzer.*.plist
```

### Re-enable automation
```bash
launchctl load ~/Library/LaunchAgents/com.nba-analyzer.daily.plist
launchctl load ~/Library/LaunchAgents/com.nba-analyzer.odds.plist
launchctl load ~/Library/LaunchAgents/com.nba-analyzer.scores.plist
launchctl load ~/Library/LaunchAgents/com.nba-analyzer.retrain.plist
```

## After System Restart
LaunchAgents automatically start after login. No manual intervention needed.
