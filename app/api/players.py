"""Player reference data endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.player import Player
from app.schemas.player import PlayerListResponse, PlayerResponse

router = APIRouter(prefix="/players", tags=["Players"])


@router.get("", response_model=PlayerListResponse)
async def list_players(
    search: Optional[str] = Query(None, description="Search by name (case-insensitive)"),
    active: Optional[bool] = Query(None, description="Filter by active status"),
    position: Optional[str] = Query(None, description="Filter by primary position"),
    bat_side: Optional[str] = Query(None, description="Filter by bat side (L/R/S)"),
    pitch_hand: Optional[str] = Query(None, description="Filter by pitch hand (L/R)"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List players with optional filters."""
    query = select(Player)
    count_query = select(func.count()).select_from(Player)

    if search:
        pattern = f"%{search}%"
        filt = Player.full_name.ilike(pattern)
        query = query.where(filt)
        count_query = count_query.where(filt)
    if active is not None:
        query = query.where(Player.active == active)
        count_query = count_query.where(Player.active == active)
    if position:
        query = query.where(Player.primary_position == position.upper())
        count_query = count_query.where(Player.primary_position == position.upper())
    if bat_side:
        query = query.where(Player.bat_side == bat_side.upper())
        count_query = count_query.where(Player.bat_side == bat_side.upper())
    if pitch_hand:
        query = query.where(Player.pitch_hand == pitch_hand.upper())
        count_query = count_query.where(Player.pitch_hand == pitch_hand.upper())

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    query = query.order_by(Player.last_name, Player.first_name).limit(limit).offset(offset)
    result = await db.execute(query)
    players = result.scalars().all()

    return PlayerListResponse(
        results=[PlayerResponse.model_validate(p) for p in players],
        total=total,
    )


@router.get("/{mlb_id}", response_model=PlayerResponse)
async def get_player(mlb_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single player by MLB ID."""
    result = await db.execute(select(Player).where(Player.mlb_id == mlb_id))
    player = result.scalar_one_or_none()
    if player is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Player {mlb_id} not found")
    return PlayerResponse.model_validate(player)
