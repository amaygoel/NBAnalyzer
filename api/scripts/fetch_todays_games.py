"""
Fetch today's scheduled games from the NBA API.
"""
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nba_api.stats.endpoints import scoreboardv2

from nb_analyzer.database import SessionLocal, init_db
from nb_analyzer.models import Game, Team


def parse_game_time(game_status_text: str, game_date: date) -> datetime | None:
    """Parse game start time from status text (e.g., '7:30 pm ET') and convert to UTC."""
    if not game_status_text or ('pm' not in game_status_text.lower() and 'am' not in game_status_text.lower()):
        return None

    try:
        # Extract time string (e.g., "7:30 pm ET" or "7:00 pm ET")
        time_str = game_status_text.strip()
        # Remove timezone indicator for parsing
        time_str = time_str.replace(' ET', '').replace(' EST', '').replace(' EDT', '').strip()
        # Parse the time
        game_time = datetime.strptime(time_str, "%I:%M %p")
        # Combine with the game date
        full_datetime = datetime.combine(game_date, game_time.time())
        # Localize to Eastern Time
        et_datetime = full_datetime.replace(tzinfo=ZoneInfo("America/New_York"))
        # Convert to UTC
        utc_datetime = et_datetime.astimezone(ZoneInfo("UTC"))
        # Return as naive UTC datetime for SQLite storage
        return utc_datetime.replace(tzinfo=None)
    except Exception as e:
        # Silently fail - game time is optional
        return None


def fetch_todays_games(game_date: date = None):
    """
    Fetch today's games from the NBA scoreboard.

    Args:
        game_date: Date to fetch games for (defaults to today)
    """
    if game_date is None:
        game_date = date.today()

    init_db()
    db = SessionLocal()

    try:
        # Format date for NBA API (MM/DD/YYYY)
        date_str = game_date.strftime("%m/%d/%Y")
        print(f"Fetching games for {game_date} ({date_str})...")

        scoreboard = scoreboardv2.ScoreboardV2(game_date=date_str)
        games_df = scoreboard.get_data_frames()[0]  # GameHeader

        if games_df.empty:
            print("No games scheduled for this date.")
            return

        print(f"Found {len(games_df)} games")

        # Get team abbreviation to ID mapping
        teams = {t.id: t.abbreviation for t in db.query(Team).all()}

        # Determine current season
        if game_date.month >= 10:
            season = f"{game_date.year}-{str(game_date.year + 1)[2:]}"
        else:
            season = f"{game_date.year - 1}-{str(game_date.year)[2:]}"

        games_added = 0
        games_updated = 0
        seen_game_ids = set()

        for _, row in games_df.iterrows():
            game_id = int(row["GAME_ID"])

            # Skip duplicates in the API response
            if game_id in seen_game_ids:
                continue
            seen_game_ids.add(game_id)

            home_team_id = int(row["HOME_TEAM_ID"])
            away_team_id = int(row["VISITOR_TEAM_ID"])

            # Check game status
            game_status = row.get("GAME_STATUS_ID", 1)
            is_completed = game_status == 3  # 3 = Final

            # Parse game time from status text
            game_status_text = row.get("GAME_STATUS_TEXT", "")
            game_time = parse_game_time(game_status_text, game_date)

            # Get scores if available
            home_score = None
            away_score = None
            if is_completed or game_status == 2:  # 2 = In Progress
                # Scores are in the line score dataframe
                line_score_df = scoreboard.get_data_frames()[1]
                home_line = line_score_df[line_score_df["TEAM_ID"] == home_team_id]
                away_line = line_score_df[line_score_df["TEAM_ID"] == away_team_id]
                if not home_line.empty and home_line["PTS"].notna().values[0]:
                    home_score = int(home_line["PTS"].values[0])
                if not away_line.empty and away_line["PTS"].notna().values[0]:
                    away_score = int(away_line["PTS"].values[0])

            # Check if game exists
            existing = db.query(Game).filter(Game.id == game_id).first()

            if existing:
                # Update if scores changed or time info available
                needs_update = (
                    existing.home_score != home_score or
                    existing.away_score != away_score or
                    existing.is_completed != is_completed or
                    (game_time and existing.game_time != game_time)
                )
                if needs_update:
                    existing.home_score = home_score
                    existing.away_score = away_score
                    existing.is_completed = is_completed
                    if game_time:
                        existing.game_time = game_time
                    games_updated += 1
                    print(f"  Updated: {teams.get(away_team_id, '?')} @ {teams.get(home_team_id, '?')} - {away_score or '?'}-{home_score or '?'}")
            else:
                # Add new game
                game = Game(
                    id=game_id,
                    date=game_date,
                    game_time=game_time,
                    season=season,
                    home_team_id=home_team_id,
                    away_team_id=away_team_id,
                    home_score=home_score,
                    away_score=away_score,
                    is_completed=is_completed,
                )
                db.add(game)
                games_added += 1
                status = "Final" if is_completed else "Scheduled"
                time_info = f" at {game_time.strftime('%I:%M %p')}" if game_time else ""
                print(f"  Added: {teams.get(away_team_id, '?')} @ {teams.get(home_team_id, '?')} [{status}]{time_info}")

        db.commit()
        print(f"\nAdded {games_added} new games, updated {games_updated} games")

    except Exception as e:
        db.rollback()
        print(f"Error fetching games: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--date", type=str, help="Date to fetch (YYYY-MM-DD), defaults to today")
    args = parser.parse_args()

    if args.date:
        game_date = datetime.strptime(args.date, "%Y-%m-%d").date()
    else:
        game_date = None

    fetch_todays_games(game_date)
