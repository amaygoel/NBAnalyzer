"""
Service for fetching current NBA standings/records.
"""
from nba_api.stats.endpoints import leaguestandings
from sqlalchemy.orm import Session

from nb_analyzer.models import Team


class StandingsService:
    """Service for fetching current team standings and records."""

    def __init__(self, db: Session):
        self.db = db
        self._standings_cache = None

    def _fetch_standings(self) -> dict[int, dict]:
        """Fetch current standings from NBA API and cache them."""
        if self._standings_cache is not None:
            return self._standings_cache

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

    def get_team_record(self, team_id: int) -> str:
        """Get team's current W-L record string (e.g., '37-10')."""
        standings = self._fetch_standings()
        if team_id in standings:
            return standings[team_id]['record']
        return "0-0"  # Fallback if team not found

    def get_team_record_data(self, team_id: int) -> dict:
        """Get detailed record data for a team."""
        standings = self._fetch_standings()
        if team_id in standings:
            return standings[team_id]
        return {'wins': 0, 'losses': 0, 'record': '0-0', 'win_pct': 0.0}
