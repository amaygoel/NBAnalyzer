"""
Master script to seed the database with all NBA data.
Run this once to populate the database with historical data.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingest_teams import ingest_teams
from ingest_players import ingest_players
from ingest_games import ingest_games
from ingest_player_stats import ingest_player_stats


def seed_database(seasons: list[str] = None):
    """
    Seed the database with all NBA data.

    Args:
        seasons: List of seasons to fetch (e.g., ["2022-23", "2023-24"])
    """
    if seasons is None:
        seasons = ["2022-23", "2023-24", "2024-25"]

    print("=" * 60)
    print("NBA PREDICTOR - DATABASE SEEDING")
    print("=" * 60)

    print("\n[1/4] Ingesting teams...")
    print("-" * 40)
    ingest_teams()

    print("\n[2/4] Ingesting active players...")
    print("-" * 40)
    ingest_players(active_only=True)

    print("\n[3/4] Ingesting games...")
    print("-" * 40)
    ingest_games(seasons=seasons)

    print("\n[4/4] Ingesting player stats...")
    print("-" * 40)
    print("This may take a while (fetching box scores for each game)...")
    ingest_player_stats()

    print("\n" + "=" * 60)
    print("DATABASE SEEDING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed the NBA Predictor database")
    parser.add_argument(
        "--seasons",
        type=str,
        nargs="+",
        default=["2022-23", "2023-24", "2024-25"],
        help="Seasons to fetch (e.g., 2022-23 2023-24)",
    )
    args = parser.parse_args()

    seed_database(seasons=args.seasons)
