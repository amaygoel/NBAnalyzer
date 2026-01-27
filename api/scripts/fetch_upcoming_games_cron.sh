#!/bin/bash
# Cron wrapper for fetching upcoming games

PROJECT_DIR="/Users/amaygoel/Desktop/Projects/NBAnalyzer/api"
LOG_FILE="$PROJECT_DIR/logs/fetch_upcoming_games.log"

cd "$PROJECT_DIR"

echo "===== Fetch Upcoming Games =====" >> "$LOG_FILE"
echo "Run started at $(date)" >> "$LOG_FILE"

# Run the Python script
./venv/bin/python scripts/fetch_upcoming_games.py >> "$LOG_FILE" 2>&1

echo "Run completed at $(date)" >> "$LOG_FILE"
echo "---" >> "$LOG_FILE"
