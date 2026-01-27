"""
Fetch current betting odds from The Odds API and store in database.
"""
import sys
import os
from pathlib import Path
from datetime import datetime
import requests
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nb_analyzer.database import SessionLocal, init_db
from nb_analyzer.models import Game, Team, GameOdds

# Load environment variables
load_dotenv()
ODDS_API_KEY = os.getenv("ODDS_API_KEY")

def fetch_nba_odds():
    """Fetch NBA odds from The Odds API."""
    url = "https://api.the-odds-api.com/v4/sports/basketball_nba/odds/"
    params = {
        "apiKey": ODDS_API_KEY,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "oddsFormat": "american",
    }

    print(f"Fetching odds from The Odds API...")
    response = requests.get(url, params=params)

    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        print(response.text)
        return None

    print(f"✅ Successfully fetched odds")
    print(f"Remaining requests: {response.headers.get('x-requests-remaining', 'unknown')}")

    return response.json()


def store_odds_in_db(odds_data):
    """Store odds in database."""
    init_db()
    db = SessionLocal()

    try:
        # Get all teams for name matching
        teams = {t.name: t for t in db.query(Team).all()}
        stored_count = 0
        skipped_count = 0

        for game_data in odds_data:
            home_team_name = game_data["home_team"]
            away_team_name = game_data["away_team"]

            # Find matching teams
            home_team = teams.get(home_team_name)
            away_team = teams.get(away_team_name)

            if not home_team or not away_team:
                print(f"  ⚠️  Skipping {away_team_name} @ {home_team_name} - teams not in database")
                skipped_count += 1
                continue

            # Parse commence time (UTC) and convert to EST
            commence_time_utc = datetime.fromisoformat(game_data["commence_time"].replace("Z", "+00:00"))

            # Convert to EST (UTC-5, or UTC-4 during DST)
            # Simple approach: subtract 5 hours to get EST date
            from datetime import timedelta
            est_time = commence_time_utc - timedelta(hours=5)
            game_date = est_time.date()

            # Find or create game
            game = db.query(Game).filter(
                Game.home_team_id == home_team.id,
                Game.away_team_id == away_team.id,
                Game.date == game_date
            ).first()

            if not game:
                print(f"  ⚠️  No game found for {away_team_name} @ {home_team_name} on {game_date}")
                skipped_count += 1
                continue

            # Delete existing odds for this game (to refresh with latest)
            db.query(GameOdds).filter(GameOdds.game_id == game.id).delete()

            # Process each bookmaker
            for bookmaker in game_data.get("bookmakers", []):
                bookmaker_key = bookmaker["key"]
                last_update = datetime.fromisoformat(bookmaker["last_update"].replace("Z", "+00:00"))

                for market in bookmaker["markets"]:
                    market_type = market["key"]

                    odds_record = GameOdds(
                        game_id=game.id,
                        bookmaker=bookmaker_key,
                        market_type=market_type,
                        last_update=last_update,
                    )

                    if market_type == "spreads":
                        for outcome in market["outcomes"]:
                            if outcome["name"] == home_team_name:
                                odds_record.home_line = outcome["point"]
                                odds_record.home_odds = outcome["price"]
                            elif outcome["name"] == away_team_name:
                                odds_record.away_line = outcome["point"]
                                odds_record.away_odds = outcome["price"]

                    elif market_type == "totals":
                        for outcome in market["outcomes"]:
                            if outcome["name"] == "Over":
                                odds_record.over_line = outcome["point"]
                                odds_record.over_odds = outcome["price"]
                            elif outcome["name"] == "Under":
                                odds_record.under_line = outcome["point"]
                                odds_record.under_odds = outcome["price"]

                    elif market_type == "h2h":  # moneyline
                        for outcome in market["outcomes"]:
                            if outcome["name"] == home_team_name:
                                odds_record.home_odds = outcome["price"]
                            elif outcome["name"] == away_team_name:
                                odds_record.away_odds = outcome["price"]

                    db.add(odds_record)
                    stored_count += 1

            print(f"  ✅ Stored odds for {away_team.abbreviation} @ {home_team.abbreviation}")

        db.commit()
        print(f"\n✅ Successfully stored {stored_count} odds records")
        print(f"⚠️  Skipped {skipped_count} games (not in database)")

    except Exception as e:
        db.rollback()
        print(f"❌ Error storing odds: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    if not ODDS_API_KEY:
        print("❌ Error: ODDS_API_KEY not found in .env file")
        sys.exit(1)

    odds_data = fetch_nba_odds()

    if odds_data:
        print(f"\nFound odds for {len(odds_data)} games\n")
        store_odds_in_db(odds_data)
