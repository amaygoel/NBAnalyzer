"""
Team-level analysis service for generating betting insights.
"""
from dataclasses import dataclass
from datetime import date
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from nb_analyzer.models import Game, Team


@dataclass
class Record:
    """Win-loss record with calculated metrics."""
    wins: int
    losses: int

    @property
    def total(self) -> int:
        return self.wins + self.losses

    @property
    def win_pct(self) -> float:
        if self.total == 0:
            return 0.0
        return self.wins / self.total

    @property
    def display(self) -> str:
        return f"{self.wins}-{self.losses}"


@dataclass
class TrendInsight:
    """A single trend insight with confidence metrics."""
    category: str  # e.g., "home_after_loss", "vs_opponent"
    description: str
    record: Record
    confidence: str  # "high", "medium", "low"

    @property
    def hit_rate(self) -> float:
        return self.record.win_pct

    @property
    def sample_size(self) -> int:
        return self.record.total


class TeamAnalysisService:
    """Analyzes team performance trends for betting insights."""

    def __init__(self, db: Session):
        self.db = db

    def get_team_by_id(self, team_id: int) -> Team | None:
        return self.db.query(Team).filter(Team.id == team_id).first()

    def get_team_by_abbrev(self, abbrev: str) -> Team | None:
        return self.db.query(Team).filter(Team.abbreviation == abbrev).first()

    def get_team_games(
        self,
        team_id: int,
        season: str | None = None,
        completed_only: bool = True,
    ) -> list[Game]:
        """Get all games for a team, optionally filtered by season."""
        query = self.db.query(Game).filter(
            or_(Game.home_team_id == team_id, Game.away_team_id == team_id)
        )
        if season:
            query = query.filter(Game.season == season)
        if completed_only:
            query = query.filter(Game.is_completed == True)
        return query.order_by(Game.date).all()

    def _team_won(self, game: Game, team_id: int) -> bool:
        """Check if the team won a given game."""
        if game.home_team_id == team_id:
            return game.home_score > game.away_score
        return game.away_score > game.home_score

    def _is_home_game(self, game: Game, team_id: int) -> bool:
        """Check if this was a home game for the team."""
        return game.home_team_id == team_id

    def get_overall_record(self, team_id: int, season: str | None = None) -> Record:
        """Get overall win-loss record."""
        games = self.get_team_games(team_id, season)
        wins = sum(1 for g in games if self._team_won(g, team_id))
        return Record(wins=wins, losses=len(games) - wins)

    def get_team_record(self, team_id: int, season: str | None = None) -> str:
        """Get team's W-L record as a string (e.g., '23-15')."""
        record = self.get_overall_record(team_id, season)
        return record.display

    def get_home_record(self, team_id: int, season: str | None = None) -> Record:
        """Get home game record."""
        games = self.get_team_games(team_id, season)
        home_games = [g for g in games if self._is_home_game(g, team_id)]
        wins = sum(1 for g in home_games if self._team_won(g, team_id))
        return Record(wins=wins, losses=len(home_games) - wins)

    def get_away_record(self, team_id: int, season: str | None = None) -> Record:
        """Get away game record."""
        games = self.get_team_games(team_id, season)
        away_games = [g for g in games if not self._is_home_game(g, team_id)]
        wins = sum(1 for g in away_games if self._team_won(g, team_id))
        return Record(wins=wins, losses=len(away_games) - wins)

    def get_record_after_win(self, team_id: int, season: str | None = None) -> Record:
        """Get record in games following a win."""
        games = self.get_team_games(team_id, season)
        wins, losses = 0, 0
        for i, game in enumerate(games[1:], 1):
            prev_game = games[i - 1]
            if self._team_won(prev_game, team_id):
                if self._team_won(game, team_id):
                    wins += 1
                else:
                    losses += 1
        return Record(wins=wins, losses=losses)

    def get_record_after_loss(self, team_id: int, season: str | None = None) -> Record:
        """Get record in games following a loss."""
        games = self.get_team_games(team_id, season)
        wins, losses = 0, 0
        for i, game in enumerate(games[1:], 1):
            prev_game = games[i - 1]
            if not self._team_won(prev_game, team_id):
                if self._team_won(game, team_id):
                    wins += 1
                else:
                    losses += 1
        return Record(wins=wins, losses=losses)

    def get_home_record_after_loss(self, team_id: int, season: str | None = None) -> Record:
        """Get home game record following a loss."""
        games = self.get_team_games(team_id, season)
        wins, losses = 0, 0
        for i, game in enumerate(games[1:], 1):
            prev_game = games[i - 1]
            if not self._team_won(prev_game, team_id) and self._is_home_game(game, team_id):
                if self._team_won(game, team_id):
                    wins += 1
                else:
                    losses += 1
        return Record(wins=wins, losses=losses)

    def get_away_record_after_win(self, team_id: int, season: str | None = None) -> Record:
        """Get away game record following a win."""
        games = self.get_team_games(team_id, season)
        wins, losses = 0, 0
        for i, game in enumerate(games[1:], 1):
            prev_game = games[i - 1]
            if self._team_won(prev_game, team_id) and not self._is_home_game(game, team_id):
                if self._team_won(game, team_id):
                    wins += 1
                else:
                    losses += 1
        return Record(wins=wins, losses=losses)

    def get_back_to_back_record(self, team_id: int, season: str | None = None) -> Record:
        """Get record in back-to-back games."""
        games = self.get_team_games(team_id, season)
        wins, losses = 0, 0
        for game in games:
            is_b2b = (
                (game.home_team_id == team_id and game.is_home_back_to_back) or
                (game.away_team_id == team_id and game.is_away_back_to_back)
            )
            if is_b2b:
                if self._team_won(game, team_id):
                    wins += 1
                else:
                    losses += 1
        return Record(wins=wins, losses=losses)

    def get_well_rested_record(self, team_id: int, min_rest_days: int = 2, season: str | None = None) -> Record:
        """Get record when team has had extra rest (2+ days)."""
        games = self.get_team_games(team_id, season)
        wins, losses = 0, 0
        for game in games:
            rest_days = (
                game.home_rest_days if game.home_team_id == team_id else game.away_rest_days
            )
            if rest_days is not None and rest_days >= min_rest_days:
                if self._team_won(game, team_id):
                    wins += 1
                else:
                    losses += 1
        return Record(wins=wins, losses=losses)

    def get_head_to_head_record(
        self,
        team_id: int,
        opponent_id: int,
        seasons: list[str] | None = None,
    ) -> Record:
        """Get record against a specific opponent."""
        query = self.db.query(Game).filter(
            Game.is_completed == True,
            or_(
                and_(Game.home_team_id == team_id, Game.away_team_id == opponent_id),
                and_(Game.home_team_id == opponent_id, Game.away_team_id == team_id),
            )
        )
        if seasons:
            query = query.filter(Game.season.in_(seasons))

        games = query.order_by(Game.date).all()
        wins = sum(1 for g in games if self._team_won(g, team_id))
        return Record(wins=wins, losses=len(games) - wins)

    def get_recent_form(self, team_id: int, num_games: int = 10, season: str | None = None) -> Record:
        """Get record over the last N games from current season (or previous if no completed games)."""
        # Default to current season if not specified
        if season is None:
            season = "2025-26"
        games = self.get_team_games(team_id, season=season)
        # If no completed games in current season, fall back to previous season
        if not games:
            games = self.get_team_games(team_id, season="2024-25")
        recent = games[-num_games:] if len(games) >= num_games else games
        wins = sum(1 for g in recent if self._team_won(g, team_id))
        return Record(wins=wins, losses=len(recent) - wins)

    def get_recent_games(self, team_id: int, num_games: int = 10, season: str | None = None) -> list[dict]:
        """Get details of last N games from current season (or previous if no completed games)."""
        # Default to current season if not specified
        if season is None:
            season = "2025-26"
        games = self.get_team_games(team_id, season=season)
        # If no completed games in current season, fall back to previous season
        if not games:
            games = self.get_team_games(team_id, season="2024-25")
        recent = games[-num_games:] if len(games) >= num_games else games

        results = []
        for game in reversed(recent):  # Most recent first
            is_home = self._is_home_game(game, team_id)
            opponent_id = game.away_team_id if is_home else game.home_team_id
            opponent = self.get_team_by_id(opponent_id)
            won = self._team_won(game, team_id)

            team_score = game.home_score if is_home else game.away_score
            opp_score = game.away_score if is_home else game.home_score

            results.append({
                "date": game.date.isoformat(),
                "opponent": opponent.abbreviation if opponent else "UNK",
                "home": is_home,
                "result": "W" if won else "L",
                "score": f"{team_score}-{opp_score}",
            })
        return results

    def _calculate_confidence(self, record: Record) -> str:
        """Determine confidence level based on sample size and win rate."""
        if record.total < 5:
            return "low"
        if record.total < 10:
            return "medium" if record.win_pct >= 0.6 or record.win_pct <= 0.4 else "low"
        # 10+ games
        if record.win_pct >= 0.7 or record.win_pct <= 0.3:
            return "high"
        if record.win_pct >= 0.6 or record.win_pct <= 0.4:
            return "medium"
        return "low"

    def get_all_trends(self, team_id: int, season: str | None = None) -> list[TrendInsight]:
        """Get all calculated trends for a team."""
        team = self.get_team_by_id(team_id)
        if not team:
            return []

        trends = []

        # Overall record
        overall = self.get_overall_record(team_id, season)
        trends.append(TrendInsight(
            category="overall",
            description=f"Overall record: {overall.display}",
            record=overall,
            confidence=self._calculate_confidence(overall),
        ))

        # Home record
        home = self.get_home_record(team_id, season)
        trends.append(TrendInsight(
            category="home",
            description=f"Home record: {home.display}",
            record=home,
            confidence=self._calculate_confidence(home),
        ))

        # Away record
        away = self.get_away_record(team_id, season)
        trends.append(TrendInsight(
            category="away",
            description=f"Away record: {away.display}",
            record=away,
            confidence=self._calculate_confidence(away),
        ))

        # After win
        after_win = self.get_record_after_win(team_id, season)
        if after_win.total >= 3:
            trends.append(TrendInsight(
                category="after_win",
                description=f"After a win: {after_win.display}",
                record=after_win,
                confidence=self._calculate_confidence(after_win),
            ))

        # After loss
        after_loss = self.get_record_after_loss(team_id, season)
        if after_loss.total >= 3:
            trends.append(TrendInsight(
                category="after_loss",
                description=f"After a loss: {after_loss.display}",
                record=after_loss,
                confidence=self._calculate_confidence(after_loss),
            ))

        # Home after loss (bounce back)
        home_after_loss = self.get_home_record_after_loss(team_id, season)
        if home_after_loss.total >= 3:
            trends.append(TrendInsight(
                category="home_after_loss",
                description=f"At home after a loss: {home_after_loss.display}",
                record=home_after_loss,
                confidence=self._calculate_confidence(home_after_loss),
            ))

        # Away after win
        away_after_win = self.get_away_record_after_win(team_id, season)
        if away_after_win.total >= 3:
            trends.append(TrendInsight(
                category="away_after_win",
                description=f"On the road after a win: {away_after_win.display}",
                record=away_after_win,
                confidence=self._calculate_confidence(away_after_win),
            ))

        # Back to back
        b2b = self.get_back_to_back_record(team_id, season)
        if b2b.total >= 3:
            trends.append(TrendInsight(
                category="back_to_back",
                description=f"In back-to-back games: {b2b.display}",
                record=b2b,
                confidence=self._calculate_confidence(b2b),
            ))

        # Well rested
        rested = self.get_well_rested_record(team_id, min_rest_days=2, season=season)
        if rested.total >= 3:
            trends.append(TrendInsight(
                category="well_rested",
                description=f"With 2+ days rest: {rested.display}",
                record=rested,
                confidence=self._calculate_confidence(rested),
            ))

        # Recent form (always current season)
        recent = self.get_recent_form(team_id, num_games=10, season="2025-26")
        if recent.total >= 5:
            trends.append(TrendInsight(
                category="recent_form",
                description=f"Last {recent.total} games: {recent.display}",
                record=recent,
                confidence=self._calculate_confidence(recent),
            ))

        return trends

    def get_game_insights(
        self,
        home_team_id: int,
        away_team_id: int,
        seasons: list[str] | None = None,
    ) -> dict:
        """
        Get comprehensive insights for an upcoming game.
        Returns insights for both teams plus head-to-head.
        """
        if seasons is None:
            seasons = ["2023-24", "2024-25", "2025-26"]

        home_team = self.get_team_by_id(home_team_id)
        away_team = self.get_team_by_id(away_team_id)

        # Get last game results to determine if coming off win/loss (current season, or previous if no games)
        home_games = self.get_team_games(home_team_id, season="2025-26")
        if not home_games:
            home_games = self.get_team_games(home_team_id, season="2024-25")

        away_games = self.get_team_games(away_team_id, season="2025-26")
        if not away_games:
            away_games = self.get_team_games(away_team_id, season="2024-25")

        home_last_result = None
        away_last_result = None
        if home_games:
            home_last_result = "W" if self._team_won(home_games[-1], home_team_id) else "L"
        if away_games:
            away_last_result = "W" if self._team_won(away_games[-1], away_team_id) else "L"

        # Calculate rest days (current season, or previous if no games)
        home_rest = None
        away_rest = None
        if home_games:
            home_rest = (date.today() - home_games[-1].date).days
        if away_games:
            away_rest = (date.today() - away_games[-1].date).days

        return {
            "home_team": {
                "id": home_team_id,
                "name": home_team.name if home_team else None,
                "abbreviation": home_team.abbreviation if home_team else None,
                "last_result": home_last_result,
                "rest_days": home_rest,
                "trends": [
                    {
                        "category": t.category,
                        "description": t.description,
                        "record": t.record.display,
                        "win_pct": round(t.hit_rate * 100, 1),
                        "sample_size": t.sample_size,
                        "confidence": t.confidence,
                    }
                    for t in self.get_all_trends(home_team_id)
                    if t.confidence in ("high", "medium")
                ],
                "recent_games": self.get_recent_games(home_team_id, 5, season="2025-26"),
            },
            "away_team": {
                "id": away_team_id,
                "name": away_team.name if away_team else None,
                "abbreviation": away_team.abbreviation if away_team else None,
                "last_result": away_last_result,
                "rest_days": away_rest,
                "trends": [
                    {
                        "category": t.category,
                        "description": t.description,
                        "record": t.record.display,
                        "win_pct": round(t.hit_rate * 100, 1),
                        "sample_size": t.sample_size,
                        "confidence": t.confidence,
                    }
                    for t in self.get_all_trends(away_team_id)
                    if t.confidence in ("high", "medium")
                ],
                "recent_games": self.get_recent_games(away_team_id, 5, season="2025-26"),
            },
            "head_to_head": {
                "home_record": self.get_head_to_head_record(home_team_id, away_team_id, seasons).display,
                "away_record": self.get_head_to_head_record(away_team_id, home_team_id, seasons).display,
            },
        }
