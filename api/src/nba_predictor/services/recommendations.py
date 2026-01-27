"""
Recommendation engine for generating betting insights.
"""
from dataclasses import dataclass
from datetime import date
from sqlalchemy.orm import Session

from nba_predictor.models import Game, Team
from nba_predictor.services.team_analysis import TeamAnalysisService, Record


@dataclass
class Recommendation:
    """A betting recommendation with supporting evidence."""
    game_id: int
    bet_type: str  # "moneyline", "spread", "total"
    subject: str  # Team name
    subject_abbrev: str
    insight: str  # Main recommendation text
    confidence: str  # "high", "medium"
    supporting_stats: list[dict]  # List of supporting evidence


class RecommendationService:
    """Generates betting recommendations based on team analysis."""

    # Thresholds for recommendations
    MIN_SAMPLE_SIZE = 8
    HIGH_CONFIDENCE_WIN_PCT = 0.70
    MEDIUM_CONFIDENCE_WIN_PCT = 0.62

    def __init__(self, db: Session):
        self.db = db
        self.team_analysis = TeamAnalysisService(db)

    def get_todays_games(self) -> list[Game]:
        """Get all games scheduled for today."""
        today = date.today()
        return (
            self.db.query(Game)
            .filter(Game.date == today)
            .all()
        )

    def get_upcoming_games(self, days: int = 1) -> list[Game]:
        """Get games for the next N days."""
        today = date.today()
        from datetime import timedelta
        end_date = today + timedelta(days=days)
        return (
            self.db.query(Game)
            .filter(Game.date >= today, Game.date <= end_date)
            .order_by(Game.date)
            .all()
        )

    def _check_trend_strength(self, record: Record) -> str | None:
        """Check if a trend is strong enough to recommend."""
        if record.total < self.MIN_SAMPLE_SIZE:
            return None
        if record.win_pct >= self.HIGH_CONFIDENCE_WIN_PCT:
            return "high"
        if record.win_pct >= self.MEDIUM_CONFIDENCE_WIN_PCT:
            return "medium"
        return None

    def _get_team_situation(self, team_id: int) -> dict:
        """Determine the current situation for a team."""
        games = self.team_analysis.get_team_games(team_id)
        if not games:
            return {"last_result": None, "rest_days": None, "is_b2b": False}

        last_game = games[-1]
        last_result = "W" if self.team_analysis._team_won(last_game, team_id) else "L"
        rest_days = (date.today() - last_game.date).days - 1  # Days since last game
        is_b2b = rest_days == 0

        return {
            "last_result": last_result,
            "rest_days": rest_days,
            "is_b2b": is_b2b,
        }

    def generate_recommendations_for_game(self, game: Game) -> list[Recommendation]:
        """Generate all applicable recommendations for a single game."""
        recommendations = []

        home_team = self.team_analysis.get_team_by_id(game.home_team_id)
        away_team = self.team_analysis.get_team_by_id(game.away_team_id)

        if not home_team or not away_team:
            return recommendations

        home_situation = self._get_team_situation(game.home_team_id)
        away_situation = self._get_team_situation(game.away_team_id)

        # --- Home Team Recommendations ---

        # Home team at home after a loss (bounce back)
        if home_situation["last_result"] == "L":
            record = self.team_analysis.get_home_record_after_loss(game.home_team_id)
            confidence = self._check_trend_strength(record)
            if confidence:
                recommendations.append(Recommendation(
                    game_id=game.id,
                    bet_type="moneyline",
                    subject=home_team.name,
                    subject_abbrev=home_team.abbreviation,
                    insight=f"{home_team.abbreviation} at home after a loss: {record.display} ({record.win_pct:.0%})",
                    confidence=confidence,
                    supporting_stats=[
                        {"label": "Record", "value": record.display},
                        {"label": "Win %", "value": f"{record.win_pct:.0%}"},
                        {"label": "Sample", "value": f"{record.total} games"},
                        {"label": "Situation", "value": "Home after loss"},
                    ],
                ))

        # Home team with rest advantage
        if home_situation["rest_days"] and home_situation["rest_days"] >= 2:
            record = self.team_analysis.get_well_rested_record(game.home_team_id, min_rest_days=2)
            confidence = self._check_trend_strength(record)
            if confidence:
                recommendations.append(Recommendation(
                    game_id=game.id,
                    bet_type="moneyline",
                    subject=home_team.name,
                    subject_abbrev=home_team.abbreviation,
                    insight=f"{home_team.abbreviation} well-rested ({home_situation['rest_days']} days): {record.display} ({record.win_pct:.0%})",
                    confidence=confidence,
                    supporting_stats=[
                        {"label": "Record", "value": record.display},
                        {"label": "Win %", "value": f"{record.win_pct:.0%}"},
                        {"label": "Rest days", "value": str(home_situation["rest_days"])},
                    ],
                ))

        # Home team overall home record
        home_record = self.team_analysis.get_home_record(game.home_team_id)
        confidence = self._check_trend_strength(home_record)
        if confidence:
            recommendations.append(Recommendation(
                game_id=game.id,
                bet_type="moneyline",
                subject=home_team.name,
                subject_abbrev=home_team.abbreviation,
                insight=f"{home_team.abbreviation} strong at home: {home_record.display} ({home_record.win_pct:.0%})",
                confidence=confidence,
                supporting_stats=[
                    {"label": "Home record", "value": home_record.display},
                    {"label": "Win %", "value": f"{home_record.win_pct:.0%}"},
                ],
            ))

        # --- Away Team Recommendations ---

        # Away team on the road after a win
        if away_situation["last_result"] == "W":
            record = self.team_analysis.get_away_record_after_win(game.away_team_id)
            confidence = self._check_trend_strength(record)
            if confidence:
                recommendations.append(Recommendation(
                    game_id=game.id,
                    bet_type="moneyline",
                    subject=away_team.name,
                    subject_abbrev=away_team.abbreviation,
                    insight=f"{away_team.abbreviation} on road after a win: {record.display} ({record.win_pct:.0%})",
                    confidence=confidence,
                    supporting_stats=[
                        {"label": "Record", "value": record.display},
                        {"label": "Win %", "value": f"{record.win_pct:.0%}"},
                        {"label": "Situation", "value": "Away after win"},
                    ],
                ))

        # Away team strong road record
        away_record = self.team_analysis.get_away_record(game.away_team_id)
        confidence = self._check_trend_strength(away_record)
        if confidence:
            recommendations.append(Recommendation(
                game_id=game.id,
                bet_type="moneyline",
                subject=away_team.name,
                subject_abbrev=away_team.abbreviation,
                insight=f"{away_team.abbreviation} strong on the road: {away_record.display} ({away_record.win_pct:.0%})",
                confidence=confidence,
                supporting_stats=[
                    {"label": "Away record", "value": away_record.display},
                    {"label": "Win %", "value": f"{away_record.win_pct:.0%}"},
                ],
            ))

        # --- Negative Signals (fade opportunities) ---

        # Away team on back-to-back (fade)
        if away_situation["is_b2b"]:
            b2b_record = self.team_analysis.get_back_to_back_record(game.away_team_id)
            if b2b_record.total >= self.MIN_SAMPLE_SIZE and b2b_record.win_pct <= 0.40:
                recommendations.append(Recommendation(
                    game_id=game.id,
                    bet_type="moneyline",
                    subject=home_team.name,  # Recommend the other team
                    subject_abbrev=home_team.abbreviation,
                    insight=f"Fade {away_team.abbreviation} on back-to-back: {b2b_record.display} ({b2b_record.win_pct:.0%})",
                    confidence="medium",
                    supporting_stats=[
                        {"label": f"{away_team.abbreviation} B2B record", "value": b2b_record.display},
                        {"label": "Win %", "value": f"{b2b_record.win_pct:.0%}"},
                    ],
                ))

        # --- Head to Head ---
        h2h = self.team_analysis.get_head_to_head_record(
            game.home_team_id,
            game.away_team_id,
            seasons=["2022-23", "2023-24", "2024-25"],
        )
        if h2h.total >= 4:  # Need some H2H history
            if h2h.win_pct >= 0.75:
                recommendations.append(Recommendation(
                    game_id=game.id,
                    bet_type="moneyline",
                    subject=home_team.name,
                    subject_abbrev=home_team.abbreviation,
                    insight=f"{home_team.abbreviation} dominates {away_team.abbreviation}: {h2h.display} last {h2h.total} meetings",
                    confidence="high" if h2h.total >= 6 else "medium",
                    supporting_stats=[
                        {"label": "H2H record", "value": h2h.display},
                        {"label": "Win %", "value": f"{h2h.win_pct:.0%}"},
                    ],
                ))
            elif h2h.win_pct <= 0.25:
                # Away team dominates
                away_h2h = self.team_analysis.get_head_to_head_record(
                    game.away_team_id, game.home_team_id
                )
                recommendations.append(Recommendation(
                    game_id=game.id,
                    bet_type="moneyline",
                    subject=away_team.name,
                    subject_abbrev=away_team.abbreviation,
                    insight=f"{away_team.abbreviation} dominates {home_team.abbreviation}: {away_h2h.display} last {away_h2h.total} meetings",
                    confidence="high" if h2h.total >= 6 else "medium",
                    supporting_stats=[
                        {"label": "H2H record", "value": away_h2h.display},
                        {"label": "Win %", "value": f"{away_h2h.win_pct:.0%}"},
                    ],
                ))

        # Sort by confidence (high first)
        recommendations.sort(key=lambda r: (0 if r.confidence == "high" else 1))

        return recommendations

    def get_daily_recommendations(self) -> dict:
        """Get all recommendations for today's games."""
        games = self.get_todays_games()

        result = {
            "date": date.today().isoformat(),
            "games_count": len(games),
            "games": [],
        }

        for game in games:
            home_team = self.team_analysis.get_team_by_id(game.home_team_id)
            away_team = self.team_analysis.get_team_by_id(game.away_team_id)

            recs = self.generate_recommendations_for_game(game)

            result["games"].append({
                "game_id": game.id,
                "home_team": home_team.abbreviation if home_team else "UNK",
                "away_team": away_team.abbreviation if away_team else "UNK",
                "home_team_name": home_team.name if home_team else "Unknown",
                "away_team_name": away_team.name if away_team else "Unknown",
                "recommendations_count": len(recs),
                "recommendations": [
                    {
                        "bet_type": r.bet_type,
                        "subject": r.subject_abbrev,
                        "insight": r.insight,
                        "confidence": r.confidence,
                        "supporting_stats": r.supporting_stats,
                    }
                    for r in recs
                ],
            })

        # Sort games by number of recommendations (most first)
        result["games"].sort(key=lambda g: -g["recommendations_count"])

        return result

    def get_weekly_recommendations(self, days: int = 7) -> dict:
        """Get all recommendations for the next N days, grouped by date."""
        from datetime import timedelta

        today = date.today()
        end_date = today + timedelta(days=days - 1)

        games = (
            self.db.query(Game)
            .filter(Game.date >= today, Game.date <= end_date)
            .order_by(Game.date)
            .all()
        )

        # Group games by date
        games_by_date: dict[date, list] = {}
        for game in games:
            if game.date not in games_by_date:
                games_by_date[game.date] = []
            games_by_date[game.date].append(game)

        result = {
            "start_date": today.isoformat(),
            "end_date": end_date.isoformat(),
            "total_games": len(games),
            "days": [],
        }

        for game_date in sorted(games_by_date.keys()):
            day_games = games_by_date[game_date]
            day_data = {
                "date": game_date.isoformat(),
                "games_count": len(day_games),
                "games": [],
            }

            for game in day_games:
                home_team = self.team_analysis.get_team_by_id(game.home_team_id)
                away_team = self.team_analysis.get_team_by_id(game.away_team_id)

                recs = self.generate_recommendations_for_game(game)

                day_data["games"].append({
                    "game_id": game.id,
                    "date": game.date.isoformat(),
                    "home_team": home_team.abbreviation if home_team else "UNK",
                    "away_team": away_team.abbreviation if away_team else "UNK",
                    "home_team_name": home_team.name if home_team else "Unknown",
                    "away_team_name": away_team.name if away_team else "Unknown",
                    "recommendations_count": len(recs),
                    "recommendations": [
                        {
                            "bet_type": r.bet_type,
                            "subject": r.subject_abbrev,
                            "insight": r.insight,
                            "confidence": r.confidence,
                            "supporting_stats": r.supporting_stats,
                        }
                        for r in recs
                    ],
                })

            # Sort games within day by recommendations count
            day_data["games"].sort(key=lambda g: -g["recommendations_count"])
            result["days"].append(day_data)

        return result
