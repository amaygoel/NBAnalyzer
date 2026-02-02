#!/usr/bin/env python3
"""
Pick the single best bet for each upcoming NBA game.

Uses margin predictions + market odds to calculate expected value
for moneyline and spread bets, then recommends the best opportunity.
"""
import sys
from pathlib import Path
from datetime import date, timedelta
from typing import Optional
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy.orm import Session

from nb_analyzer.database import SessionLocal, init_db
from nb_analyzer.models import Game, Team, GameOdds
from nb_analyzer.ml.margin_inference import MarginInference
from nb_analyzer.ml.bet_selector import (
    get_consensus_odds,
    select_best_bet,
    BetRecommendation,
    DEFAULT_SIGMA
)


def diagnose_odds_coverage(db: Session, days: int = 3):
    """
    Diagnose odds coverage issues.

    Shows why games are labeled NO_ODDS.
    """
    today = date.today()
    end_date = today + timedelta(days=days)

    print("\n" + "="*90)
    print(f"ODDS COVERAGE DIAGNOSTICS (Next {days} days)")
    print("="*90)

    # Get upcoming games
    upcoming_games = db.query(Game).filter(
        Game.date >= today,
        Game.date <= end_date,
        Game.is_completed == False
    ).order_by(Game.date, Game.id).all()

    print(f"\nTotal upcoming games: {len(upcoming_games)}")

    # Get team info
    teams = {t.id: t for t in db.query(Team).all()}

    # Analyze odds coverage
    games_with_any_odds = 0
    games_with_spreads = 0
    games_with_h2h = 0
    games_with_totals = 0
    no_odds_reasons = []

    print(f"\nAnalyzing odds for each game...")
    print("="*90)

    for i, game in enumerate(upcoming_games, 1):
        home_team = teams.get(game.home_team_id)
        away_team = teams.get(game.away_team_id)

        if not home_team or not away_team:
            continue

        matchup = f"{away_team.abbreviation} @ {home_team.abbreviation}"

        # Query all odds for this game
        all_odds = db.query(GameOdds).filter(
            GameOdds.game_id == game.id
        ).all()

        # Check spreads
        spread_odds = [o for o in all_odds if o.market_type == 'spreads' and o.home_line is not None]

        # Check h2h (moneyline)
        h2h_odds = [o for o in all_odds if o.market_type == 'h2h' and o.home_odds is not None and o.away_odds is not None]

        # Check totals
        totals_odds = [o for o in all_odds if o.market_type == 'totals']

        has_any = len(all_odds) > 0
        has_spreads = len(spread_odds) > 0
        has_h2h = len(h2h_odds) > 0
        has_totals = len(totals_odds) > 0

        if has_any:
            games_with_any_odds += 1
        if has_spreads:
            games_with_spreads += 1
        if has_h2h:
            games_with_h2h += 1
        if has_totals:
            games_with_totals += 1

        # Determine why NO_ODDS
        reason = None
        if not has_any:
            reason = "no_odds_in_db"
        elif not has_spreads and not has_h2h:
            reason = "only_totals"
        elif not has_spreads and has_h2h:
            reason = "missing_spreads"
        elif has_spreads and not has_h2h:
            reason = "missing_moneyline"

        if reason:
            no_odds_reasons.append(reason)

        # Log first 5 NO_ODDS games in detail
        if reason and len([r for r in no_odds_reasons if r == reason]) <= 2:
            print(f"\n{i}. {matchup} (Game ID: {game.id}, Date: {game.date})")
            print(f"   Status: NO_ODDS - Reason: {reason}")
            print(f"   Query: GameOdds.game_id == {game.id}")
            print(f"   Results:")
            print(f"     - Total odds rows: {len(all_odds)}")
            print(f"     - Spreads (market_type='spreads', home_line IS NOT NULL): {len(spread_odds)}")
            print(f"     - Moneyline (market_type='h2h', home_odds/away_odds IS NOT NULL): {len(h2h_odds)}")
            print(f"     - Totals (market_type='totals'): {len(totals_odds)}")
            if all_odds:
                print(f"   Sample odds records:")
                for odd in all_odds[:3]:
                    print(f"     - Bookmaker: {odd.bookmaker_key}, Market: {odd.market_type}, "
                          f"Home line: {odd.home_line}, Home odds: {odd.home_odds}, Away odds: {odd.away_odds}")

    # Summary
    print("\n" + "="*90)
    print("SUMMARY")
    print("="*90)
    print(f"\nTotal upcoming games:      {len(upcoming_games)}")
    print(f"Games with ANY odds:       {games_with_any_odds} ({games_with_any_odds/len(upcoming_games):.1%})")
    print(f"Games with spreads:        {games_with_spreads} ({games_with_spreads/len(upcoming_games):.1%})")
    print(f"Games with moneyline:      {games_with_h2h} ({games_with_h2h/len(upcoming_games):.1%})")
    print(f"Games with totals:         {games_with_totals} ({games_with_totals/len(upcoming_games):.1%})")

    # Top reasons for NO_ODDS
    if no_odds_reasons:
        print(f"\nTop reasons for NO_ODDS:")
        reason_counts = Counter(no_odds_reasons)
        for reason, count in reason_counts.most_common(3):
            print(f"  {count:2d} games: {reason}")
    else:
        print(f"\n✓ All games have odds available")


