"""
Recommendation engine for generating betting insights.
"""
from dataclasses import dataclass
from datetime import date
from sqlalchemy.orm import Session

from nb_analyzer.models import Game, Team, GameOdds
from nb_analyzer.services.team_analysis import TeamAnalysisService, Record
from nb_analyzer.services.standings import StandingsService


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
    MIN_EDGE = 0.08  # Minimum 8% edge for value bet

    def __init__(self, db: Session):
        self.db = db
        self.team_analysis = TeamAnalysisService(db)
        self.standings = StandingsService(db)

    @staticmethod
    def _american_to_implied_probability(odds: int) -> float:
        """Convert American odds to implied probability."""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)

    @staticmethod
    def _calculate_edge(historical_win_pct: float, implied_prob: float) -> float:
        """Calculate betting edge (positive means value)."""
        return historical_win_pct - implied_prob

    def _calculate_weighted_win_rate(self, team_id: int, opponent_id: int = None, is_home: bool = True) -> tuple[float, str, int]:
        """
        Calculate weighted win rate prioritizing current season.
        Returns: (weighted_win_pct, description, total_games)

        Weights:
        - Current season (2025-26): 70%
        - Last season (2024-25): 20%
        - Older season (2023-24): 10%
        """
        # Current season performance (70% weight)
        if is_home:
            current = self.team_analysis.get_home_record(team_id, season="2025-26")
        else:
            current = self.team_analysis.get_away_record(team_id, season="2025-26")

        # Last season (20% weight)
        if is_home:
            last = self.team_analysis.get_home_record(team_id, season="2024-25")
        else:
            last = self.team_analysis.get_away_record(team_id, season="2024-25")

        # Two seasons ago (10% weight)
        if is_home:
            older = self.team_analysis.get_home_record(team_id, season="2023-24")
        else:
            older = self.team_analysis.get_away_record(team_id, season="2023-24")

        # Require minimum current season games
        if current.total < 5:
            return None, None, 0

        # Sanity check: Don't recommend near-.500 teams with small sample sizes
        # If current season is 40-60% win rate with < 10 games, skip recommendation
        if current.total < 10 and 0.40 <= current.win_pct <= 0.60:
            return None, None, 0

        # Calculate weighted average
        total_weight = 0
        weighted_wins = 0
        total_games = current.total

        if current.total > 0:
            weighted_wins += current.wins * 0.70
            total_weight += current.total * 0.70

        if last.total > 0:
            weighted_wins += last.wins * 0.20
            total_weight += last.total * 0.20

        if older.total > 0:
            weighted_wins += older.wins * 0.10
            total_weight += older.total * 0.10

        if total_weight == 0:
            return None, None, 0

        weighted_win_pct = weighted_wins / total_weight

        # Description emphasizes current season
        location = "Home" if is_home else "Road"
        desc = f"{location}: {current.display} (this season)"

        return weighted_win_pct, desc, total_games

    def _get_game_odds(self, game: Game) -> dict | None:
        """Get betting odds for a game. Prefers DraftKings, falls back to first available."""
        odds_records = self.db.query(GameOdds).filter(GameOdds.game_id == game.id).all()

        if not odds_records:
            return None

        # Try to get DraftKings odds first (most popular)
        dk_odds = {
            "spread": next((o for o in odds_records if o.bookmaker == "draftkings" and o.market_type == "spreads"), None),
            "total": next((o for o in odds_records if o.bookmaker == "draftkings" and o.market_type == "totals"), None),
            "moneyline": next((o for o in odds_records if o.bookmaker == "draftkings" and o.market_type == "h2h"), None),
        }

        # Fall back to any bookmaker if DraftKings not available
        if not any(dk_odds.values()):
            dk_odds = {
                "spread": next((o for o in odds_records if o.market_type == "spreads"), None),
                "total": next((o for o in odds_records if o.market_type == "totals"), None),
                "moneyline": next((o for o in odds_records if o.market_type == "h2h"), None),
            }

        result = {}

        if dk_odds["spread"]:
            result["spread"] = {
                "home_line": dk_odds["spread"].home_line,
                "home_odds": dk_odds["spread"].home_odds,
                "away_line": dk_odds["spread"].away_line,
                "away_odds": dk_odds["spread"].away_odds,
            }

        if dk_odds["total"]:
            result["total"] = {
                "line": dk_odds["total"].over_line,
                "over_odds": dk_odds["total"].over_odds,
                "under_odds": dk_odds["total"].under_odds,
            }

        if dk_odds["moneyline"]:
            result["moneyline"] = {
                "home_odds": dk_odds["moneyline"].home_odds,
                "away_odds": dk_odds["moneyline"].away_odds,
            }

        return result if result else None

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

    def _get_team_situation(self, team_id: int, game_date: date) -> dict:
        """Determine the current situation for a team relative to a specific game date (current season, or previous if no games)."""
        games = self.team_analysis.get_team_games(team_id, season="2025-26")
        # Fall back to previous season if no games in current season
        if not games:
            games = self.team_analysis.get_team_games(team_id, season="2024-25")
        if not games:
            return {"last_result": None, "rest_days": None, "is_b2b": False}

        # Find the most recent game before the given game_date
        previous_games = [g for g in games if g.date < game_date]
        if not previous_games:
            return {"last_result": None, "rest_days": None, "is_b2b": False}

        last_game = previous_games[-1]
        last_result = "W" if self.team_analysis._team_won(last_game, team_id) else "L"
        rest_days = (game_date - last_game.date).days - 1  # Days between games
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

        home_situation = self._get_team_situation(game.home_team_id, game.date)
        away_situation = self._get_team_situation(game.away_team_id, game.date)

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

        # Home team with rest advantage (only for reasonable rest periods: 2-7 days)
        if home_situation["rest_days"] and 2 <= home_situation["rest_days"] <= 7:
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
            seasons=["2023-24", "2024-25", "2025-26"],
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

                # Only generate recommendations for upcoming games
                recs = [] if game.is_completed else self.generate_focused_recommendations(game)
                # Only get odds for upcoming games
                odds = None if game.is_completed else self._get_game_odds(game)

                # Get team records from current standings
                home_record = self.standings.get_team_record(game.home_team_id)
                away_record = self.standings.get_team_record(game.away_team_id)

                game_data = {
                    "game_id": game.id,
                    "date": game.date.isoformat(),
                    "game_time": game.game_time.isoformat() + "Z" if game.game_time else None,
                    "home_team": home_team.abbreviation if home_team else "UNK",
                    "away_team": away_team.abbreviation if away_team else "UNK",
                    "home_team_name": home_team.name if home_team else "Unknown",
                    "away_team_name": away_team.name if away_team else "Unknown",
                    "home_record": home_record,
                    "away_record": away_record,
                    "is_completed": game.is_completed,
                    "home_score": game.home_score,
                    "away_score": game.away_score,
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
                }

                # Add odds if available
                if odds:
                    game_data["odds"] = odds

                day_data["games"].append(game_data)

            # Sort games within day by recommendations count
            day_data["games"].sort(key=lambda g: -g["recommendations_count"])
            result["days"].append(day_data)

        return result

    def generate_focused_recommendations(self, game: Game) -> list[Recommendation]:
        """
        Generate focused, value-based recommendations.
        Returns max 2 recommendations:
        - ONE best bet from moneyline/spread (best edge among 4 options)
        - ONE total bet (over/under) ONLY if strong indicators exist

        NOTE: Only generates recommendations when betting lines are available.
        Pattern-based recommendations without odds are not actionable.
        """
        recommendations = []

        home_team = self.team_analysis.get_team_by_id(game.home_team_id)
        away_team = self.team_analysis.get_team_by_id(game.away_team_id)

        if not home_team or not away_team:
            return recommendations

        # Get odds
        odds = self._get_game_odds(game)
        if not odds:
            # No odds available = no actionable recommendations
            # Don't fall back to pattern-based - users can't bet without lines
            return []

        home_situation = self._get_team_situation(game.home_team_id, game.date)
        away_situation = self._get_team_situation(game.away_team_id, game.date)

        # Calculate weighted win rates (prioritizes current season)
        home_win_pct, home_desc, home_games = self._calculate_weighted_win_rate(
            game.home_team_id, game.away_team_id, is_home=True
        )
        away_win_pct, away_desc, away_games = self._calculate_weighted_win_rate(
            game.away_team_id, game.home_team_id, is_home=False
        )

        # Skip if insufficient data
        if home_win_pct is None and away_win_pct is None:
            return []

        # Calculate value for each bet option
        bet_options = []

        # Home Moneyline
        if home_win_pct and odds.get("moneyline"):
            home_odds = odds["moneyline"]["home_odds"]
            implied_prob = self._american_to_implied_probability(home_odds)
            edge = self._calculate_edge(home_win_pct, implied_prob)

            # Sanity checks for moneylines:
            # 1. Don't recommend extreme underdogs (odds > +250)
            # 2. Don't recommend teams with < 50% win rate (losing bets long-term)
            if home_odds <= 250 and home_win_pct >= 0.50:
                bet_options.append({
                    "bet_type": "moneyline",
                    "team": home_team,
                    "win_pct": home_win_pct,
                    "sample_size": home_games,
                    "description": home_desc,
                    "edge": edge,
                    "odds": home_odds,
                })

        # Away Moneyline
        if away_win_pct and odds.get("moneyline"):
            away_odds = odds["moneyline"]["away_odds"]
            implied_prob = self._american_to_implied_probability(away_odds)
            edge = self._calculate_edge(away_win_pct, implied_prob)

            # Sanity checks for moneylines:
            # 1. Don't recommend extreme underdogs (odds > +250)
            # 2. Don't recommend teams with < 50% win rate (losing bets long-term)
            if away_odds <= 250 and away_win_pct >= 0.50:
                bet_options.append({
                    "bet_type": "moneyline",
                    "team": away_team,
                    "win_pct": away_win_pct,
                    "sample_size": away_games,
                    "description": away_desc,
                    "edge": edge,
                    "odds": away_odds,
                })

        # Home Spread
        if home_win_pct and odds.get("spread"):
            # For spread, use slightly adjusted win% (more conservative)
            # Spread betting is different from straight-up wins
            adjusted_win_pct = home_win_pct * 0.92  # 8% haircut for spread
            implied_prob = self._american_to_implied_probability(odds["spread"]["home_odds"])
            edge = self._calculate_edge(adjusted_win_pct, implied_prob)

            bet_options.append({
                "bet_type": "spread",
                "team": home_team,
                "win_pct": home_win_pct,
                "sample_size": home_games,
                "description": home_desc,
                "edge": edge,
                "odds": odds["spread"]["home_odds"],
                "line": odds["spread"]["home_line"],
            })

        # Away Spread
        if away_win_pct and odds.get("spread"):
            adjusted_win_pct = away_win_pct * 0.92  # 8% haircut for spread
            implied_prob = self._american_to_implied_probability(odds["spread"]["away_odds"])
            edge = self._calculate_edge(adjusted_win_pct, implied_prob)

            bet_options.append({
                "bet_type": "spread",
                "team": away_team,
                "win_pct": away_win_pct,
                "sample_size": away_games,
                "description": away_desc,
                "edge": edge,
                "odds": odds["spread"]["away_odds"],
                "line": odds["spread"]["away_line"],
            })

        # Find best edge (if above threshold)
        if bet_options:
            best_bet = max(bet_options, key=lambda x: x["edge"])
            if best_bet["edge"] >= self.MIN_EDGE:
                insight = f"{best_bet['team'].abbreviation} "
                if best_bet["bet_type"] == "spread":
                    line_str = f"+{best_bet['line']}" if best_bet['line'] > 0 else str(best_bet['line'])
                    insight += f"{line_str} ({best_bet['description']})"
                else:
                    insight += f"ML ({best_bet['description']})"

                odds_str = f"+{best_bet['odds']}" if best_bet['odds'] > 0 else str(best_bet['odds'])

                recommendations.append(Recommendation(
                    game_id=game.id,
                    bet_type=best_bet["bet_type"],
                    subject=best_bet["team"].name,
                    subject_abbrev=best_bet["team"].abbreviation,
                    insight=insight,
                    confidence="high" if best_bet["edge"] >= 0.12 else "medium",
                    supporting_stats=[
                        {"label": "Edge", "value": f"+{best_bet['edge']:.1%}"},
                        {"label": "Historical", "value": f"{best_bet['win_pct']:.0%} (weighted)"},
                        {"label": "Implied", "value": f"{self._american_to_implied_probability(best_bet['odds']):.0%}"},
                        {"label": "Odds", "value": odds_str},
                        {"label": "Sample", "value": f"{best_bet['sample_size']} current season games"},
                    ],
                ))

        # TODO: Add total (over/under) recommendation logic
        # For now, skip totals - will add after implementing scoring analysis

        return recommendations
