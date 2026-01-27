"""
API routes for team data and analysis.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from nba_predictor.database import get_db
from nba_predictor.models import Team
from nba_predictor.services import TeamAnalysisService

router = APIRouter(prefix="/teams", tags=["teams"])


@router.get("/")
def list_teams(
    conference: str | None = Query(None, description="Filter by conference (East/West)"),
    db: Session = Depends(get_db),
):
    """List all NBA teams."""
    query = db.query(Team)
    if conference:
        query = query.filter(Team.conference == conference)

    teams = query.order_by(Team.name).all()

    return {
        "count": len(teams),
        "teams": [
            {
                "id": t.id,
                "name": t.name,
                "abbreviation": t.abbreviation,
                "city": t.city,
                "conference": t.conference,
                "division": t.division,
            }
            for t in teams
        ],
    }


@router.get("/{team_abbrev}")
def get_team(team_abbrev: str, db: Session = Depends(get_db)):
    """Get team details by abbreviation (e.g., GSW, LAL)."""
    team = db.query(Team).filter(Team.abbreviation == team_abbrev.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_abbrev}' not found")

    service = TeamAnalysisService(db)

    return {
        "id": team.id,
        "name": team.name,
        "abbreviation": team.abbreviation,
        "city": team.city,
        "conference": team.conference,
        "division": team.division,
        "current_season": {
            "overall": service.get_overall_record(team.id, "2024-25").display,
            "home": service.get_home_record(team.id, "2024-25").display,
            "away": service.get_away_record(team.id, "2024-25").display,
        },
    }


@router.get("/{team_abbrev}/trends")
def get_team_trends(
    team_abbrev: str,
    season: str | None = Query(None, description="Season filter (e.g., 2024-25)"),
    db: Session = Depends(get_db),
):
    """Get all calculated trends for a team."""
    team = db.query(Team).filter(Team.abbreviation == team_abbrev.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_abbrev}' not found")

    service = TeamAnalysisService(db)
    trends = service.get_all_trends(team.id, season)

    return {
        "team": team.abbreviation,
        "team_name": team.name,
        "season": season or "all",
        "trends": [
            {
                "category": t.category,
                "description": t.description,
                "record": t.record.display,
                "win_pct": round(t.hit_rate * 100, 1),
                "sample_size": t.sample_size,
                "confidence": t.confidence,
            }
            for t in trends
        ],
    }


@router.get("/{team_abbrev}/recent")
def get_team_recent_games(
    team_abbrev: str,
    limit: int = Query(10, ge=1, le=50, description="Number of games to return"),
    db: Session = Depends(get_db),
):
    """Get a team's recent game results."""
    team = db.query(Team).filter(Team.abbreviation == team_abbrev.upper()).first()
    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_abbrev}' not found")

    service = TeamAnalysisService(db)
    recent = service.get_recent_games(team.id, limit)
    form = service.get_recent_form(team.id, limit)

    return {
        "team": team.abbreviation,
        "team_name": team.name,
        "record": form.display,
        "win_pct": round(form.win_pct * 100, 1),
        "games": recent,
    }


@router.get("/{team_abbrev}/vs/{opponent_abbrev}")
def get_head_to_head(
    team_abbrev: str,
    opponent_abbrev: str,
    db: Session = Depends(get_db),
):
    """Get head-to-head record between two teams."""
    team = db.query(Team).filter(Team.abbreviation == team_abbrev.upper()).first()
    opponent = db.query(Team).filter(Team.abbreviation == opponent_abbrev.upper()).first()

    if not team:
        raise HTTPException(status_code=404, detail=f"Team '{team_abbrev}' not found")
    if not opponent:
        raise HTTPException(status_code=404, detail=f"Team '{opponent_abbrev}' not found")

    service = TeamAnalysisService(db)

    # Get H2H for different time periods
    all_time = service.get_head_to_head_record(team.id, opponent.id)
    recent_seasons = service.get_head_to_head_record(
        team.id, opponent.id, seasons=["2022-23", "2023-24", "2024-25"]
    )

    return {
        "team": team.abbreviation,
        "opponent": opponent.abbreviation,
        "all_time": {
            "record": all_time.display,
            "win_pct": round(all_time.win_pct * 100, 1),
            "games": all_time.total,
        },
        "last_3_seasons": {
            "record": recent_seasons.display,
            "win_pct": round(recent_seasons.win_pct * 100, 1),
            "games": recent_seasons.total,
        },
    }
