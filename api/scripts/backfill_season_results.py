"""
Backfill game results for the 2025-26 season.
Fetches all games from season start (Oct 22, 2025) through today.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fetch_todays_games import fetch_todays_games


def backfill_season():
    """Backfill all games from season start to today."""
    # 2025-26 season started October 22, 2025
    start_date = date(2025, 10, 22)
    end_date = date.today()

    print(f"Backfilling games from {start_date} to {end_date}")
    print(f"This will take approximately {(end_date - start_date).days} API calls (about 1-2 minutes with delays)\n")

    current_date = start_date
    days_processed = 0

    while current_date <= end_date:
        print(f"\n=== {current_date} ===")
        try:
            fetch_todays_games(current_date)
            days_processed += 1
        except Exception as e:
            print(f"Error on {current_date}: {e}")

        current_date += timedelta(days=1)

        # Small delay to be respectful to NBA API (0.6s between requests)
        if current_date <= end_date:
            import time
            time.sleep(0.6)

    print(f"\n✅ Backfill complete! Processed {days_processed} days")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    args = parser.parse_args()

    if not args.yes:
        confirm = input("This will backfill ~96 days of games. Continue? (y/n): ")
        if confirm.lower() != 'y':
            print("Cancelled")
            sys.exit(0)

    backfill_season()
