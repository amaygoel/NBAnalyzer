"""
Fetch NBA games for specified seasons and store them in the database.
"""
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nba_api.stats.endpoints import leaguegamefinder

from nb_analyzer.database import SessionLocal, init_db
from nb_analyzer.models import Game, Team


def parse_game_date(date_str: str) -> datetime:
    """Parse date from NBA API format."""
    return datetime.strptime(date_str, "%Y-%m-%d").date()


def ingest_games(seasons: list[str] = None):
    """
    Fetch NBA games for specified seasons.

    Args:
        seasons: List of seasons in format "2023-24". Defaults to last 3 seasons.
    """
    if seasons is None:
        # Default to last 3 complete seasons plus current
        seasons = ["2022-23", "2023-24", "2024-25"]

    init_db()
    db = SessionLocal()

    try:
        # Get team ID mapping
        teams = {t.id: t for t in db.query(Team).all()}
        team_ids = list(teams.keys())

        if not team_ids:
            print("No teams in database. Run ingest_teams.py first.")
            return

        print(f"Fetching games for seasons: {seasons}")

        for season in seasons:
            print(f"\nProcessing season {season}...")

            # Fetch games using league game finder
            # We query by one team to get all games, then deduplicate
            game_finder = leaguegamefinder.LeagueGameFinder(
                season_nullable=season,
                league_id_nullable="00",  # NBA
                season_type_nullable="Regular Season",
            )

            games_df = game_finder.get_data_frames()[0]

            if games_df.empty:
                print(f"  No games found for {season}")
                continue

            print(f"  Found {len(games_df)} game records")

            # Process games - each game appears twice (once per team)
            # Group by GAME_ID to deduplicate
            processed_game_ids = set()
            games_added = 0

            for game_id in games_df["GAME_ID"].unique():
                if game_id in processed_game_ids:
                    continue

                # Check if game already exists
                existing = db.query(Game).filter(Game.id == int(game_id)).first()
                if existing:
                    processed_game_ids.add(game_id)
                    continue

                game_rows = games_df[games_df["GAME_ID"] == game_id]
                if len(game_rows) < 2:
                    continue  # Need both teams

                # Identify home and away teams
                home_row = game_rows[game_rows["MATCHUP"].str.contains("vs.")].iloc[0] if not game_rows[game_rows["MATCHUP"].str.contains("vs.")].empty else None
                away_row = game_rows[game_rows["MATCHUP"].str.contains("@")].iloc[0] if not game_rows[game_rows["MATCHUP"].str.contains("@")].empty else None

                if home_row is None or away_row is None:
                    continue

                game = Game(
                    id=int(game_id),
                    date=parse_game_date(home_row["GAME_DATE"]),
                    season=season,
                    home_team_id=int(home_row["TEAM_ID"]),
                    away_team_id=int(away_row["TEAM_ID"]),
                    home_score=int(home_row["PTS"]) if home_row["PTS"] else None,
                    away_score=int(away_row["PTS"]) if away_row["PTS"] else None,
                    is_completed=True,  # Historical games are completed
                )
                db.add(game)
                games_added += 1
                processed_game_ids.add(game_id)

            db.commit()
            print(f"  Added {games_added} new games for {season}")
            time.sleep(1)  # Rate limiting

        # Calculate rest days and back-to-back status
        print("\nCalculating rest days and back-to-back status...")
        calculate_rest_days(db)
        db.commit()

        total_games = db.query(Game).count()
        print(f"\nTotal games in database: {total_games}")

    except Exception as e:
        db.rollback()
        print(f"Error ingesting games: {e}")
        raise
    finally:
        db.close()


def calculate_rest_days(db):
    """Calculate rest days and back-to-back status for all games."""
    teams = db.query(Team).all()

    for team in teams:
        # Get all games for this team, ordered by date
        games = (
            db.query(Game)
            .filter((Game.home_team_id == team.id) | (Game.away_team_id == team.id))
            .order_by(Game.date)
            .all()
        )

        prev_game_date = None
        for game in games:
            if prev_game_date:
                rest_days = (game.date - prev_game_date).days - 1  # Subtract 1 to get actual rest days
                is_b2b = rest_days == 0

                if game.home_team_id == team.id:
                    game.home_rest_days = rest_days
                    game.is_home_back_to_back = is_b2b
                else:
                    game.away_rest_days = rest_days
                    game.is_away_back_to_back = is_b2b

            prev_game_date = game.date


if __name__ == "__main__":
    ingest_games()