def print_bet_recommendations(
    db: Session,
    inference: MarginInference,
    days: int = 3,
    debug: bool = False,
    only_bets: bool = False
):
    """
    Print bet recommendations for upcoming games.

    Args:
        db: Database session
        inference: Margin inference pipeline
        days: Number of days ahead to predict
        debug: If True, show all 4 candidate EVs for first 5 games
        only_bets: If True, only show HIGH/MEDIUM confidence games
    """
    today = date.today()
    end_date = today + timedelta(days=days)

    print("\n" + "="*90)
    print(f"NBA BET RECOMMENDATIONS (Next {days} days)")
    print("="*90)

    # Get upcoming games
    upcoming_games = db.query(Game).filter(
        Game.date >= today,
        Game.date <= end_date,
        Game.is_completed == False
    ).order_by(Game.date, Game.id).all()

    if not upcoming_games:
        print(f"\n⚠️  No upcoming games found in next {days} days")
        return

    print(f"\nFound {len(upcoming_games)} upcoming games")
    print(f"Using sigma = {DEFAULT_SIGMA:.1f} (model RMSE)")
    print(f"Confidence tiers: HIGH (EV≥6%, Prob≥60%), MEDIUM (EV≥3%, Prob≥57%), LOW (EV≥0%, Prob≥52%)")
    if only_bets:
        print(f"Filter: Showing only HIGH and MEDIUM confidence bets")
    print()

    # Get team info
    teams = {t.id: t for t in db.query(Team).all()}

    # Predict margins and select bets
    recommendations: list[BetRecommendation] = []
    debug_count = 0

    for game in upcoming_games:
        # Predict margin
        pred_margin = inference.predict_margin(game)

        # Get consensus odds
        consensus_odds = get_consensus_odds(db, game)

        # Select best bet
        recommendation = select_best_bet(
            game=game,
            pred_margin=pred_margin,
            consensus_odds=consensus_odds
        )

        recommendations.append(recommendation)

        # Debug output for first 5 games
        if debug and debug_count < 5 and recommendation.confidence_tier != "NO_ODDS":
            print_debug_candidates(game, recommendation, teams)
            debug_count += 1

    # Print recommendations grouped by date
    print_recommendations_by_date(recommendations, teams, only_bets=only_bets)

    # Print summary statistics
    print_summary(recommendations, only_bets=only_bets)


def print_debug_candidates(
    game: Game,
    rec: BetRecommendation,
    teams: dict
):
    """Print full candidate table for debugging."""
    home_team = teams.get(game.home_team_id)
    away_team = teams.get(game.away_team_id)

    if not home_team or not away_team:
        return

    print(f"\n{'='*90}")
    print(f"DEBUG: {away_team.abbreviation} @ {home_team.abbreviation}")
    print(f"{'='*90}")
    print(f"Predicted margin: {rec.pred_margin:+.1f}")
    print(f"\nConsensus odds:")

    odds = rec.consensus_odds
    if odds.spread_line_home is not None:
        print(f"  Spread: {odds.spread_line_home:+.1f} ({odds.spread_odds_home:+d}/{odds.spread_odds_away:+d})")
    else:
        print(f"  Spread: N/A")

    if odds.ml_odds_home is not None:
        print(f"  Moneyline: {odds.ml_odds_home:+d} / {odds.ml_odds_away:+d}")
    else:
        print(f"  Moneyline: N/A")

    print(f"\nCandidate EVs:")
    print(f"{'Market':<12} {'Side':<6} {'Line':<8} {'Odds':<8} {'Prob':<8} {'EV':<8} {'Status':<15}")
    print("-" * 90)

    if rec.all_candidates:
        for cand in rec.all_candidates:
            line_str = f"{cand.line:+.1f}" if cand.line is not None else "---"

            # Determine status
            status = ""
            if cand == rec.best_bet:
                status = "ACTIONABLE ✓"
            elif cand == rec.best_overall:
                if rec.best_bet is None:
                    status = "BEST (no action)"
                else:
                    status = "BEST OVERALL"

            # Check if passes threshold
            passes_prob = cand.probability >= 0.52

            print(f"{cand.market:<12} {cand.side.upper():<6} {line_str:<8} "
                  f"{cand.odds:+6d}   {cand.probability:>6.1%}  {cand.ev:>6.1%}  {status}")

    if rec.best_bet:
        print(f"\n✓ Actionable bet: {rec.best_bet} | Prob: {rec.best_bet.probability:.1%} | "
              f"EV: {rec.best_bet.ev:.1%} | Tier: {rec.confidence_tier}")
    elif rec.best_overall:
        print(f"\n✗ No actionable bet (best overall: {rec.best_overall} | "
              f"Prob: {rec.best_overall.probability:.1%} | EV: {rec.best_overall.ev:.1%})")
    else:
        print(f"\n✗ No odds available")


