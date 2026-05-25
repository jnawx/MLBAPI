"""Team reference data endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.team import Team
from app.schemas.team import TeamListResponse, TeamResponse

router = APIRouter(prefix="/teams", tags=["Teams"])


@router.get("", response_model=TeamListResponse)
async def list_teams(
    active: Optional[bool] = Query(None),
    league: Optional[str] = Query(None, description="'American League' or 'National League'"),
    db: AsyncSession = Depends(get_db),
):
    """List all MLB teams."""
    query = select(Team)
    if active is not None:
        query = query.where(Team.active == active)
    if league:
        query = query.where(Team.league_name.ilike(f"%{league}%"))

    result = await db.execute(query.order_by(Team.name))
    teams = result.scalars().all()
    return TeamListResponse(
        results=[TeamResponse.model_validate(t) for t in teams],
        total=len(teams),
    )


@router.get("/{mlb_id}", response_model=TeamResponse)
async def get_team(mlb_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single team by MLB ID."""
    result = await db.execute(select(Team).where(Team.mlb_id == mlb_id))
    team = result.scalar_one_or_none()
    if team is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Team {mlb_id} not found")
    return TeamResponse.model_validate(team)
