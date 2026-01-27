"""
Backfill game scores for the 2025-26 season using LeagueGameFinder.
This endpoint has historical data that ScoreboardV2 doesn't provide.

IMPORTANT: This script only backfills through YESTERDAY to avoid marking
today's potentially live games as completed. Today's games should be handled
by the regular fetch_todays_games.py script which properly checks game status.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nba_api.stats.endpoints import leaguegamefinder
from nb_analyzer.database import SessionLocal, init_db
from nb_analyzer.models import Game


def backfill_scores_batch(start_date: date, end_date: date):
    """Backfill scores for a date range using LeagueGameFinder."""
    print(f"Fetching games from {start_date} to {end_date}...")

    # LeagueGameFinder returns all games in the range
    games = leaguegamefinder.LeagueGameFinder(
        season_nullable='2025-26',
        season_type_nullable='Regular Season',
        date_from_nullable=start_date.strftime('%m/%d/%Y'),
        date_to_nullable=end_date.strftime('%m/%d/%Y')
    )

    df = games.get_data_frames()[0]
    print(f"Found {len(df)} team-game records ({len(df)//2} games)")

    if df.empty:
        return 0

    init_db()
    db = SessionLocal()

    updated = 0

    # Group by game_id to process each game once
    game_ids = df['GAME_ID'].unique()

    for game_id_str in game_ids:
        # Convert to int (remove leading 00)
        game_id = int(game_id_str)

        # Get both team records for this game
        game_records = df[df['GAME_ID'] == game_id_str]

        if len(game_records) < 2:
            print(f"  Skipping {game_id_str}: only {len(game_records)} team record(s)")
            continue

        # Find home and away teams
        home_records = game_records[game_records['MATCHUP'].str.contains('vs.', na=False)]
        away_records = game_records[game_records['MATCHUP'].str.contains('@', na=False)]

        if home_records.empty or away_records.empty:
            print(f"  Skipping {game_id_str}: couldn't identify home/away")
            continue

        home_record = home_records.iloc[0]
        away_record = away_records.iloc[0]

        home_score = int(home_record['PTS'])
        away_score = int(away_record['PTS'])

        # Check if game is actually completed (W/L means final)
        # Games in progress won't have W/L designation
        is_final = home_record['WL'] in ['W', 'L'] and away_record['WL'] in ['W', 'L']

        # Update in database
        existing = db.query(Game).filter(Game.id == game_id).first()

        if existing:
            # Update scores regardless, but only mark completed if actually final
            existing.home_score = home_score
            existing.away_score = away_score
            if is_final and not existing.is_completed:
                existing.is_completed = True
                updated += 1
            elif not is_final:
                # Make sure live games aren't marked completed
                existing.is_completed = False

    db.commit()
    db.close()

    print(f"Updated {updated} games")
    return updated


def backfill_season():
    """Backfill all games from season start to yesterday (not today's live games)."""
    # 2025-26 season started October 22, 2025
    start_date = date(2025, 10, 22)
    # Stop at yesterday to avoid marking today's live games as completed
    end_date = date.today() - timedelta(days=1)

    print(f"Backfilling scores from {start_date} to {end_date}\n")

    total_updated = 0

    # Process in monthly batches to avoid API rate limits
    current = start_date

    while current <= end_date:
        # Calculate end of current month or end_date, whichever is earlier
        if current.month == 12:
            next_month = date(current.year + 1, 1, 1)
        else:
            next_month = date(current.year, current.month + 1, 1)

        batch_end = min(next_month - timedelta(days=1), end_date)

        try:
            updated = backfill_scores_batch(current, batch_end)
            total_updated += updated
        except Exception as e:
            print(f"Error processing {current} to {batch_end}: {e}")

        # Move to next month
        current = next_month

        # Small delay between batches
        if current <= end_date:
            import time
            time.sleep(1)

    print(f"\n✅ Backfill complete! Updated {total_updated} games total")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", "-y", action="store_true", help="Skip confirmation")
    args = parser.parse_args()

    if not args.yes:
        confirm = input("This will backfill all game scores for the 2025-26 season. Continue? (y/n): ")
        if confirm.lower() != 'y':
            print("Cancelled")
            sys.exit(0)

    backfill_season()
