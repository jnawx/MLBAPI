"""Game reference data endpoints."""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.game import Game
from app.schemas.game import GameListResponse, GameResponse

router = APIRouter(prefix="/games", tags=["Games"])


@router.get("", response_model=GameListResponse)
async def list_games(
    date_from: Optional[date] = Query(None, description="Start date (inclusive)"),
    date_to: Optional[date] = Query(None, description="End date (inclusive)"),
    season: Optional[int] = Query(None),
    game_type: Optional[str] = Query(None, description="R, P, S, A, etc."),
    team_id: Optional[int] = Query(None, description="Home or away team MLB ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List games with optional filters."""
    query = select(Game)
    count_query = select(func.count()).select_from(Game)

    filters = []
    if date_from:
        filters.append(Game.game_date >= date_from)
    if date_to:
        filters.append(Game.game_date <= date_to)
    if season:
        filters.append(Game.season == season)
    if game_type:
        filters.append(Game.game_type == game_type)
    if team_id:
        from sqlalchemy import or_
        filters.append(or_(Game.home_team_mlb_id == team_id, Game.away_team_mlb_id == team_id))

    for f in filters:
        query = query.where(f)
        count_query = count_query.where(f)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Game.game_date.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    games = result.scalars().all()

    return GameListResponse(
        results=[GameResponse.model_validate(g) for g in games],
        total=total,
    )


@router.get("/{mlb_game_id}", response_model=GameResponse)
async def get_game(mlb_game_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single game by MLB game PK."""
    result = await db.execute(select(Game).where(Game.mlb_game_id == mlb_game_id))
    game = result.scalar_one_or_none()
    if game is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Game {mlb_game_id} not found")
    return GameResponse.model_validate(game)
