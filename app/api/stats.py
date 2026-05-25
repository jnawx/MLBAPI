"""
Stats endpoints — the core of the API.

These endpoints accept complex filter parameters, build dynamic SQL queries,
execute them against the at-bat-level data, and compute derived statistics.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.stats import (
    BattingStatsRequest,
    BattingStatsResponse,
    BattingStatsResult,
    PitchingStatsRequest,
    PitchingStatsResponse,
    PitchingStatsResult,
    StealStatsRequest,
    StealStatsResponse,
    StealStatsResult,
)
from app.services.query_builder import (
    build_batting_stats_query,
    build_pitching_stats_query,
    build_steal_stats_query,
)
from app.services.stats_engine import compute_batting_stats, compute_pitching_stats, compute_steal_stats

router = APIRouter(prefix="/stats", tags=["Stats"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _row_to_dict(row, keys: list[str]) -> dict[str, Any]:
    """Convert a SQLAlchemy Row to a dict using the column label keys."""
    return {k: getattr(row, k, None) for k in keys}


def _extract_group(row, group_by: list[str] | None) -> dict[str, Any]:
    """Pull the group-by column values out of a result row."""
    if not group_by:
        return {}
    group = {}
    for g in group_by:
        # Handle special mapping: home_away stores a boolean batter_is_home
        if g == "home_away":
            val = getattr(row, "batter_is_home", None)
            group[g] = "home" if val else "away"
        else:
            group[g] = getattr(row, g, getattr(row, f"{g}_mlb_id", None))
    return group


# ---------------------------------------------------------------------------
# Batting stats
# ---------------------------------------------------------------------------


@router.post("/batting", response_model=BattingStatsResponse)
async def batting_stats(params: BattingStatsRequest, db: AsyncSession = Depends(get_db)):
    """
    Query batting statistics with custom split filters.

    Send a JSON body with filter parameters. All filters are optional —
    omit a field to leave it unfiltered.
    """
    query = build_batting_stats_query(params)

    # Apply sorting
    if params.sort_by:
        from sqlalchemy import text
        direction = "ASC" if params.sort_dir and params.sort_dir.lower() == "asc" else "DESC"
        query = query.order_by(text(f"{params.sort_by} {direction} NULLS LAST"))

    # Pagination
    query = query.limit(params.limit).offset(params.offset)

    result = await db.execute(query)
    rows = result.all()

    # Determine season for wOBA weights
    season = params.seasons[0] if params.seasons and len(params.seasons) == 1 else None

    # Stat column labels (everything after the group-by columns)
    stat_keys = [
        "pa", "ab", "h", "singles", "doubles", "triples", "hr", "rbi",
        "bb", "ibb", "hbp", "so", "sf", "sh",
        "avg_exit_velocity", "avg_launch_angle", "hard_hit", "barrels", "batted_balls",
    ]

    results = []
    for row in rows:
        group = _extract_group(row, params.group_by)
        raw = _row_to_dict(row, stat_keys)
        stat_line = compute_batting_stats(raw, season=season)
        results.append(BattingStatsResult(group=group, stats=stat_line))

    # Build a clean summary of applied filters for the response
    filters_applied = params.model_dump(exclude_none=True, exclude={"limit", "offset", "sort_by", "sort_dir"})

    return BattingStatsResponse(
        filters_applied=filters_applied,
        results=results,
        total_results=len(results),
    )


# ---------------------------------------------------------------------------
# Pitching stats
# ---------------------------------------------------------------------------


@router.post("/pitching", response_model=PitchingStatsResponse)
async def pitching_stats(params: PitchingStatsRequest, db: AsyncSession = Depends(get_db)):
    """
    Query pitching statistics with custom split filters.

    Same idea as batting stats but from the pitcher's perspective.
    """
    query = build_pitching_stats_query(params)

    if params.sort_by:
        from sqlalchemy import text
        direction = "ASC" if params.sort_dir and params.sort_dir.lower() == "asc" else "DESC"
        query = query.order_by(text(f"{params.sort_by} {direction} NULLS LAST"))

    query = query.limit(params.limit).offset(params.offset)

    result = await db.execute(query)
    rows = result.all()

    season = params.seasons[0] if params.seasons and len(params.seasons) == 1 else None

    stat_keys = [
        "pa", "ab", "h", "singles", "doubles", "triples", "hr", "rbi",
        "bb", "ibb", "hbp", "so", "sf", "sh",
        "avg_exit_velocity", "avg_launch_angle", "hard_hit", "barrels", "batted_balls",
        "outs_recorded",
    ]

    results = []
    for row in rows:
        group = _extract_group(row, params.group_by)
        raw = _row_to_dict(row, stat_keys)
        stat_line = compute_pitching_stats(raw, season=season)
        results.append(PitchingStatsResult(group=group, stats=stat_line))

    filters_applied = params.model_dump(exclude_none=True, exclude={"limit", "offset", "sort_by", "sort_dir"})

    return PitchingStatsResponse(
        filters_applied=filters_applied,
        results=results,
        total_results=len(results),
    )


# ---------------------------------------------------------------------------
# Steal stats
# ---------------------------------------------------------------------------


@router.post("/steals", response_model=StealStatsResponse)
async def steal_stats(params: StealStatsRequest, db: AsyncSession = Depends(get_db)):
    """Query stolen base statistics."""
    query = build_steal_stats_query(params)
    query = query.limit(params.limit).offset(params.offset)

    result = await db.execute(query)
    rows = result.all()

    stat_keys = ["attempts", "stolen_bases", "caught_stealing"]

    results = []
    for row in rows:
        group = _extract_group(row, params.group_by)
        raw = _row_to_dict(row, stat_keys)
        stat_line = compute_steal_stats(raw)
        results.append(StealStatsResult(group=group, stats=stat_line))

    filters_applied = params.model_dump(exclude_none=True, exclude={"limit", "offset"})

    return StealStatsResponse(
        filters_applied=filters_applied,
        results=results,
        total_results=len(results),
    )
