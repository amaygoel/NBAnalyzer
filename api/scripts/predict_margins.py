#!/usr/bin/env python3
"""
Predict margins for upcoming NBA games using trained model.

Demonstrates the inference pipeline with sanity checks.
"""
import sys
import random
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np
from sqlalchemy import and_
from sklearn.metrics import mean_absolute_error

from nb_analyzer.database import SessionLocal, init_db
from nb_analyzer.models import Game, Team, GameOdds
from nb_analyzer.ml.margin_inference import MarginInference


def get_consensus_spread(db, game: Game) -> float | None:
    """Get median spread line across all bookmakers."""
    odds_records = db.query(GameOdds).filter(
        GameOdds.game_id == game.id,
        GameOdds.market_type == 'spreads',
        GameOdds.home_line.isnot(None)
    ).all()

    if not odds_records:
        return None

    lines = [o.home_line for o in odds_records]
    return float(np.median(lines))


def print_upcoming_predictions(db, inference: MarginInference, days: int = 3):
    """Print predictions for upcoming games."""
    today = date.today()
    end_date = today + timedelta(days=days)

    print("\n" + "="*80)
    print(f"UPCOMING GAMES PREDICTIONS (Next {days} days)")
    print("="*80)

    # Get upcoming games
    upcoming_games = db.query(Game).filter(
        Game.date >= today,
        Game.date <= end_date,
        Game.is_completed == False
    ).order_by(Game.date, Game.id).all()

    if not upcoming_games:
        print(f"\n⚠️  No upcoming games found in next {days} days")
        return

    print(f"\nFound {len(upcoming_games)} upcoming games\n")

    # Get team info for display
    teams = {t.id: t for t in db.query(Team).all()}

    # Predict margins
    results = inference.predict_margins_batch(upcoming_games)

    # Print results grouped by date
    current_date = None
    for game, predicted_margin, features in results:
        if game.date != current_date:
            current_date = game.date
            print(f"\n{'─'*80}")
            print(f"📅 {current_date.strftime('%A, %B %d, %Y')}")
            print(f"{'─'*80}")

        home_team = teams.get(game.home_team_id)
        away_team = teams.get(game.away_team_id)

        if not home_team or not away_team:
            continue

        # Format matchup
        matchup = f"{away_team.abbreviation:3s} @ {home_team.abbreviation:3s}"

        # Format prediction
        if predicted_margin > 0:
            pred_str = f"{home_team.abbreviation} by {abs(predicted_margin):.1f}"
        else:
            pred_str = f"{away_team.abbreviation} by {abs(predicted_margin):.1f}"

        # Get consensus spread if available
        consensus_spread = get_consensus_spread(db, game)
        if consensus_spread is not None:
            spread_str = f"Market: {home_team.abbreviation} {consensus_spread:+.1f}"
            diff = predicted_margin - consensus_spread
            edge_str = f"Edge: {diff:+.1f}" if abs(diff) >= 2.0 else ""
        else:
            spread_str = "Market: N/A"
            edge_str = ""

        # Print game info
        print(f"\n  {matchup}  │  Pred: {pred_str:20s}  │  {spread_str:20s}  {edge_str}")

        # Print key features
        rest_str = f"Rest: {features['rest_diff']:+d}" if features['rest_diff'] != 0 else ""
        b2b_str = ""
        if features['home_b2b'] == 1:
            b2b_str = f"{home_team.abbreviation} B2B"
        if features['away_b2b'] == 1:
            b2b_str += f" {away_team.abbreviation} B2B" if b2b_str else f"{away_team.abbreviation} B2B"

        if rest_str or b2b_str:
            print(f"         {rest_str}  {b2b_str}")

    print("\n" + "="*80)


def print_example_features(results: list):
    """Print 3 example feature dictionaries."""
    print("\n" + "="*80)
    print("EXAMPLE FEATURE EXTRACTION (3 games)")
    print("="*80)

    for i, (game, predicted_margin, features) in enumerate(results[:3], 1):
        print(f"\nGame {i}: {game.id} on {game.date}")
        print(f"  Predicted margin: {predicted_margin:+.2f}")
        print("  Features:")
        for key, value in features.items():
            print(f"    {key:30s} = {value:.4f}")


