#!/bin/bash
# Daily game result updates for NBAnalyzer
# Updates completed game scores from the NBA API

cd /Users/amaygoel/Desktop/Projects/NBAnalyzer/api

# Activate virtual environment
source venv/bin/activate

# Fetch and update today's games (includes scores for completed games)
python scripts/fetch_todays_games.py >> logs/game_results.log 2>&1

# Also fetch yesterday in case of late finishes
python scripts/fetch_todays_games.py --date "$(date -v-1d +%Y-%m-%d)" >> logs/game_results.log 2>&1

# Add timestamp
echo "Run completed at $(date)" >> logs/game_results.log
echo "---" >> logs/game_results.log
