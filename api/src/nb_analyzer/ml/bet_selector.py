"""
Bet selection logic using margin predictions and market odds.

Converts predicted margins to win/cover probabilities using normal distribution,
then calculates expected value for moneyline and spread bets.
"""
from dataclasses import dataclass
from typing import Optional
import math

from sqlalchemy.orm import Session

from nb_analyzer.models import Game, GameOdds


# Default sigma from model RMSE
DEFAULT_SIGMA = 14.4

# Confidence tier thresholds (tunable)
CONFIDENCE_HIGH_MIN_EV = 0.06
CONFIDENCE_HIGH_MIN_PROB = 0.60

CONFIDENCE_MEDIUM_MIN_EV = 0.03
CONFIDENCE_MEDIUM_MIN_PROB = 0.57

CONFIDENCE_LOW_MIN_EV = 0.00
CONFIDENCE_LOW_MIN_PROB = 0.52


# ============================================================================
# Odds conversion utilities
# ============================================================================

def american_to_decimal(american_odds: int) -> float:
    """
    Convert American odds to decimal odds.

    Examples:
        +150 -> 2.50 (win $1.50 on $1 bet)
        -150 -> 1.67 (win $0.67 on $1 bet)
    """
    if american_odds > 0:
        return 1 + (american_odds / 100)
    else:
        return 1 + (100 / abs(american_odds))


def implied_prob_from_american(american_odds: int) -> float:
    """
    Calculate implied probability from American odds (no-vig).

    Examples:
        +150 -> 0.40 (40%)
        -150 -> 0.60 (60%)
    """
    if american_odds > 0:
        return 100 / (american_odds + 100)
    else:
        return abs(american_odds) / (abs(american_odds) + 100)


def ev_from_prob_and_american(prob: float, american_odds: int) -> float:
    """
    Calculate expected value (profit per $1 stake) given true probability and odds.

    EV = prob * (decimal_odds - 1) - (1 - prob) * 1
       = prob * decimal_odds - 1

    Args:
        prob: True probability of winning (0 to 1)
        american_odds: American odds for the bet

    Returns:
        Expected profit per $1 wagered (e.g., 0.05 = 5% expected return)
    """
    decimal_odds = american_to_decimal(american_odds)
    return prob * decimal_odds - 1


# ============================================================================
# Probability calculations from margin predictions
# ============================================================================

def normal_cdf(x: float) -> float:
    """
    Standard normal CDF using error function.

    CDF(x) = 0.5 * (1 + erf(x / sqrt(2)))
    """
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def win_prob_from_margin(pred_margin: float, sigma: float = DEFAULT_SIGMA) -> float:
    """
    Calculate probability home team wins given predicted margin.

    Assumes actual_margin ~ Normal(pred_margin, sigma)
    P(home_win) = P(actual_margin > 0) = CDF(pred_margin / sigma)

    Args:
        pred_margin: Predicted home_score - away_score
        sigma: Standard deviation of prediction error (default: model RMSE)

    Returns:
        Probability home team wins (0 to 1)
    """
    if pred_margin == 0:
        return 0.5

    z_score = pred_margin / sigma
    return normal_cdf(z_score)


def cover_prob_from_margin(
    pred_margin: float,
    spread_line: float,
    sigma: float = DEFAULT_SIGMA
) -> float:
    """
    Calculate probability home team covers the spread.

    Assumes actual_margin ~ Normal(pred_margin, sigma)

    Spread convention: If home_line = -6.5, home must win by 7+ to cover.
    Therefore: home covers if actual_margin > abs(spread_line) = 6.5

    General formula: home covers if actual_margin > -spread_line
    P(home_cover) = P(actual_margin > -spread_line)
                  = 1 - CDF((-spread_line - pred_margin) / sigma)

    Args:
        pred_margin: Predicted home_score - away_score
        spread_line: Home spread line (negative if favored, e.g., -6.5)
        sigma: Standard deviation of prediction error

    Returns:
        Probability home team covers spread (0 to 1)

    Examples:
        pred_margin=10, spread_line=-6.5 -> high prob (model predicts 10pt win, needs 7+)
        pred_margin=3, spread_line=-6.5 -> low prob (model predicts 3pt win, needs 7+)
    """
    # Home covers if actual_margin > -spread_line
    # E.g., if spread_line=-6.5, home covers if margin > 6.5
    threshold = -spread_line
    z_score = (threshold - pred_margin) / sigma
    return 1 - normal_cdf(z_score)


