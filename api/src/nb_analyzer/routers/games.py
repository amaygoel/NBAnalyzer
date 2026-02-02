"""
API routes for games and recommendations.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from nb_analyzer.database import get_db
from nb_analyzer.models import Game, Team
from nb_analyzer.services import TeamAnalysisService, RecommendationService, StandingsService

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/today")
def get_todays_games(db: Session = Depends(get_db)):
    """Get all games scheduled for today with recommendations."""
    rec_service = RecommendationService(db)
    return rec_service.get_daily_recommendations()


@router.get("/week")
def get_weekly_games(days: int = Query(default=7, ge=1, le=14), db: Session = Depends(get_db)):
    """Get all games for the next N days with recommendations (default 7, max 14)."""
    rec_service = RecommendationService(db)
    return rec_service.get_weekly_recommendations(days=days)


@router.get("/date/{game_date}")
def get_games_by_date(game_date: str, db: Session = Depends(get_db)):
    """Get all games for a specific date (YYYY-MM-DD format)."""
    try:
        parsed_date = date.fromisoformat(game_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

    games = db.query(Game).filter(Game.date == parsed_date).all()

    result = []
    for game in games:
        home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
        away_team = db.query(Team).filter(Team.id == game.away_team_id).first()

        result.append({
            "game_id": game.id,
            "date": game.date.isoformat(),
            "home_team": home_team.abbreviation if home_team else "UNK",
            "away_team": away_team.abbreviation if away_team else "UNK",
            "home_team_name": home_team.name if home_team else "Unknown",
            "away_team_name": away_team.name if away_team else "Unknown",
            "home_score": game.home_score,
            "away_score": game.away_score,
            "is_completed": game.is_completed,
        })

    return {"date": game_date, "games": result}


@router.get("/{game_id}")
def get_game_details(game_id: int, db: Session = Depends(get_db)):
    """Get detailed analysis for a specific game."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    team_service = TeamAnalysisService(db)
    rec_service = RecommendationService(db)
    standings_service = StandingsService(db)

    home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
    away_team = db.query(Team).filter(Team.id == game.away_team_id).first()

    # Get full insights
    insights = team_service.get_game_insights(game.home_team_id, game.away_team_id)

    # Get ML-based recommendations
    recommendations = rec_service.generate_ml_recommendations(game)

    # Get odds
    odds = rec_service._get_game_odds(game)

    # Get team records from current standings
    home_record = standings_service.get_team_record(game.home_team_id)
    away_record = standings_service.get_team_record(game.away_team_id)

    return {
        "game_id": game.id,
        "date": game.date.isoformat(),
        "season": game.season,
        "home_team": {
            "id": game.home_team_id,
            "abbreviation": home_team.abbreviation if home_team else "UNK",
            "name": home_team.name if home_team else "Unknown",
            "score": game.home_score,
            "record": home_record,
        },
        "away_team": {
            "id": game.away_team_id,
            "abbreviation": away_team.abbreviation if away_team else "UNK",
            "name": away_team.name if away_team else "Unknown",
            "score": game.away_score,
            "record": away_record,
        },
        "is_completed": game.is_completed,
        "odds": odds,
        "insights": insights,
        "recommendations": [
            {
                "bet_type": r.bet_type,
                "subject": r.subject_abbrev,
                "insight": r.insight,
                "confidence": r.confidence,
                "supporting_stats": r.supporting_stats,
            }
            for r in recommendations
        ],
    }


@router.get("/{game_id}/recommendations")
def get_game_recommendations(game_id: int, db: Session = Depends(get_db)):
    """Get betting recommendations for a specific game."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    rec_service = RecommendationService(db)
    recommendations = rec_service.generate_ml_recommendations(game)

    home_team = db.query(Team).filter(Team.id == game.home_team_id).first()
    away_team = db.query(Team).filter(Team.id == game.away_team_id).first()

    return {
        "game_id": game.id,
        "matchup": f"{away_team.abbreviation} @ {home_team.abbreviation}" if home_team and away_team else "Unknown",
        "recommendations_count": len(recommendations),
        "recommendations": [
            {
                "bet_type": r.bet_type,
                "subject": r.subject_abbrev,
                "insight": r.insight,
                "confidence": r.confidence,
                "supporting_stats": r.supporting_stats,
            }
            for r in recommendations
        ],
    }