def format_confidence_emoji(tier: str) -> str:
    """Get emoji for confidence tier."""
    return {
        "HIGH": "🔥",
        "MEDIUM": "✓",
        "LOW": "~",
        "NO_BET": "✗",
        "NO_ODDS": "—"
    }.get(tier, "?")


def print_recommendations_by_date(
    recommendations: list[BetRecommendation],
    teams: dict,
    only_bets: bool = False
):
    """Print recommendations grouped by date."""
    print(f"\n{'='*90}")
    print("BET RECOMMENDATIONS")
    print("="*90)

    current_date = None
    shown_count = 0

    for rec in recommendations:
        game = rec.game
        home_team = teams.get(game.home_team_id)
        away_team = teams.get(game.away_team_id)

        if not home_team or not away_team:
            continue

        # Skip if only_bets and not actionable
        if only_bets and not rec.is_actionable():
            continue

        # Date header
        if game.date != current_date:
            current_date = game.date
            print(f"\n{'─'*90}")
            print(f"📅 {current_date.strftime('%A, %B %d, %Y')}")
            print(f"{'─'*90}")

        # Format matchup
        matchup = f"{away_team.abbreviation:3s} @ {home_team.abbreviation:3s}"

        # Format prediction
        if rec.pred_margin > 0:
            pred_str = f"{home_team.abbreviation} by {abs(rec.pred_margin):.1f}"
        elif rec.pred_margin < 0:
            pred_str = f"{away_team.abbreviation} by {abs(rec.pred_margin):.1f}"
        else:
            pred_str = "Even"

        # Format consensus spread
        if rec.consensus_odds.spread_line_home is not None:
            if rec.consensus_odds.spread_line_home < 0:
                fav_team = home_team.abbreviation
                fav_line = rec.consensus_odds.spread_line_home
            else:
                fav_team = away_team.abbreviation
                fav_line = -rec.consensus_odds.spread_line_home
            spread_str = f"{fav_team} {fav_line:.1f}"
        else:
            spread_str = "N/A"

        # Print game header
        confidence_emoji = format_confidence_emoji(rec.confidence_tier)
        print(f"\n  {matchup}  │  Pred: {pred_str:20s}  │  Market: {spread_str:12s}  │  {confidence_emoji} {rec.confidence_tier}")

        # Print best bet if available
        if rec.best_bet:
            bet = rec.best_bet
            team_abbr = home_team.abbreviation if bet.side == 'home' else away_team.abbreviation

            if bet.market == 'spread':
                bet_desc = f"{team_abbr} {bet.line:+.1f}"
            else:
                bet_desc = f"{team_abbr} ML"

            print(f"      Bet:  {bet_desc:<20s} @ {bet.odds:+5d}  │  "
                  f"Prob: {bet.probability:>5.1%}  │  EV: {bet.ev:>6.1%}")
        elif rec.best_overall:
            # Show best overall as context but mark as NO BET
            bet = rec.best_overall
            team_abbr = home_team.abbreviation if bet.side == 'home' else away_team.abbreviation

            if bet.market == 'spread':
                bet_desc = f"{team_abbr} {bet.line:+.1f}"
            else:
                bet_desc = f"{team_abbr} ML"

            print(f"      NO BET (lean: {bet_desc} @ {bet.odds:+d}, Prob: {bet.probability:.1%}, EV: {bet.ev:.1%})")
        else:
            print(f"      No odds available")

        shown_count += 1

    print("\n" + "="*90)
    if only_bets:
        print(f"Showing {shown_count} actionable bets (HIGH/MEDIUM only)")