# ============================================================================
# Consensus odds extraction
# ============================================================================

@dataclass
class ConsensusOdds:
    """Consensus odds across bookmakers for a game."""
    # Spread market
    spread_line_home: Optional[float] = None  # Home line (negative if favored)
    spread_odds_home: Optional[int] = None    # American odds for home spread
    spread_odds_away: Optional[int] = None    # American odds for away spread

    # Moneyline market
    ml_odds_home: Optional[int] = None        # American odds for home ML
    ml_odds_away: Optional[int] = None        # American odds for away ML


def get_consensus_odds(db: Session, game: Game) -> ConsensusOdds:
    """
    Get consensus odds for a game using median across bookmakers.

    For spreads: use median line, then median odds among books with that line.
    For moneyline: use median odds across all books.

    Args:
        db: Database session
        game: Game to get odds for

    Returns:
        ConsensusOdds object with median values (None if not available)
    """
    import numpy as np

    # Query all odds for this game
    spread_odds = db.query(GameOdds).filter(
        GameOdds.game_id == game.id,
        GameOdds.market_type == 'spreads',
        GameOdds.home_line.isnot(None)
    ).all()

    ml_odds = db.query(GameOdds).filter(
        GameOdds.game_id == game.id,
        GameOdds.market_type == 'h2h',
        GameOdds.home_odds.isnot(None),
        GameOdds.away_odds.isnot(None)
    ).all()

    consensus = ConsensusOdds()

    # Spread consensus
    if spread_odds:
        lines = [o.home_line for o in spread_odds]
        median_line = float(np.median(lines))

        # Get odds from books with the median line (or closest)
        closest_odds = min(spread_odds, key=lambda o: abs(o.home_line - median_line))

        # Use odds from books at or near median line
        matching_odds = [
            o for o in spread_odds
            if abs(o.home_line - median_line) <= 0.5
        ]

        if matching_odds:
            home_odds_list = [o.home_odds for o in matching_odds if o.home_odds is not None]
            away_odds_list = [o.away_odds for o in matching_odds if o.away_odds is not None]

            consensus.spread_line_home = median_line
            if home_odds_list:
                consensus.spread_odds_home = int(np.median(home_odds_list))
            if away_odds_list:
                consensus.spread_odds_away = int(np.median(away_odds_list))

    # Moneyline consensus
    if ml_odds:
        home_ml_list = [o.home_odds for o in ml_odds]
        away_ml_list = [o.away_odds for o in ml_odds]

        consensus.ml_odds_home = int(np.median(home_ml_list))
        consensus.ml_odds_away = int(np.median(away_ml_list))

    return consensus


# ============================================================================
# Bet selection
# ============================================================================

@dataclass
class BetCandidate:
    """A potential bet with its expected value."""
    market: str         # 'moneyline' or 'spread'
    side: str          # 'home' or 'away'
    line: Optional[float]  # Spread line (None for ML)
    odds: int          # American odds
    probability: float # True probability of winning bet
    ev: float          # Expected value (profit per $1)

    def __str__(self):
        if self.market == 'spread':
            return f"{self.side.upper()} {self.line:+.1f} @ {self.odds:+d}"
        else:
            return f"{self.side.upper()} ML @ {self.odds:+d}"


@dataclass
class BetRecommendation:
    """Best bet recommendation for a game."""
    game: Game
    pred_margin: float
    sigma: float
    consensus_odds: ConsensusOdds
    best_bet: Optional[BetCandidate] = None  # Actionable bet (or None)
    best_overall: Optional[BetCandidate] = None  # Best EV regardless of thresholds
    all_candidates: list[BetCandidate] = None
    confidence_tier: str = "NO_ODDS"  # HIGH, MEDIUM, LOW, NO_BET, NO_ODDS

    def has_recommendation(self) -> bool:
        return self.best_bet is not None

    def is_actionable(self) -> bool:
        """Returns True if confidence is HIGH or MEDIUM."""
        return self.confidence_tier in ["HIGH", "MEDIUM"]


def determine_confidence_tier(bet: BetCandidate) -> str:
    """
    Determine confidence tier based on EV and probability thresholds.

    Returns: "HIGH", "MEDIUM", "LOW", or "NO_BET"
    """
    if bet.ev >= CONFIDENCE_HIGH_MIN_EV and bet.probability >= CONFIDENCE_HIGH_MIN_PROB:
        return "HIGH"
    elif bet.ev >= CONFIDENCE_MEDIUM_MIN_EV and bet.probability >= CONFIDENCE_MEDIUM_MIN_PROB:
        return "MEDIUM"
    elif bet.ev >= CONFIDENCE_LOW_MIN_EV and bet.probability >= CONFIDENCE_LOW_MIN_PROB:
        return "LOW"
    else:
        return "NO_BET"


