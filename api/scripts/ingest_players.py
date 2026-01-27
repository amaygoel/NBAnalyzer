"""
Fetch NBA players and store them in the database.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nba_api.stats.static import players as nba_players
from nba_api.stats.endpoints import commonplayerinfo

from nb_analyzer.database import SessionLocal, init_db
from nb_analyzer.models import Player, Team


def ingest_players(active_only: bool = True):
    """
    Fetch NBA players and store in database.

    Args:
        active_only: If True, only fetch currently active players
    """
    init_db()
    db = SessionLocal()

    try:
        if active_only:
            all_players = nba_players.get_active_players()
        else:
            all_players = nba_players.get_players()

        print(f"Found {len(all_players)} {'active ' if active_only else ''}players")

        # Get team abbreviation to ID mapping
        teams = {t.abbreviation: t.id for t in db.query(Team).all()}

        for i, player_data in enumerate(all_players):
            player_id = player_data["id"]

            # Check if player already exists
            existing = db.query(Player).filter(Player.id == player_id).first()

            if existing:
                print(f"  [{i+1}/{len(all_players)}] Player {player_data['full_name']} exists, skipping")
                continue

            # Get detailed player info for team and position
            # Rate limit to avoid hitting NBA API limits
            if i > 0 and i % 10 == 0:
                time.sleep(1)

            try:
                player_info = commonplayerinfo.CommonPlayerInfo(player_id=player_id)
                info_df = player_info.get_data_frames()[0]

                if not info_df.empty:
                    row = info_df.iloc[0]
                    team_abbrev = row.get("TEAM_ABBREVIATION", "")
                    team_id = teams.get(team_abbrev)
                    position = row.get("POSITION", None)
                else:
                    team_id = None
                    position = None
            except Exception as e:
                print(f"    Warning: Could not fetch details for {player_data['full_name']}: {e}")
                team_id = None
                position = None

            player = Player(
                id=player_id,
                name=player_data["full_name"],
                team_id=team_id,
                position=position,
                is_active=player_data.get("is_active", True),
            )
            db.add(player)
            print(f"  [{i+1}/{len(all_players)}] Added: {player.name}")

            # Commit in batches
            if (i + 1) % 50 == 0:
                db.commit()
                print(f"  Committed batch ({i+1} players)")

        db.commit()
        print(f"\nSuccessfully ingested {len(all_players)} players")

    except Exception as e:
        db.rollback()
        print(f"Error ingesting players: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    ingest_players(active_only=True)
