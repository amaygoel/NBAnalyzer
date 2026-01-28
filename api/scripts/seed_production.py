"""
Lightweight production database seeding.
Seeds teams and fetches current games + odds.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingest_teams import ingest_teams
from fetch_todays_games import fetch_todays_games


def seed_production():
    """Seed production database with teams and current games."""
    print("=" * 60)
    print("PRODUCTION DATABASE SEEDING")
    print("=" * 60)

    print("\n[1/2] Ingesting teams...")
    print("-" * 40)
    ingest_teams()

    print("\n[2/2] Fetching games for next 14 days...")
    print("-" * 40)
    for days_ahead in range(14):
        game_date = date.today() + timedelta(days=days_ahead)
        try:
            fetch_todays_games(game_date)
        except Exception as e:
            print(f"  Error fetching {game_date}: {e}")
            continue

    print("\n" + "=" * 60)
    print("✅ PRODUCTION SEEDING COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Run fetch_odds.py to populate betting lines")
    print("2. Run backfill_scores.py to populate historical scores")


if __name__ == "__main__":
    seed_production()
