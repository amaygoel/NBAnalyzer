"""
Margin prediction inference pipeline for upcoming games.

Efficiently computes features for any game using single-pass state building.
Reuses TeamState logic from dataset_builder.py to avoid data leakage.
"""
from datetime import date
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
from sqlalchemy.orm import Session

from nb_analyzer.models import Game
from nb_analyzer.ml.dataset_builder import TeamState


class MarginInference:
    """
    Efficient margin prediction for upcoming games.

    Loads all completed games once, builds team states chronologically,
    then predicts margins for upcoming games using pre-computed states.
    """

    def __init__(self, db: Session, model_path: Path = None):
        """
        Initialize inference pipeline.

        Args:
            db: SQLAlchemy session
            model_path: Path to trained model artifact (default: artifacts/margin_model.pkl)
        """
        self.db = db

        if model_path is None:
            model_path = Path(__file__).parent / "artifacts" / "margin_model.pkl"

        self.model = None
        self.model_path = model_path

        # Cache of team states indexed by date
        # Keys: date objects, Values: dict[team_id -> TeamState]
        self._state_cache = {}

        # Store completed games for efficient state building
        self._completed_games = None
        self._completed_games_date_range = None

    def load_model(self):
        """Load trained model from artifact."""
        if self.model is None:
            self.model = joblib.load(self.model_path)
            print(f"✓ Loaded model from {self.model_path}")
        return self.model

    def _load_completed_games(self, until_date: Optional[date] = None):
        """
        Load all completed games from DB (single query).

        Args:
            until_date: Only load games up to this date (default: all)
        """
        query = self.db.query(Game).filter(
            Game.is_completed == True,
            Game.home_score.isnot(None),
            Game.away_score.isnot(None)
        )

        if until_date:
            query = query.filter(Game.date < until_date)

        games = query.order_by(Game.date, Game.id).all()

        self._completed_games = games
        if games:
            self._completed_games_date_range = (games[0].date, games[-1].date)
            print(f"✓ Loaded {len(games)} completed games")
            print(f"  Date range: {games[0].date} to {games[-1].date}")
        else:
            self._completed_games_date_range = (None, None)
            print("⚠️  No completed games found")

        return games

    def _build_state_until(self, target_date: date) -> dict[int, TeamState]:
        """
        Build team states up to (but not including) target_date.

        Uses single-pass algorithm to process all completed games chronologically
        and build team state as of the day before target_date.

        Args:
            target_date: Build state using only games before this date

        Returns:
            dict mapping team_id -> TeamState as of day before target_date
        """
        # Check cache first
        if target_date in self._state_cache:
            return self._state_cache[target_date]

        # Initialize team states
        team_states = {}

        def get_team_state(team_id: int) -> TeamState:
            if team_id not in team_states:
                team_states[team_id] = TeamState(team_id=team_id)
            return team_states[team_id]

        # Load completed games if not already loaded
        if self._completed_games is None:
            self._load_completed_games(until_date=target_date)

        # Process games chronologically up to target_date
        for game in self._completed_games:
            if game.date >= target_date:
                break  # Stop before target date

            # Update team states with this completed game
            home_margin = game.home_score - game.away_score
            away_margin = -home_margin

            home_state = get_team_state(game.home_team_id)
            away_state = get_team_state(game.away_team_id)

            home_state.update_after_game(home_margin, is_home=True, game_date=game.date)
            away_state.update_after_game(away_margin, is_home=False, game_date=game.date)

        # Cache the result
        self._state_cache[target_date] = team_states

        return team_states

    def features_for_game(self, game: Game) -> dict:
        """
        Extract features for a game using only data before game.date.

        Returns dict with 11 feature columns matching training data.
        """
        # Build team states up to this game's date
        team_states = self._build_state_until(game.date)

        # Get team states (or create empty if teams have no prior games)
        if game.home_team_id not in team_states:
            team_states[game.home_team_id] = TeamState(team_id=game.home_team_id)
        if game.away_team_id not in team_states:
            team_states[game.away_team_id] = TeamState(team_id=game.away_team_id)

        home_state = team_states[game.home_team_id]
        away_state = team_states[game.away_team_id]

        # Extract features (same as dataset_builder.py)
        home_win_pct = home_state.get_win_pct()
        away_win_pct = away_state.get_win_pct()

        home_avg_margin = home_state.get_avg_margin()
        away_avg_margin = away_state.get_avg_margin()

        home_home_margin = home_state.get_home_avg_margin()
        away_away_margin = away_state.get_away_avg_margin()

        home_last10_margin = home_state.get_last10_avg_margin()
        away_last10_margin = away_state.get_last10_avg_margin()

        home_rest = home_state.get_rest_days(game.date)
        away_rest = away_state.get_rest_days(game.date)

        home_b2b = 1 if home_rest == 0 else 0
        away_b2b = 1 if away_rest == 0 else 0

        return {
            'home_win_pct_to_date': home_win_pct,
            'away_win_pct_to_date': away_win_pct,
            'win_pct_diff': home_win_pct - away_win_pct,
            'home_last10_margin': home_last10_margin,
            'away_last10_margin': away_last10_margin,
            'last10_margin_diff': home_last10_margin - away_last10_margin,
            'home_home_margin_to_date': home_home_margin,
            'away_away_margin_to_date': away_away_margin,
            'rest_diff': home_rest - away_rest,
            'home_b2b': home_b2b,
            'away_b2b': away_b2b,
        }

    def predict_margin(self, game: Game) -> float:
        """
        Predict expected margin (home_score - away_score) for a game.

        Positive = home team favored
        Negative = away team favored

        Args:
            game: Game to predict

        Returns:
            Predicted margin in points
        """
        # Ensure model is loaded
        if self.model is None:
            self.load_model()

        # Extract features
        features = self.features_for_game(game)

        # Convert to DataFrame (model expects this format)
        features_df = pd.DataFrame([features])

        # Predict
        predicted_margin = self.model.predict(features_df)[0]

        return float(predicted_margin)

    def predict_margins_batch(self, games: list[Game]) -> list[tuple[Game, float, dict]]:
        """
        Predict margins for multiple games efficiently.

        Groups games by date and reuses state computation.

        Args:
            games: List of games to predict

        Returns:
            List of (game, predicted_margin, features) tuples
        """
        # Ensure model is loaded
        if self.model is None:
            self.load_model()

        # Sort games by date for efficient state building
        sorted_games = sorted(games, key=lambda g: g.date)

        results = []

        for game in sorted_games:
            features = self.features_for_game(game)
            features_df = pd.DataFrame([features])
            predicted_margin = float(self.model.predict(features_df)[0])
            results.append((game, predicted_margin, features))

        return results

    def clear_cache(self):
        """Clear state cache (useful if DB is updated)."""
        self._state_cache = {}
        self._completed_games = None
        self._completed_games_date_range = None
