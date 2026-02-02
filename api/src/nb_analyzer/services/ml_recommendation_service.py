"""
ML-based recommendation service using margin prediction model.

Provides singleton-cached inference and integrates with existing recommendation system.
"""
from typing import Optional
from sqlalchemy.orm import Session

from nb_analyzer.models import Game
from nb_analyzer.ml.margin_inference import MarginInference
from nb_analyzer.ml.bet_selector import (
    BetRecommendation,
    get_consensus_odds,
    select_best_bet
)


# Module-level singleton cache
_inference_instance: Optional[MarginInference] = None
_inference_db_id: Optional[int] = None


def get_ml_inference(db: Session) -> MarginInference:
    """
    Get cached ML inference instance.

    Loads model once and reuses across requests.
    """
    global _inference_instance, _inference_db_id

    current_db_id = id(db)

    # Initialize if first call or DB session changed
    if _inference_instance is None or _inference_db_id != current_db_id:
        _inference_instance = MarginInference(db)
        _inference_instance.load_model()
        _inference_instance._load_completed_games()
        _inference_db_id = current_db_id

    return _inference_instance


class MLRecommendationService:
    """
    Service wrapper for ML-based recommendations.

    Generates exactly one recommendation per game using margin prediction model.
    """

    def __init__(self, db: Session):
        self.db = db
        self.inference = get_ml_inference(db)

    def generate_ml_recommendation(self, game: Game) -> BetRecommendation:
        """
        Generate ML-based recommendation for a game.

        Always returns exactly one recommendation (or NO_ODDS if no market data).

        Args:
            game: Game to generate recommendation for

        Returns:
            BetRecommendation with best actionable bet and confidence tier
        """
        # Predict margin
        pred_margin = self.inference.predict_margin(game)

        # Get consensus odds
        consensus_odds = get_consensus_odds(self.db, game)

        # Select best bet
        recommendation = select_best_bet(
            game=game,
            pred_margin=pred_margin,
            consensus_odds=consensus_odds
        )

        return recommendation

    def generate_ml_recommendations_batch(
        self,
        games: list[Game]
    ) -> list[BetRecommendation]:
        """
        Generate ML-based recommendations for multiple games efficiently.

        Args:
            games: List of games to generate recommendations for

        Returns:
            List of BetRecommendation objects (one per game)
        """
        recommendations = []

        for game in games:
            rec = self.generate_ml_recommendation(game)
            recommendations.append(rec)

        return recommendations