def select_best_bet(
    game: Game,
    pred_margin: float,
    consensus_odds: ConsensusOdds,
    max_spread: float = 14.0,
    sigma: float = DEFAULT_SIGMA
) -> BetRecommendation:
    """
    Select the single best bet for a game based on expected value.

    Always returns a recommendation when odds exist, with confidence tier.
    Evaluates 4 candidates: home ML, away ML, home spread, away spread.

    Args:
        game: Game to bet on
        pred_margin: Predicted home_score - away_score
        consensus_odds: Market odds
        max_spread: Maximum spread size to consider (default 14 pts)
        sigma: Prediction error std dev

    Returns:
        BetRecommendation with best bet and confidence tier
    """
    candidates = []

    # Calculate win probabilities
    prob_home_win = win_prob_from_margin(pred_margin, sigma)
    prob_away_win = 1 - prob_home_win

    # Moneyline candidates
    if consensus_odds.ml_odds_home is not None:
        ev_home_ml = ev_from_prob_and_american(prob_home_win, consensus_odds.ml_odds_home)
        candidates.append(BetCandidate(
            market='moneyline',
            side='home',
            line=None,
            odds=consensus_odds.ml_odds_home,
            probability=prob_home_win,
            ev=ev_home_ml
        ))

    if consensus_odds.ml_odds_away is not None:
        ev_away_ml = ev_from_prob_and_american(prob_away_win, consensus_odds.ml_odds_away)
        candidates.append(BetCandidate(
            market='moneyline',
            side='away',
            line=None,
            odds=consensus_odds.ml_odds_away,
            probability=prob_away_win,
            ev=ev_away_ml
        ))

    # Spread candidates (only if spread size is reasonable)
    if (consensus_odds.spread_line_home is not None and
        abs(consensus_odds.spread_line_home) <= max_spread):

        # Calculate cover probabilities
        prob_home_cover = cover_prob_from_margin(
            pred_margin,
            consensus_odds.spread_line_home,
            sigma
        )
        prob_away_cover = 1 - prob_home_cover

        if consensus_odds.spread_odds_home is not None:
            ev_home_spread = ev_from_prob_and_american(
                prob_home_cover,
                consensus_odds.spread_odds_home
            )
            candidates.append(BetCandidate(
                market='spread',
                side='home',
                line=consensus_odds.spread_line_home,
                odds=consensus_odds.spread_odds_home,
                probability=prob_home_cover,
                ev=ev_home_spread
            ))

        if consensus_odds.spread_odds_away is not None:
            # Away line is opposite of home line
            away_line = -consensus_odds.spread_line_home
            ev_away_spread = ev_from_prob_and_american(
                prob_away_cover,
                consensus_odds.spread_odds_away
            )
            candidates.append(BetCandidate(
                market='spread',
                side='away',
                line=away_line,
                odds=consensus_odds.spread_odds_away,
                probability=prob_away_cover,
                ev=ev_away_spread
            ))

    # If no candidates, return NO_ODDS
    if not candidates:
        return BetRecommendation(
            game=game,
            pred_margin=pred_margin,
            sigma=sigma,
            consensus_odds=consensus_odds,
            best_bet=None,
            best_overall=None,
            all_candidates=[],
            confidence_tier="NO_ODDS"
        )

    # Find best candidate overall (max EV regardless of thresholds)
    best_overall = max(candidates, key=lambda c: c.ev)

    # Find best actionable candidate (prob >= 52% threshold)
    actionable_candidates = [
        c for c in candidates
        if c.probability >= CONFIDENCE_LOW_MIN_PROB
    ]

    best_actionable = None
    confidence_tier = "NO_BET"

    if actionable_candidates:
        best_actionable = max(actionable_candidates, key=lambda c: c.ev)
        confidence_tier = determine_confidence_tier(best_actionable)

    return BetRecommendation(
        game=game,
        pred_margin=pred_margin,
        sigma=sigma,
        consensus_odds=consensus_odds,
        best_bet=best_actionable,  # Actionable bet (or None if no candidates pass threshold)
        best_overall=best_overall,  # Best EV regardless of thresholds
        all_candidates=candidates,
        confidence_tier=confidence_tier
    )