def print_summary(recommendations: list[BetRecommendation], only_bets: bool = False):
    """Print summary statistics."""
    total_games = len(recommendations)

    # Count by confidence tier
    tier_counts = {
        "HIGH": 0,
        "MEDIUM": 0,
        "LOW": 0,
        "NO_BET": 0,
        "NO_ODDS": 0
    }

    for rec in recommendations:
        tier_counts[rec.confidence_tier] += 1

    # Stats for games with bets
    games_with_odds = sum(1 for r in recommendations if r.confidence_tier != "NO_ODDS")
    actionable_bets = tier_counts["HIGH"] + tier_counts["MEDIUM"]

    # Market breakdown for actionable bets
    ml_bets = sum(1 for r in recommendations
                  if r.is_actionable() and r.best_bet and r.best_bet.market == 'moneyline')
    spread_bets = sum(1 for r in recommendations
                      if r.is_actionable() and r.best_bet and r.best_bet.market == 'spread')

    # Side breakdown for actionable bets
    home_bets = sum(1 for r in recommendations
                    if r.is_actionable() and r.best_bet and r.best_bet.side == 'home')
    away_bets = sum(1 for r in recommendations
                    if r.is_actionable() and r.best_bet and r.best_bet.side == 'away')

    # Average stats for actionable bets
    if actionable_bets > 0:
        actionable_recs = [r for r in recommendations if r.is_actionable()]
        avg_ev = sum(r.best_bet.ev for r in actionable_recs) / actionable_bets
        avg_prob = sum(r.best_bet.probability for r in actionable_recs) / actionable_bets
    else:
        avg_ev = 0
        avg_prob = 0

    print(f"\nSUMMARY:")
    print(f"  Total games:           {total_games}")
    print(f"  Games with odds:       {games_with_odds}")
    print(f"\nConfidence Breakdown:")
    print(f"  🔥 HIGH:               {tier_counts['HIGH']} ({tier_counts['HIGH']/total_games:.1%})")
    print(f"  ✓  MEDIUM:             {tier_counts['MEDIUM']} ({tier_counts['MEDIUM']/total_games:.1%})")
    print(f"  ~  LOW:                {tier_counts['LOW']} ({tier_counts['LOW']/total_games:.1%})")
    print(f"  ✗  NO_BET:             {tier_counts['NO_BET']} ({tier_counts['NO_BET']/total_games:.1%})")
    print(f"  —  NO_ODDS:            {tier_counts['NO_ODDS']} ({tier_counts['NO_ODDS']/total_games:.1%})")
    print(f"\nActionable Bets (HIGH + MEDIUM): {actionable_bets}")
    if actionable_bets > 0:
        print(f"  By market:             ML: {ml_bets}, Spread: {spread_bets}")
        print(f"  By side:               Home: {home_bets}, Away: {away_bets}")
        print(f"  Avg EV:                {avg_ev:.1%}")
        print(f"  Avg Probability:       {avg_prob:.1%}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Pick best bets for upcoming NBA games"
    )
    parser.add_argument(
        '--days',
        type=int,
        default=3,
        help='Number of days ahead to predict (default: 3)'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Show full candidate table for first 5 games'
    )
    parser.add_argument(
        '--only-bets',
        action='store_true',
        help='Only show HIGH and MEDIUM confidence bets'
    )
    parser.add_argument(
        '--diagnose-odds',
        action='store_true',
        help='Run odds coverage diagnostics'
    )
    parser.add_argument(
        '--sigma',
        type=float,
        default=DEFAULT_SIGMA,
        help=f'Prediction error std dev (default: {DEFAULT_SIGMA})'
    )

    args = parser.parse_args()

    print("="*90)
    print("NBA BET PICKER - MARGIN MODEL + EV CALCULATION")
    print("="*90)

    # Initialize database
    init_db()
    db = SessionLocal()

    try:
        # Run diagnostics if requested
        if args.diagnose_odds:
            diagnose_odds_coverage(db, days=args.days)
            return

        # Initialize inference
        inference = MarginInference(db)
        inference.load_model()

        # Load completed games
        inference._load_completed_games()

        # Print recommendations
        print_bet_recommendations(
            db=db,
            inference=inference,
            days=args.days,
            debug=args.debug,
            only_bets=args.only_bets
        )

        print("\n✅ Bet picking complete")

    finally:
        db.close()


if __name__ == '__main__':
    main()
