"""
Fetch player box scores for all games and store them in the database.
"""
import sys
import time
import warnings
from pathlib import Path
import pandas as pd

# Suppress deprecation warnings from nba_api (V2 still works for historical data)
warnings.filterwarnings("ignore", category=DeprecationWarning)

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nba_api.stats.endpoints import boxscoretraditionalv2

from nb_analyzer.database import SessionLocal, init_db
from nb_analyzer.models import Game, Player, PlayerGameStats


def parse_minutes(min_str: str | None) -> float | None:
    """Parse minutes from format like '32:45' to decimal."""
    if not min_str or min_str == "" or pd.isna(min_str):
        return None
    try:
        if ":" in str(min_str):
            parts = str(min_str).split(":")
            return float(parts[0]) + float(parts[1]) / 60
        return float(min_str)
    except (ValueError, TypeError):
        return None


def safe_int(value) -> int | None:
    """Safely convert value to int, handling NaN and None."""
    if value is None or pd.isna(value):
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def ingest_player_stats(season: str = None, batch_size: int = 50):
    """
    Fetch player box scores for all games in the database.

    Args:
        season: Optional season filter (e.g., "2023-24")
        batch_size: Number of games to process before committing
    """
    init_db()
    db = SessionLocal()

    try:
        # Get games that need stats
        query = db.query(Game).filter(Game.is_completed == True)
        if season:
            query = query.filter(Game.season == season)

        games = query.order_by(Game.date).all()
        print(f"Processing {len(games)} games")

        # Get all player IDs in database
        player_ids = {p.id for p in db.query(Player).all()}

        # Track which games already have stats
        games_with_stats = {
            g[0] for g in db.query(PlayerGameStats.game_id).distinct().all()
        }

        games_to_process = [g for g in games if g.id not in games_with_stats]
        print(f"  {len(games_to_process)} games need stats")

        if not games_to_process:
            print("All games already have player stats.")
            return

        stats_added = 0
        players_added = 0

        for i, game in enumerate(games_to_process):
            try:
                # Fetch box score
                box_score = boxscoretraditionalv2.BoxScoreTraditionalV2(game_id=str(game.id).zfill(10))
                player_stats_df = box_score.get_data_frames()[0]

                if player_stats_df.empty:
                    print(f"  [{i+1}/{len(games_to_process)}] No stats for game {game.id}")
                    continue

                for _, row in player_stats_df.iterrows():
                    player_id = safe_int(row["PLAYER_ID"])
                    if not player_id:
                        continue

                    # Add player if not exists
                    if player_id not in player_ids:
                        player = Player(
                            id=player_id,
                            name=row["PLAYER_NAME"],
                            team_id=safe_int(row["TEAM_ID"]),
                            is_active=False,  # Historical player
                        )
                        db.add(player)
                        player_ids.add(player_id)
                        players_added += 1

                    # Check if stats already exist
                    existing = (
                        db.query(PlayerGameStats)
                        .filter(
                            PlayerGameStats.player_id == player_id,
                            PlayerGameStats.game_id == game.id,
                        )
                        .first()
                    )
                    if existing:
                        continue

                    stat = PlayerGameStats(
                        player_id=player_id,
                        game_id=game.id,
                        team_id=safe_int(row["TEAM_ID"]),
                        minutes=parse_minutes(row.get("MIN")),
                        points=safe_int(row.get("PTS")),
                        rebounds=safe_int(row.get("REB")),
                        offensive_rebounds=safe_int(row.get("OREB")),
                        defensive_rebounds=safe_int(row.get("DREB")),
                        assists=safe_int(row.get("AST")),
                        steals=safe_int(row.get("STL")),
                        blocks=safe_int(row.get("BLK")),
                        turnovers=safe_int(row.get("TO")),
                        personal_fouls=safe_int(row.get("PF")),
                        fg_made=safe_int(row.get("FGM")),
                        fg_attempted=safe_int(row.get("FGA")),
                        three_made=safe_int(row.get("FG3M")),
                        three_attempted=safe_int(row.get("FG3A")),
                        ft_made=safe_int(row.get("FTM")),
                        ft_attempted=safe_int(row.get("FTA")),
                        plus_minus=safe_int(row.get("PLUS_MINUS")),
                        started=row.get("START_POSITION", "") != "",
                    )
                    db.add(stat)
                    stats_added += 1

                print(f"  [{i+1}/{len(games_to_process)}] Processed game {game.id} ({game.date})")

                # Commit in batches
                if (i + 1) % batch_size == 0:
                    db.commit()
                    print(f"  Committed batch ({i+1} games, {stats_added} stats)")

                # Rate limiting - be gentle with NBA API
                time.sleep(0.6)

            except Exception as e:
                print(f"  Error processing game {game.id}: {e}")
                continue

        db.commit()
        print(f"\nSuccessfully added {stats_added} player stat records")
        print(f"Added {players_added} new players")

    except Exception as e:
        db.rollback()
        print(f"Error ingesting player stats: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=str, help="Season to process (e.g., 2023-24)")
    args = parser.parse_args()

    ingest_player_stats(season=args.season)
