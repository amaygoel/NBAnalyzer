"""
Fetch all NBA teams and store them in the database.
"""
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nba_api.stats.static import teams as nba_teams

from nb_analyzer.database import SessionLocal, init_db
from nb_analyzer.models import Team


# Conference/Division mapping (nba_api doesn't provide this directly)
TEAM_INFO = {
    "ATL": {"conference": "East", "division": "Southeast"},
    "BOS": {"conference": "East", "division": "Atlantic"},
    "BKN": {"conference": "East", "division": "Atlantic"},
    "CHA": {"conference": "East", "division": "Southeast"},
    "CHI": {"conference": "East", "division": "Central"},
    "CLE": {"conference": "East", "division": "Central"},
    "DAL": {"conference": "West", "division": "Southwest"},
    "DEN": {"conference": "West", "division": "Northwest"},
    "DET": {"conference": "East", "division": "Central"},
    "GSW": {"conference": "West", "division": "Pacific"},
    "HOU": {"conference": "West", "division": "Southwest"},
    "IND": {"conference": "East", "division": "Central"},
    "LAC": {"conference": "West", "division": "Pacific"},
    "LAL": {"conference": "West", "division": "Pacific"},
    "MEM": {"conference": "West", "division": "Southwest"},
    "MIA": {"conference": "East", "division": "Southeast"},
    "MIL": {"conference": "East", "division": "Central"},
    "MIN": {"conference": "West", "division": "Northwest"},
    "NOP": {"conference": "West", "division": "Southwest"},
    "NYK": {"conference": "East", "division": "Atlantic"},
    "OKC": {"conference": "West", "division": "Northwest"},
    "ORL": {"conference": "East", "division": "Southeast"},
    "PHI": {"conference": "East", "division": "Atlantic"},
    "PHX": {"conference": "West", "division": "Pacific"},
    "POR": {"conference": "West", "division": "Northwest"},
    "SAC": {"conference": "West", "division": "Pacific"},
    "SAS": {"conference": "West", "division": "Southwest"},
    "TOR": {"conference": "East", "division": "Atlantic"},
    "UTA": {"conference": "West", "division": "Northwest"},
    "WAS": {"conference": "East", "division": "Southeast"},
}


def ingest_teams():
    """Fetch all NBA teams and store in database."""
    init_db()
    db = SessionLocal()

    try:
        all_teams = nba_teams.get_teams()
        print(f"Found {len(all_teams)} NBA teams")

        for team_data in all_teams:
            abbrev = team_data["abbreviation"]
            team_info = TEAM_INFO.get(abbrev, {"conference": "Unknown", "division": "Unknown"})

            # Check if team already exists
            existing = db.query(Team).filter(Team.id == team_data["id"]).first()
            if existing:
                print(f"  Team {abbrev} already exists, updating...")
                existing.name = team_data["full_name"]
                existing.abbreviation = abbrev
                existing.city = team_data["city"]
                existing.conference = team_info["conference"]
                existing.division = team_info["division"]
            else:
                team = Team(
                    id=team_data["id"],
                    name=team_data["full_name"],
                    abbreviation=abbrev,
                    city=team_data["city"],
                    conference=team_info["conference"],
                    division=team_info["division"],
                )
                db.add(team)
                print(f"  Added team: {team.name}")

        db.commit()
        print(f"\nSuccessfully ingested {len(all_teams)} teams")

    except Exception as e:
        db.rollback()
        print(f"Error ingesting teams: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    ingest_teams()
