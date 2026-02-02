#!/usr/bin/env python3
"""
Test ML recommendation integration with API.

Verifies that ML recommendations work end-to-end through the recommendations service.
"""
import sys
from pathlib import Path
from datetime import date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from nb_analyzer.database import SessionLocal, init_db
from nb_analyzer.models import Game, Team
from nb_analyzer.services.recommendations import RecommendationService


def test_ml_integration(days: int = 1):
    """
    Test ML integration through recommendations service.

    Args:
        days: Number of days ahead to test
    """
    print("="*90)
    print("ML RECOMMENDATION INTEGRATION TEST")
    print("="*90)

    # Initialize database
    init_db()
    db = SessionLocal()

    try:
        # Initialize service
        service = RecommendationService(db)

        # Get upcoming games
        today = date.today()
        end_date = today + timedelta(days=days)

        games = db.query(Game).filter(
            Game.date >= today,
            Game.date <= end_date,
            Game.is_completed == False
        ).order_by(Game.date, Game.id).all()

        print(f"\nTesting {len(games)} upcoming games (next {days} day(s))")
        print(f"Date range: {today} to {end_date}")

        # Get team lookup
        teams = {t.id: t for t in db.query(Team).all()}

        print("\n" + "="*90)
        print("GAME-BY-GAME RESULTS")
        print("="*90)

        # Test each game
        success_count = 0
        error_count = 0
        confidence_counts = {"high": 0, "medium": 0, "low": 0}
        bet_type_counts = {}

        for i, game in enumerate(games, 1):
            home_team = teams.get(game.home_team_id)
            away_team = teams.get(game.away_team_id)

            if not home_team or not away_team:
                continue

            matchup = f"{away_team.abbreviation} @ {home_team.abbreviation}"

            try:
                # Generate ML recommendation
                recommendations = service.generate_ml_recommendations(game)

                if recommendations:
                    rec = recommendations[0]
                    success_count += 1

                    # Count confidence and bet types
                    confidence_counts[rec.confidence] = confidence_counts.get(rec.confidence, 0) + 1
                    bet_type_counts[rec.bet_type] = bet_type_counts.get(rec.bet_type, 0) + 1

                    # Format output
                    print(f"\n{i}. {matchup} (Game ID: {game.id})")
                    print(f"   Date: {game.date}")
                    print(f"   Bet Type: {rec.bet_type}")
                    print(f"   Subject: {rec.subject_abbrev}")
                    print(f"   Confidence: {rec.confidence}")
                    print(f"   Insight: {rec.insight}")
                    print(f"   Supporting Stats:")
                    for stat in rec.supporting_stats[:6]:  # Show first 6 stats
                        print(f"     - {stat['label']}: {stat['value']}")

                else:
                    print(f"\n{i}. {matchup} - No recommendation returned")
                    error_count += 1

            except Exception as e:
                print(f"\n{i}. {matchup} - ERROR: {str(e)}")
                error_count += 1
                import traceback
                traceback.print_exc()

        # Summary
        print("\n" + "="*90)
        print("SUMMARY")
        print("="*90)
        print(f"\nTotal games tested:    {len(games)}")
        print(f"Successful:            {success_count}")
        print(f"Errors:                {error_count}")

        print(f"\nConfidence Breakdown:")
        for conf, count in sorted(confidence_counts.items()):
            print(f"  {conf.capitalize():8s}: {count}")

        print(f"\nBet Type Breakdown:")
        for bet_type, count in sorted(bet_type_counts.items()):
            print(f"  {bet_type:12s}: {count}")

        # Test weekly recommendations endpoint
        print("\n" + "="*90)
        print("TESTING WEEKLY RECOMMENDATIONS ENDPOINT")
        print("="*90)

        weekly_data = service.get_weekly_recommendations(days=days)

        print(f"\nStart date: {weekly_data['start_date']}")
        print(f"End date: {weekly_data['end_date']}")
        print(f"Total games: {weekly_data['total_games']}")
        print(f"Days: {len(weekly_data['days'])}")

        for day in weekly_data['days']:
            print(f"\n  Date: {day['date']}")
            print(f"  Games: {day['games_count']}")

            for game_data in day['games'][:3]:  # Show first 3 games per day
                print(f"    {game_data['away_team']} @ {game_data['home_team']}")
                print(f"      Recommendations: {game_data['recommendations_count']}")
                if game_data['recommendations']:
                    rec = game_data['recommendations'][0]
                    print(f"      - {rec['bet_type']} | {rec['subject']} | {rec['confidence']}")
                    print(f"      - {rec['insight'][:80]}...")

        print("\n" + "="*90)
        print("✅ INTEGRATION TEST COMPLETE")
        print("="*90)

    finally:
        db.close()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(
        description="Test ML recommendation integration"
    )
    parser.add_argument(
        '--days',
        type=int,
        default=1,
        help='Number of days ahead to test (default: 1)'
    )

    args = parser.parse_args()

    test_ml_integration(days=args.days)
