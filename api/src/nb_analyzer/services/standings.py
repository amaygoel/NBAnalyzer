"""
Service for fetching current NBA standings/records.
"""
from nba_api.stats.endpoints import leaguestandings
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from nb_analyzer.models import Team, Game


class StandingsService:
    """Service for fetching current team standings and records."""

    def __init__(self, db: Session):
        self.db = db
        self._standings_cache = None

    def _calculate_standings_from_db(self) -> dict[int, dict]:
        """Calculate standings from completed games in the database."""
        from datetime import date
        current_season = "2025-26"  # TODO: Make this dynamic

        # Get all teams
        teams = self.db.query(Team).all()
        cache = {}

        for team in teams:
            # Count wins and losses from completed games
            home_games = self.db.query(Game).filter(
                Game.home_team_id == team.id,
                Game.is_completed == True,
                Game.season == current_season
            ).all()

            away_games = self.db.query(Game).filter(
                Game.away_team_id == team.id,
                Game.is_completed == True,
                Game.season == current_season
            ).all()

            wins = 0
            losses = 0

            for game in home_games:
                if game.home_score > game.away_score:
                    wins += 1
                else:
                    losses += 1

            for game in away_games:
                if game.away_score > game.home_score:
                    wins += 1
                else:
                    losses += 1

            total_games = wins + losses
            win_pct = wins / total_games if total_games > 0 else 0.0

            cache[team.id] = {
                'wins': wins,
                'losses': losses,
                'record': f"{wins}-{losses}",
                'win_pct': win_pct,
            }

        return cache

    def _fetch_standings(self) -> dict[int, dict]:
        """Fetch current standings from NBA API and cache them."""
        if self._standings_cache is not None:
            return self._standings_cache

        try:
            standings = leaguestandings.LeagueStandings()
            df = standings.get_data_frames()[0]

            # Build cache: team_id -> {wins, losses, record_str}
            cache = {}
            for _, row in df.iterrows():
                team_id = int(row['TeamID'])
                cache[team_id] = {
                    'wins': int(row['WINS']),
                    'losses': int(row['LOSSES']),
                    'record': f"{int(row['WINS'])}-{int(row['LOSSES'])}",
                    'win_pct': float(row['WinPCT']),
                }

            self._standings_cache = cache
            return cache
        except Exception as e:
            print(f"⚠ Failed to fetch standings from NBA API: {e}")
            print("  Calculating records from games table...")
            cache = self._calculate_standings_from_db()
            self._standings_cache = cache
            return cache

    def get_team_record(self, team_id: int) -> str:
        """Get team's current W-L record string (e.g., '37-10')."""
        standings = self._fetch_standings()
        if standings and team_id in standings:
            return standings[team_id]['record']
        print(f"⚠ No record found for team {team_id}, returning 0-0")
        return "0-0"  # Fallback if team not found

    def get_team_record_data(self, team_id: int) -> dict:
        """Get detailed record data for a team."""
        standings = self._fetch_standings()
        if team_id in standings:
            return standings[team_id]
        return {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.0}
