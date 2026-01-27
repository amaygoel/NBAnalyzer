#!/bin/bash
# Automated odds fetching script for cron
# Logs output to a file for debugging

cd /Users/amaygoel/Desktop/Projects/NBAnalyzer/api

# Activate virtual environment
source venv/bin/activate

# Run the fetch script
python scripts/fetch_odds.py >> logs/fetch_odds.log 2>&1

# Add timestamp
echo "Run completed at $(date)" >> logs/fetch_odds.log
echo "---" >> logs/fetch_odds.log
