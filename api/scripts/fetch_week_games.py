"""
Fetch games for the next week from the NBA API.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from fetch_todays_games import fetch_todays_games


def fetch_week_games(days: int = 7):
    """Fetch games for the next N days."""
    today = date.today()

    for i in range(days):
        game_date = today + timedelta(days=i)
        print(f"\n{'='*50}")
        fetch_todays_games(game_date)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=7, help="Number of days to fetch")
    args = parser.parse_args()

    fetch_week_games(args.days)