def run_backtest_spot_check(db, inference: MarginInference, n_samples: int = 50):
    """
    Backtest on random completed games to verify no leakage.

    Computes features as-of each game's date and compares prediction to actual.
    """
    print("\n" + "="*80)
    print(f"BACKTEST SPOT CHECK ({n_samples} random completed games)")
    print("="*80)

    # Get random completed games
    all_completed = db.query(Game).filter(
        Game.is_completed == True,
        Game.home_score.isnot(None),
        Game.away_score.isnot(None)
    ).all()

    if len(all_completed) < n_samples:
        n_samples = len(all_completed)

    sample_games = random.sample(all_completed, n_samples)

    print(f"\nSampled {n_samples} completed games from {len(all_completed)} total")
    print("Computing predictions as-of each game date...\n")

    # Clear cache to ensure fresh state computation
    inference.clear_cache()

    predictions = []
    actuals = []

    for game in sample_games:
        try:
            predicted_margin = inference.predict_margin(game)
            actual_margin = game.home_score - game.away_score

            predictions.append(predicted_margin)
            actuals.append(actual_margin)

        except Exception as e:
            print(f"  ⚠️  Error on game {game.id}: {e}")
            continue

    # Compute metrics
    if predictions:
        mae = mean_absolute_error(actuals, predictions)
        correct_direction = sum((p > 0) == (a > 0) for p, a in zip(predictions, actuals))
        direction_acc = correct_direction / len(predictions)

        print(f"✓ Backtest complete on {len(predictions)} games")
        print(f"\nMetrics:")
        print(f"  MAE:  {mae:.2f} points")
        print(f"  Winner Direction Accuracy: {direction_acc:.1%} ({correct_direction}/{len(predictions)})")

        # Show a few examples
        print(f"\nExample predictions vs actuals:")
        for i in range(min(5, len(predictions))):
            game = sample_games[i]
            pred = predictions[i]
            actual = actuals[i]
            error = abs(pred - actual)
            direction = "✓" if (pred > 0) == (actual > 0) else "✗"
            print(f"  {direction} Game {game.id}: Pred {pred:+6.1f} vs Actual {actual:+6.1f}  (error: {error:.1f})")
    else:
        print("❌ No successful predictions")

    print("\n" + "="*80)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Predict margins for upcoming NBA games"
    )
    parser.add_argument(
        '--days',
        type=int,
        default=3,
        help='Number of days ahead to predict (default: 3)'
    )
    parser.add_argument(
        '--show-features',
        action='store_true',
        help='Show example feature extraction'
    )
    parser.add_argument(
        '--backtest',
        action='store_true',
        help='Run backtest spot check on completed games'
    )
    parser.add_argument(
        '--backtest-samples',
        type=int,
        default=50,
        help='Number of games for backtest (default: 50)'
    )

    args = parser.parse_args()

    print("="*80)
    print("NBA MARGIN PREDICTION - INFERENCE PIPELINE")
    print("="*80)

    # Initialize database
    init_db()
    db = SessionLocal()

    try:
        # Initialize inference
        inference = MarginInference(db)
        inference.load_model()

        # Load completed games (this happens once)
        inference._load_completed_games()

        # Get upcoming games for predictions
        today = date.today()
        end_date = today + timedelta(days=args.days)

        upcoming_games = db.query(Game).filter(
            Game.date >= today,
            Game.date <= end_date,
            Game.is_completed == False
        ).order_by(Game.date, Game.id).all()

        # Predict margins
        if upcoming_games:
            results = inference.predict_margins_batch(upcoming_games)

            # Print example features if requested
            if args.show_features:
                print_example_features(results)

            # Print predictions
            print_upcoming_predictions(db, inference, days=args.days)
        else:
            print(f"\n⚠️  No upcoming games found in next {args.days} days")

        # Run backtest if requested
        if args.backtest:
            run_backtest_spot_check(db, inference, n_samples=args.backtest_samples)

        print("\n✅ Inference complete")

    finally:
        db.close()


if __name__ == '__main__':
    main()
